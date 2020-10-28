import os
import sys
import types
import copy
import acre
import getpass
import platform
import six
import logging
from pype.api import config, Anatomy, Logger
from avalon import api as avalon
from avalon import lib

log = logging.getLogger(__name__)


def execute_hook(hook, *args, **kwargs):
    """
    This will load hook file, instantiate class and call `execute` method
    on it. Hook must be in a form:

    `$PYPE_SETUP_PATH/repos/pype/path/to/hook.py/HookClass`

    This will load `hook.py`, instantiate HookClass and then execute_hook
    `execute(*args, **kwargs)`

    :param hook: path to hook class
    :type hook: str
    """

    class_name = hook.split("/")[-1]

    abspath = os.path.join(os.getenv('PYPE_SETUP_PATH'),
                           'repos', 'pype', *hook.split("/")[:-1])

    mod_name, mod_ext = os.path.splitext(os.path.basename(abspath))

    if not mod_ext == ".py":
        return False

    module = types.ModuleType(mod_name)
    module.__file__ = abspath

    try:
        with open(abspath) as f:
            six.exec_(f.read(), module.__dict__)

        sys.modules[abspath] = module

    except Exception as exp:
        log.exception("loading hook failed: {}".format(exp),
                      exc_info=True)
        return False

    obj = getattr(module, class_name)
    hook_obj = obj()
    ret_val = hook_obj.execute(*args, **kwargs)
    return ret_val


class ApplicationLaunchFailed(Exception):
    pass


def launch_application(project_name, asset_name, task_name, app_name):
    from .project_utils import get_avalon_database
    database = get_avalon_database()
    project_document = database[project_name].find_one({"type": "project"})
    asset_document = database[project_name].find_one({
        "type": "asset",
        "name": asset_name
    })

    asset_doc_parents = asset_document["data"].get("parents")
    hierarchy = "/".join(asset_doc_parents)

    app_def = lib.get_application(app_name)
    app_label = app_def.get("ftrack_label", app_def.get("label", app_name))

    host_name = app_def["application_dir"]
    data = {
        "project": {
            "name": project_document["name"],
            "code": project_document["data"].get("code")
        },
        "task": task_name,
        "asset": asset_name,
        "app": host_name,
        "hierarchy": hierarchy
    }

    try:
        anatomy = Anatomy(project_name)
        anatomy_filled = anatomy.format(data)
        workdir = os.path.normpath(anatomy_filled["work"]["folder"])

    except Exception as exc:
        raise ApplicationLaunchFailed(
            "Error in anatomy.format: {}".format(str(exc))
        )

    try:
        os.makedirs(workdir)
    except FileExistsError:
        pass

    last_workfile_path = None
    extensions = avalon.HOST_WORKFILE_EXTENSIONS.get(host_name)
    if extensions:
        # Find last workfile
        file_template = anatomy.templates["work"]["file"]
        data.update({
            "version": 1,
            "user": os.environ.get("PYPE_USERNAME") or getpass.getuser(),
            "ext": extensions[0]
        })

        last_workfile_path = avalon.last_workfile(
            workdir, file_template, data, extensions, True
        )

    # set environments for Avalon
    prep_env = copy.deepcopy(os.environ)
    prep_env.update({
        "AVALON_PROJECT": project_name,
        "AVALON_ASSET": asset_name,
        "AVALON_TASK": task_name,
        "AVALON_APP": host_name,
        "AVALON_APP_NAME": app_name,
        "AVALON_HIERARCHY": hierarchy,
        "AVALON_WORKDIR": workdir
    })

    start_last_workfile = avalon.should_start_last_workfile(
        project_name, host_name, task_name
    )
    # Store boolean as "0"(False) or "1"(True)
    prep_env["AVALON_OPEN_LAST_WORKFILE"] = (
        str(int(bool(start_last_workfile)))
    )

    if (
        start_last_workfile
        and last_workfile_path
        and os.path.exists(last_workfile_path)
    ):
        prep_env["AVALON_LAST_WORKFILE"] = last_workfile_path

    prep_env.update(anatomy.roots_obj.root_environments())

    # collect all the 'environment' attributes from parents
    tools_attr = [prep_env["AVALON_APP"], prep_env["AVALON_APP_NAME"]]
    tools_env = asset_document["data"].get("tools_env") or []
    tools_attr.extend(tools_env)

    tools_env = acre.get_tools(tools_attr)
    env = acre.compute(tools_env)
    env = acre.merge(env, current_env=dict(prep_env))

    # Get path to execute
    st_temp_path = os.environ["PYPE_CONFIG"]
    os_plat = platform.system().lower()

    # Path to folder with launchers
    path = os.path.join(st_temp_path, "launchers", os_plat)

    # Full path to executable launcher
    execfile = None

    launch_hook = app_def.get("launch_hook")
    if launch_hook:
        log.info("launching hook: {}".format(launch_hook))
        ret_val = execute_hook(launch_hook, env=env)
        if not ret_val:
            raise ApplicationLaunchFailed(
                "Hook didn't finish successfully {}".format(app_label)
            )

    if sys.platform == "win32":
        for ext in os.environ["PATHEXT"].split(os.pathsep):
            fpath = os.path.join(path.strip('"'), app_def["executable"] + ext)
            if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                execfile = fpath
                break

        # Run SW if was found executable
        if execfile is None:
            raise ApplicationLaunchFailed(
                "We didn't find launcher for {}".format(app_label)
            )

        popen = lib.launch(
            executable=execfile, args=[], environment=env
        )

    elif (
        sys.platform.startswith("linux")
        or sys.platform.startswith("darwin")
    ):
        execfile = os.path.join(path.strip('"'), app_def["executable"])
        # Run SW if was found executable
        if execfile is None:
            raise ApplicationLaunchFailed(
                "We didn't find launcher for {}".format(app_label)
            )

        if not os.path.isfile(execfile):
            raise ApplicationLaunchFailed(
                "Launcher doesn't exist - {}".format(execfile)
            )

        try:
            fp = open(execfile)
        except PermissionError as perm_exc:
            raise ApplicationLaunchFailed(
                "Access denied on launcher {} - {}".format(execfile, perm_exc)
            )

        fp.close()
        # check executable permission
        if not os.access(execfile, os.X_OK):
            raise ApplicationLaunchFailed(
                "No executable permission - {}".format(execfile)
            )

        popen = lib.launch(  # noqa: F841
            "/usr/bin/env", args=["bash", execfile], environment=env
        )
    return popen


