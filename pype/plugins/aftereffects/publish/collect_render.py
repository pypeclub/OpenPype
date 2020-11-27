from pype.lib import abstract_collect_render
from pype.lib.abstract_collect_render import RenderInstance
import pyblish.api
import attr
import os

from avalon import aftereffects


@attr.s
class AERenderInstance(RenderInstance):
    # extend generic, composition name is needed
    comp_name = attr.ib(default=None)
    comp_id = attr.ib(default=None)


class CollectAERender(abstract_collect_render.AbstractCollectRender):

    order = pyblish.api.CollectorOrder + 0.498
    label = "Collect After Effects Render Layers"
    hosts = ["aftereffects"]

    padding_width = 6
    rendered_extension = 'png'

    def get_instances(self, context):
        instances = []

        current_file = context.data["currentFile"]
        version = context.data["version"]
        asset_entity = context.data["assetEntity"]
        project_entity = context.data["projectEntity"]

        compositions = aftereffects.stub().get_items(True)
        compositions_by_id = {item.id: item for item in compositions}
        for item_id, inst in aftereffects.stub().get_metadata().items():
            schema = inst.get('schema')
            # loaded asset container skip it
            if schema and 'container' in schema:
                continue

            work_area_info = aftereffects.stub().get_work_area(int(item_id))
            frameStart = round(float(work_area_info.workAreaStart) *
                               float(work_area_info.frameRate))

            frameEnd = round(float(work_area_info.workAreaStart) *
                             float(work_area_info.frameRate) +
                             float(work_area_info.workAreaDuration) *
                             float(work_area_info.frameRate))

            if inst["family"] == "render" and inst["active"]:
                instance = AERenderInstance(
                    family="render.farm",  # other way integrate would catch it
                    families=["render.farm"],
                    version=version,
                    time="",
                    source=current_file,
                    label="{} - farm".format(inst["subset"]),
                    subset=inst["subset"],
                    asset=context.data["assetEntity"]["name"],
                    attachTo=False,
                    setMembers='',
                    publish=True,
                    renderer='aerender',
                    name=inst["subset"],
                    resolutionWidth=asset_entity["data"].get(
                        "resolutionWidth",
                        project_entity["data"]["resolutionWidth"]),
                    resolutionHeight=asset_entity["data"].get(
                        "resolutionHeight",
                        project_entity["data"]["resolutionHeight"]),
                    pixelAspect=1,
                    tileRendering=False,
                    tilesX=0,
                    tilesY=0,
                    frameStart=frameStart,
                    frameEnd=frameEnd,
                    frameStep=1,
                    toBeRenderedOn='deadline'
                )

                comp = compositions_by_id.get(int(item_id))
                if not comp:
                    raise ValueError("There is no composition for item {}".
                                     format(item_id))
                instance.comp_name = comp.name
                instance.comp_id = item_id
                instance._anatomy = context.data["anatomy"]
                instance.anatomyData = context.data["anatomyData"]

                instance.outputDir = self._get_output_dir(instance)

                instances.append(instance)

        return instances

    def get_expected_files(self, render_instance):
        """
            Returns list of rendered files that should be created by
            Deadline. These are not published directly, they are source
            for later 'submit_publish_job'.

        Args:
            render_instance (RenderInstance): to pull anatomy and parts used
                in url

        Returns:
            (list) of absolut urls to rendered file
        """
        start = render_instance.frameStart
        end = render_instance.frameEnd

        # pull file name from Render Queue Output module
        render_q = aftereffects.stub().get_render_info()
        _, ext = os.path.splitext(os.path.basename(render_q.file_name))
        base_dir = self._get_output_dir(render_instance)
        expected_files = []
        if "#" not in render_q.file_name:  # single frame (mov)W
            path = os.path.join(base_dir, "{}_{}_{}.{}".format(
                render_instance.asset,
                render_instance.subset,
                "v{:03d}".format(render_instance.version),
                ext.replace('.', '')
            ))
            expected_files.append(path)
        else:
            for frame in range(start, end + 1):
                path = os.path.join(base_dir, "{}_{}_{}.{}.{}".format(
                    render_instance.asset,
                    render_instance.subset,
                    "v{:03d}".format(render_instance.version),
                    str(frame).zfill(self.padding_width),
                    ext.replace('.', '')
                ))
                expected_files.append(path)
        return expected_files

    def _get_output_dir(self, render_instance):
        """
            Returns dir path of rendered files, used in submit_publish_job
            for metadata.json location.
            Should be in separate folder inside of work area.

        Args:
            render_instance (RenderInstance):

        Returns:
            (str): absolute path to rendered files
        """
        # render to folder of workfile
        base_dir = os.path.dirname(render_instance.source)
        file_name, _ = os.path.splitext(
            os.path.basename(render_instance.source))
        base_dir = os.path.join(base_dir, 'renders', 'aftereffects', file_name)

        # for submit_publish_job
        return base_dir
