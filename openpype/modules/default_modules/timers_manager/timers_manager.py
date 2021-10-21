import os
import platform
from openpype.modules import OpenPypeModule
from openpype_interfaces import (
    ITimersManager,
    ITrayService
)
from avalon.api import AvalonMongoDB


class ExampleTimersManagerConnector:
    """Timers manager can handle timers of multiple modules/addons.

    Module must have object under `timers_manager_connector` attribute with
    few methods. This is example class of the object that could be stored under
    module.

    Required methods are 'stop_timer' and 'start_timer'.

    # TODO pass asset document instead of `hierarchy`
    Example of `data` that are passed during changing timer:
    ```
    data = {
        "project_name": project_name,
        "task_name": task_name,
        "task_type": task_type,
        "hierarchy": hierarchy
    }
    ```
    """
    # Not needed at all
    def __init__(self, module):
        # Store timer manager module to be able call it's methods when needed
        self._timers_manager_module = None

        # Store module which want to use timers manager to have access
        self._module = module

    # Required
    def stop_timer(self):
        """Called by timers manager when module should stop timer."""
        self._module.stop_timer()

    # Required
    def start_timer(self, data):
        """Method called by timers manager when should start timer."""
        self._module.start_timer(data)

    # Optional
    def register_timers_manager(self, timer_manager_module):
        """Method called by timers manager where it's object is passed.

        This is moment when timers manager module can be store to be able
        call it's callbacks (e.g. timer started).
        """
        self._timers_manager_module = timer_manager_module

    # Custom implementation
    def timer_started(self, data):
        """This is example of possibility to trigger callbacks on manager."""
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_started(self._module.id, data)

    # Custom implementation
    def timer_stopped(self):
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_stopped(self._module.id)


