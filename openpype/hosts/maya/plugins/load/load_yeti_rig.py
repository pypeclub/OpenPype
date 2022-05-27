import os
from collections import defaultdict

from openpype.api import get_project_settings
import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api import lib

from openpype.lib import get_creator_by_name
from openpype.pipeline import (
    legacy_io,
    legacy_create,
)


class YetiRigLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """
    This loader will load Yeti rig. You can select something in scene and if it
    has same ID as mesh published with rig, their shapes will be linked
    together.
    """

    families = ["yetiRig"]
    representations = ["ma"]

    label = "Load Yeti Rig"
    order = -9
    icon = "code-fork"
    color = "orange"

    yeti_cache_creator_name = "CreateYetiCache"

    def process_reference(
            self, context, name=None, namespace=None, options=None):

        import maya.cmds as cmds

        # get roots of selected hierarchies
        selected_roots = []
        for sel in cmds.ls(sl=True, long=True):
            selected_roots.append(sel.split("|")[1])

        # get all objects under those roots
        selected_hierarchy = []
        for root in selected_roots:
            selected_hierarchy.append(cmds.listRelatives(
                                      root,
                                      allDescendents=True) or [])

        # flatten the list and filter only shapes
        shapes_flat = []
        for root in selected_hierarchy:
            shapes = cmds.ls(root, long=True, type="mesh") or []
            for shape in shapes:
                shapes_flat.append(shape)

        # create dictionary of cbId and shape nodes
        scene_lookup = defaultdict(list)
        for node in shapes_flat:
            cb_id = lib.get_id(node)
            scene_lookup[cb_id] = node

        # load rig
        with lib.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        # for every shape node we've just loaded find matching shape by its
        # cbId in selection. If found outMesh of scene shape will connect to
        # inMesh of loaded shape.
        for destination_node in nodes:
            source_node = scene_lookup[lib.get_id(destination_node)]
            if source_node:
                self.log.info("found: {}".format(source_node))
                self.log.info(
                    "creating connection to {}".format(destination_node))

                cmds.connectAttr("{}.outMesh".format(source_node),
                                 "{}.inMesh".format(destination_node),
                                 force=True)

        groupName = "{}:{}".format(namespace, name)

        settings = get_project_settings(os.environ['AVALON_PROJECT'])
        colors = settings['maya']['load']['colors']

        c = colors.get('yetiRig')
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                (float(c[0])/255),
                (float(c[1])/255),
                (float(c[2])/255)
            )
        self[:] = nodes

        # Automatically create in instance to allow publishing the loaded
        # yeti rig into a yeti cache
        self._create_yeti_cache_instance(nodes, subset=namespace)

        return nodes

    def _create_yeti_cache_instance(self, nodes, subset):

        from maya import cmds

        # Find the roots amongst the loaded nodes
        yeti_nodes = cmds.ls(nodes, type="pgYetiMaya", long=True)
        assert yeti_nodes, "No pgYetiMaya nodes in rig, this is a bug."

        self.log.info("Creating subset: {}".format(subset))

        # Create the animation instance
        creator_plugin = get_creator_by_name(self.yeti_cache_creator_name)
        with lib.maintained_selection():
            cmds.select(yeti_nodes, noExpand=True)
            legacy_create(
                creator_plugin,
                name=subset,
                asset=legacy_io.Session["AVALON_ASSET"],
                options={"useSelection": True}
            )
