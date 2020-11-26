from pype.lib import abstract_submit_deadline
from pype.lib.abstract_submit_deadline import DeadlineJobInfo
import pyblish.api
import os
import attr
import getpass
from avalon import api


@attr.s
class DeadlinePluginInfo():
    Comp = attr.ib(default=None)
    SceneFile = attr.ib(default=None)
    OutputFilePath = attr.ib(default=None)
    Output = attr.ib(default=None)
    StartupDirectory = attr.ib(default=None)
    Arguments = attr.ib(default=None)
    ProjectPath = attr.ib(default=None)
    AWSAssetFile0 = attr.ib(default=None)
    Version = attr.ib(default=None)
    MultiProcess = attr.ib(default=None)


class AfterEffectsSubmitDeadline(abstract_submit_deadline.AbstractSubmitDeadline):

    label = "Submit AE to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["aftereffects"]
    families = ["render.farm"]  # cannot be "render' as that is integrated
    use_published = False

    def get_job_info(self):
        dln_job_info = DeadlineJobInfo(Plugin="AfterEffects")

        context = self._instance.context

        dln_job_info.Name = self._instance.data["name"]
        dln_job_info.BatchName = os.path.basename(self._instance.
                                                  data["source"])
        dln_job_info.Plugin = "AfterEffects"
        dln_job_info.UserName = context.data.get(
            "deadlineUser", getpass.getuser())
        if self._instance.data["frameEnd"] > self._instance.data["frameStart"]:
            frame_range = "{}-{}".format(self._instance.data["frameStart"],
                                         self._instance.data["frameEnd"])
            dln_job_info.Frames = frame_range

        if len(self._instance.data["expectedFiles"]) == 1:
            dln_job_info.ChunkSize = 1000000

        dln_job_info.OutputFilename = \
            os.path.basename(self._instance.data["expectedFiles"][0])
        dln_job_info.OutputDirectory = \
            os.path.dirname(self._instance.data["expectedFiles"][0])
        dln_job_info.JobDelay = "00:00:00"

        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "PYPE_USERNAME",
            "PYPE_DEV",
            "PYPE_LOG_NO_COLORS"
        ]

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **api.Session)
        for key in keys:
            val = environment.get(key)
            if val:
                dln_job_info.EnvironmentKeyValue = "{key}={value}".format(
                     key=key,
                     value=val)

        return dln_job_info

    def get_plugin_info(self):
        deadline_plugin_info = DeadlinePluginInfo()
        context = self._instance.context
        script_path = context.data["currentFile"]

        render_path = self._instance.data["expectedFiles"][0]

        if len(self._instance.data["expectedFiles"]) > 1:
            # replace frame ('000001') with Deadline's required '[#######]'
            # expects filename in format project_asset_subset_version.FRAME.ext
            render_dir = os.path.dirname(render_path)
            file_name = os.path.basename(render_path)
            arr = file_name.split('.')
            assert len(arr) == 3, \
                "Unable to parse frames from {}".format(file_name)
            hashed = '[{}]'.format(len(arr[1]) * "#")

            render_path = os.path.join(render_dir,
                                       '{}.{}.{}'.format(arr[0], hashed,
                                                         arr[2]))
            deadline_plugin_info.MultiProcess = True
        else:
            deadline_plugin_info.MultiProcess = False

        deadline_plugin_info.Comp = self._instance.data["comp_name"]
        deadline_plugin_info.Version = "17.5"
        deadline_plugin_info.SceneFile = script_path
        deadline_plugin_info.Output = render_path.replace("\\", "/")

        return attr.asdict(deadline_plugin_info)
