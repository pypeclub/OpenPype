import os

import pyblish.api

from avalon import aftereffects


class CollectAudio(pyblish.api.ContextPlugin):
    """Inject audio file url for rendered composition into context.
        Needs to run AFTER 'collect_render'. Use collected comp_id to check
        if there is an AVLayer in this composition
    """

    order = pyblish.api.CollectorOrder + 0.499
    label = "Collect Audio"
    hosts = ["aftereffects"]

    def process(self, context):
        for instance in context:
            if instance.data["family"] == 'render.farm':
                comp_id = instance.data["comp_id"]
                if not comp_id:
                    self.log.debug("No comp_id filled in instance")
                    return
                context.data["audioFile"] = os.path.normpath(
                    aftereffects.stub().get_audio_url(comp_id)
                ).replace("\\", "/")
