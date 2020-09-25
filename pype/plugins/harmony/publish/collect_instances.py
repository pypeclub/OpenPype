import json

import pyblish.api
from avalon import harmony


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by nodes metadata.

    This collector takes into account assets that are associated with
    a composite node and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"
    """

    label = "Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["harmony"]
    families_mapping = {
        "render": ["image", "review"],
        "scene": ["scene", "ftrack"],
        "palette": ["palette", "ftrack"]
    }

    pair_media = True

    def process(self, context):
        nodes = harmony.send(
            {"function": "node.subNodes", "args": ["Top"]}
        )["result"]

        for node in nodes:
            data = harmony.read(node)

            # Skip non-tagged nodes.
            if not data:
                continue

            # Skip containers.
            if "container" in data["id"]:
                continue

            instance = context.create_instance(node.split("/")[-1])
            instance.append(node)
            instance.data.update(data)
            instance.data["publish"] = harmony.send(
                {"function": "node.getEnable", "args": [node]}
            )["result"]
            instance.data["families"] = self.families_mapping[data["family"]]

            # If set in plugin, pair the scene Version in ftrack with
            # thumbnails and review media.
            if (self.pair_media and
                instance.data["family"] == "scene"):
                context.data["scene_instance"] = instance

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info(
                "Found: \"{0}\": \n{1}".format(
                    instance.data["name"], json.dumps(instance.data, indent=4)
                )
            )