class TimersManager(OpenPypeModule, ITrayService):
    """ Handles about Timers.

    Should be able to start/stop all timers at once.

    To be able use this advantage module has to have attribute with name
    `timers_manager_connector` which has two methods 'stop_timer'
    and 'start_timer'. Optionally may have `register_timers_manager` where
    object of TimersManager module is passed to be able call it's callbacks.

    See `ExampleTimersManagerConnector`.
    """
    name = "timers_manager"
    label = "Timers Service"

    _required_methods = (
        "stop_timer",
        "start_timer"
    )

    def initialize(self, modules_settings):
        timers_settings = modules_settings[self.name]

        self.enabled = timers_settings["enabled"]

        # When timer will stop if idle manager is running (minutes)
        full_time = int(timers_settings["full_time"] * 60)
        # How many minutes before the timer is stopped will popup the message
        message_time = int(timers_settings["message_time"] * 60)

        auto_stop = timers_settings["auto_stop"]
        # Turn of auto stop on MacOs because pynput requires root permissions
        if platform.system().lower() == "darwin" or full_time <= 0:
            auto_stop = False

        self.auto_stop = auto_stop
        self.time_show_message = full_time - message_time
        self.time_stop_timer = full_time

        self.is_running = False
        self.last_task = None

        # Tray attributes
        self._signal_handler = None
        self._widget_user_idle = None
        self._idle_manager = None

        self._connectors_by_module_id = {}
        self._modules_by_id = {}

    def tray_init(self):
        if not self.auto_stop:
            return

        from .idle_threads import IdleManager
        from .widget_user_idle import WidgetUserIdle, SignalHandler

        signal_handler = SignalHandler(self)
        idle_manager = IdleManager()
        widget_user_idle = WidgetUserIdle(self)
        widget_user_idle.set_countdown_start(self.time_show_message)

        idle_manager.signal_reset_timer.connect(
            widget_user_idle.reset_countdown
        )
        idle_manager.add_time_signal(
            self.time_show_message, signal_handler.signal_show_message
        )
        idle_manager.add_time_signal(
            self.time_stop_timer, signal_handler.signal_stop_timers
        )

        self._signal_handler = signal_handler
        self._widget_user_idle = widget_user_idle
        self._idle_manager = idle_manager

    def tray_start(self, *_a, **_kw):
        if self._idle_manager:
            self._idle_manager.start()

    def tray_exit(self):
        if self._idle_manager:
            self._idle_manager.stop()
            self._idle_manager.wait()

    def start_timer(self, project_name, asset_name, task_name, hierarchy):
        """
            Start timer for 'project_name', 'asset_name' and 'task_name'

            Called from REST api by hosts.

            Args:
                project_name (string)
                asset_name (string)
                task_name (string)
                hierarchy (string)
        """
        dbconn = AvalonMongoDB()
        dbconn.install()
        dbconn.Session["AVALON_PROJECT"] = project_name

        asset_doc = dbconn.find_one({
            "type": "asset", "name": asset_name
        })
        if not asset_doc:
            raise ValueError("Uknown asset {}".format(asset_name))

        task_type = ''
        try:
            task_type = asset_doc["data"]["tasks"][task_name]["type"]
        except KeyError:
            self.log.warning("Couldn't find task_type for {}".
                             format(task_name))

        hierarchy = hierarchy.split("\\")
        hierarchy.append(asset_name)

        data = {
            "project_name": project_name,
            "task_name": task_name,
            "task_type": task_type,
            "hierarchy": hierarchy
        }
        self.timer_started(None, data)

    def get_task_time(self, project_name, asset_name, task_name):
        times = {}
        for module_id, connector in self._connectors_by_module_id.items():
            if hasattr(connector, "get_task_time"):
                module = self._modules_by_id[module_id]
                times[module.name] = connector.get_task_time(
                    project_name, asset_name, task_name
                )
        return times

    def timer_started(self, source_id, data):
        for module_id, connector in self._connectors_by_module_id.items():
            if module_id == source_id:
                continue

            try:
                connector.start_timer(data)
            except Exception:
                self.log.info(
                    "Failed to start timer on connector {}".format(
                        str(connector)
                    )
                )

        self.last_task = data
        self.is_running = True

    def timer_stopped(self, source_id):
        for module_id, connector in self._connectors_by_module_id.items():
            if module_id == source_id:
                continue

            try:
                connector.stop_timer()
            except Exception:
                self.log.info(
                    "Failed to stop timer on connector {}".format(
                        str(connector)
                    )
                )

    def restart_timers(self):
        if self.last_task is not None:
            self.timer_started(None, self.last_task)

    def stop_timers(self):
        if self.is_running is False:
            return

        if self._widget_user_idle is not None:
            self._widget_user_idle.set_timer_stopped()
        self.is_running = False

        self.timer_stopped(None)

    def connect_with_modules(self, enabled_modules):
        for module in enabled_modules:
            connector = getattr(module, "timers_manager_connector", None)
            if connector is None:
                continue

            missing_methods = set()
            for method_name in self._required_methods:
                if not hasattr(connector, method_name):
                    missing_methods.add(method_name)

            if missing_methods:
                joined = ", ".join(
                    ['"{}"'.format(name for name in missing_methods)]
                )
                self.log.info((
                    "Module \"{}\" has missing required methods {}."
                ).format(module.name, joined))
                continue

            self._connectors_by_module_id[module.id] = connector
            self._modules_by_id[module.id] = module

            # Optional method
            if hasattr(connector, "register_timers_manager"):
                try:
                    connector.register_timers_manager(self)
                except Exception:
                    self.log.info((
                        "Failed to register timers manager"
                        " for connector of module \"{}\"."
                    ).format(module.name))

    def show_message(self):
        if self.is_running is False:
            return
        if not self._widget_user_idle.is_showed():
            self._widget_user_idle.reset_countdown()
            self._widget_user_idle.show()

    # Webserver module implementation
    def webserver_initialization(self, server_manager):
        """Add routes for timers to be able start/stop with rest api."""
        if self.tray_initialized:
            from .rest_api import TimersManagerModuleRestApi
            self.rest_api_obj = TimersManagerModuleRestApi(
                self, server_manager
            )

    def change_timer_from_host(self, project_name, asset_name, task_name):
        """Prepared method for calling change timers on REST api"""
        webserver_url = os.environ.get("OPENPYPE_WEBSERVER_URL")
        if not webserver_url:
            self.log.warning("Couldn't find webserver url")
            return

        rest_api_url = "{}/timers_manager/start_timer".format(webserver_url)
        try:
            import requests
        except Exception:
            self.log.warning("Couldn't start timer")
            return
        data = {
            "project_name": project_name,
            "asset_name": asset_name,
            "task_name": task_name
        }

        requests.post(rest_api_url, json=data)
