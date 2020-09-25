import os

import pyblish.api
import pythoncom
from avalon import photoshop


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by LayerSet and file metadata

    This collector takes into account assets that are associated with
    an LayerSet and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"
    """

    label = "Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    families_mapping = {
        "image": ["ftrack"]
    }

    def process(self, context):
        # Necessary call when running in a different thread which pyblish-qml
        # can be.
        pythoncom.CoInitialize()

        for layer in photoshop.get_layers_in_document():
            layer_data = photoshop.read(layer)

            # Skip layers without metadata.
            if layer_data is None:
                continue

            # Skip containers.
            if "container" in layer_data["id"]:
                continue

            child_layers = [*layer.Layers]
            if not child_layers:
                self.log.info("%s skipped, it was empty." % layer.Name)
                continue

            instance = context.create_instance(layer.Name)
            instance.append(layer)
            instance.data.update(layer_data)
            instance.data["families"] = self.families_mapping[
                layer_data["family"]
            ]
            instance.data["publish"] = layer.Visible

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])

            task = os.getenv("AVALON_TASK", None)
            instance.data["version_name"] = "{}_{}". \
                format(layer.Name, task)
