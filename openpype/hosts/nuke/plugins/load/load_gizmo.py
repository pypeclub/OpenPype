from avalon import api, style, io
import nuke
from avalon.nuke import lib as anlib
from avalon.nuke import containerise, update_container


class LoadGizmo(api.Loader):
    """Loading nuke Gizmo"""

    representations = ["gizmo"]
    families = ["gizmo"]

    label = "Load Gizmo"
    order = 0
    icon = "dropbox"
    color = style.colors.light
    node_color = "0x75338eff"

    def load(self, context, name, namespace, data):
        """
        Loading function to get Gizmo into node graph

        Arguments:
            context (dict): context of version
            name (str): name of the version
            namespace (str): asset name
            data (dict): compulsory attribute > not used

        Returns:
            nuke node: containerised nuke node object
        """

        # get main variables
        version = context['version']
        version_data = version.get("data", {})
        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        namespace = namespace or context['asset']['name']
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)

        # prepare data for imprinting
        # add additional metadata from the version to imprint to Avalon knob
        add_keys = ["frameStart", "frameEnd", "handleStart", "handleEnd",
                    "source", "author", "fps"]

        data_imprint = {"frameStart": first,
                        "frameEnd": last,
                        "version": vname,
                        "colorspaceInput": colorspace,
                        "objectName": object_name}

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # getting file path
        file = self.fname.replace("\\", "/")

        # adding nodes to node graph
        # just in case we are in group lets jump out of it
        nuke.endGroup()

        with anlib.maintained_selection():
            # add group from nk
            nuke.nodePaste(file)

            GN = nuke.selectedNode()

            GN["name"].setValue(object_name)

            return containerise(
                node=GN,
                name=name,
                namespace=namespace,
                context=context,
                loader=self.__class__.__name__,
                data=data_imprint)

    def update(self, container, representation):
        """Update the Loader's path

        Nuke automatically tries to reset some variables when changing
        the loader's path to a new file. These automatic changes are to its
        inputs:

        """

        # get main variables
        # Get version from io
        version = io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })
        # get corresponding node
        GN = nuke.toNode(container['objectName'])

        file = api.get_representation_path(representation).replace("\\", "/")
        name = container['name']
        version_data = version.get("data", {})
        vname = version.get("name", None)
        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        namespace = container['namespace']
        colorspace = version_data.get("colorspace", None)
        object_name = "{}_{}".format(name, namespace)

        add_keys = ["frameStart", "frameEnd", "handleStart", "handleEnd",
                    "source", "author", "fps"]

        data_imprint = {"representation": str(representation["_id"]),
                        "frameStart": first,
                        "frameEnd": last,
                        "version": vname,
                        "colorspaceInput": colorspace,
                        "objectName": object_name}

        for k in add_keys:
            data_imprint.update({k: version_data[k]})

        # adding nodes to node graph
        # just in case we are in group lets jump out of it
        nuke.endGroup()

        with anlib.maintained_selection():
            xpos = GN.xpos()
            ypos = GN.ypos()
            avalon_data = anlib.get_avalon_knob_data(GN)
            nuke.delete(GN)
            # add group from nk
            nuke.nodePaste(file)

            GN = nuke.selectedNode()
            anlib.set_avalon_knob_data(GN, avalon_data)
            GN.setXYpos(xpos, ypos)
            GN["name"].setValue(object_name)

        # get all versions in list
        versions = io.find({
            "type": "version",
            "parent": version["parent"]
        }).distinct('name')

        max_version = max(versions)

        # change color of node
        if version.get("name") not in [max_version]:
            GN["tile_color"].setValue(int("0xd88467ff", 16))
        else:
            GN["tile_color"].setValue(int(self.node_color, 16))

        self.log.info("udated to version: {}".format(version.get("name")))

        return update_container(GN, data_imprint)

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        from avalon.nuke import viewer_update_and_undo_stop
        node = nuke.toNode(container['objectName'])
        with viewer_update_and_undo_stop():
            nuke.delete(node)