class ApplicationAction(avalon.Action):
    """Default application launcher

    This is a convenience application Action that when "config" refers to a
    parsed application `.toml` this can launch the application.

    """
    _log = None
    config = None
    group = None
    variant = None
    required_session_keys = (
        "AVALON_PROJECT",
        "AVALON_ASSET",
        "AVALON_TASK"
    )

    @property
    def log(self):
        if self._log is None:
            self._log = Logger().get_logger(self.__class__.__name__)
        return self._log

    def is_compatible(self, session):
        for key in self.required_session_keys:
            if key not in session:
                return False
        return True

    def process(self, session, **kwargs):
        """Process the full Application action"""

        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]
        task_name = session["AVALON_TASK"]
        launch_application(
            project_name, asset_name, task_name, self.name
        )

        self._ftrack_after_launch_procedure(
            project_name, asset_name, task_name
        )

    def _ftrack_after_launch_procedure(
        self, project_name, asset_name, task_name
    ):
        # TODO move to launch hook
        required_keys = ("FTRACK_SERVER", "FTRACK_API_USER", "FTRACK_API_KEY")
        for key in required_keys:
            if not os.environ.get(key):
                self.log.debug((
                    "Missing required environment \"{}\""
                    " for Ftrack after launch procedure."
                ).format(key))
                return

        try:
            import ftrack_api
            session = ftrack_api.Session(auto_connect_event_hub=True)
            self.log.debug("Ftrack session created")
        except Exception:
            self.log.warning("Couldn't create Ftrack session")
            return

        try:
            entity = self._find_ftrack_task_entity(
                session, project_name, asset_name, task_name
            )
            self._ftrack_status_change(session, entity, project_name)
            self._start_timer(session, entity, ftrack_api)
        except Exception:
            self.log.warning(
                "Couldn't finish Ftrack procedure.", exc_info=True
            )
            return

        finally:
            session.close()

    def _find_ftrack_task_entity(
        self, session, project_name, asset_name, task_name
    ):
        project_entity = session.query(
            "Project where full_name is \"{}\"".format(project_name)
        ).first()
        if not project_entity:
            self.log.warning(
                "Couldn't find project \"{}\" in Ftrack.".format(project_name)
            )
            return

        potential_task_entities = session.query((
            "TypedContext where parent.name is \"{}\" and project_id is \"{}\""
        ).format(asset_name, project_entity["id"])).all()
        filtered_entities = []
        for _entity in potential_task_entities:
            if (
                _entity.entity_type.lower() == "task"
                and _entity["name"] == task_name
            ):
                filtered_entities.append(_entity)

        if not filtered_entities:
            self.log.warning((
                "Couldn't find task \"{}\" under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        if len(filtered_entities) > 1:
            self.log.warning((
                "Found more than one task \"{}\""
                " under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        return filtered_entities[0]

    def _ftrack_status_change(self, session, entity, project_name):
        presets = config.get_presets(project_name)["ftrack"]["ftrack_config"]
        statuses = presets.get("status_update")
        if not statuses:
            return

        actual_status = entity["status"]["name"].lower()
        already_tested = set()
        ent_path = "/".join(
            [ent["name"] for ent in entity["link"]]
        )
        while True:
            next_status_name = None
            for key, value in statuses.items():
                if key in already_tested:
                    continue
                if actual_status in value or "_any_" in value:
                    if key != "_ignore_":
                        next_status_name = key
                        already_tested.add(key)
                    break
                already_tested.add(key)

            if next_status_name is None:
                break

            try:
                query = "Status where name is \"{}\"".format(
                    next_status_name
                )
                status = session.query(query).one()

                entity["status"] = status
                session.commit()
                self.log.debug("Changing status to \"{}\" <{}>".format(
                    next_status_name, ent_path
                ))
                break

            except Exception:
                session.rollback()
                msg = (
                    "Status \"{}\" in presets wasn't found"
                    " on Ftrack entity type \"{}\""
                ).format(next_status_name, entity.entity_type)
                self.log.warning(msg)

    def _start_timer(self, session, entity, _ftrack_api):
        self.log.debug("Triggering timer start.")

        user_entity = session.query("User where username is \"{}\"".format(
            os.environ["FTRACK_API_USER"]
        )).first()
        if not user_entity:
            self.log.warning(
                "Couldn't find user with username \"{}\" in Ftrack".format(
                    os.environ["FTRACK_API_USER"]
                )
            )
            return

        source = {
            "user": {
                "id": user_entity["id"],
                "username": user_entity["username"]
            }
        }
        event_data = {
            "actionIdentifier": "start.timer",
            "selection": [{"entityId": entity["id"], "entityType": "task"}]
        }
        session.event_hub.publish(
            _ftrack_api.event.base.Event(
                topic="ftrack.action.launch",
                data=event_data,
                source=source
            ),
            on_error="ignore"
        )
        self.log.debug("Timer start triggered successfully.")
