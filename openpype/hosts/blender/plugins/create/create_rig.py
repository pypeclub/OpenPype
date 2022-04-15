"""Create a rig asset."""

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops, dialog


class CreateRig(plugin.Creator):
    """Artist-friendly rig with controls to direct motion"""

    name = "rigMain"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"

    def get_selection_hierarchie(self):
        nodes = bpy.context.selected_objects
        objects = list()

        for obj in nodes:
            objects.append(obj)
            if obj.type != "ARMATURE":
                nodes.extend(list(obj.children))

        objects.reverse()
        return objects

    def process(self):
        """Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):
        all_in_container = True
        # Dialog box if use_selection is checked
        if (self.options or {}).get("useSelection"):
            # and not any objects selected
            if not lib.get_selection():
                all_in_container = dialog.use_selection_behaviour_dialog()
            # if any objects is selected
            # not set all the objects in the container
            else:
                all_in_container = False

        # Get info from data and create name value
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        # Get the scene collection and all the collection in the scene
        scene_collection = bpy.context.scene.collection

        # Get Instance Container or create it if it does not exist
        container = bpy.data.collections.get(name)
        if container is None:
            is_avalon_container = False
            if len(scene_collection.children) == 1:
                is_avalon_container = plugin.is_avalon_container(
                    scene_collection.children[0]
                )
            if (
                len(scene_collection.children) == 1
                and all_in_container
                and not is_avalon_container
            ):
                container = scene_collection.children[0]
                container.name = name
            else:
                container = bpy.data.collections.new(name=name)
                plugin.link_collection_to_collection(
                    container, scene_collection
                )

        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # Link the collections in the scene to the container
        # If the use selection option is checked
        if all_in_container:
            # If all the collection isn't already in the container
            if len(scene_collection.children) != 1:
                collections = scene_collection.children
                for collection in collections:
                    # if collection is not yet in the container
                    # And is not the container
                    if (
                        container.children.get(collection.name) is None
                        and container is not collection
                    ):
                        scene_collection.children.unlink(collection)
                        plugin.link_collection_to_collection(
                            collection, container
                        )

        # Add selected objects to container
        objects_to_link = list()
        # If the use selection option is checked
        if all_in_container:
            # Append object in the scene collection
            # In the objects_to_link list
            objects_to_link = scene_collection.objects
        else:
            selected = lib.get_selection()
            for object in selected:
                # Append object selected in the objects_to_link list
                objects_to_link.append(object)
        # If the use selection option is not checked

        for object in objects_to_link:
            # If the object is not yet in the container
            if object not in container.objects.values():
                # Find the users collection of the object
                for collection in object.users_collection:
                    # And unlink the object to its users collection
                    collection.objects.unlink(object)
                # Link the object to the container
                if object not in container.objects.values():
                    plugin.link_object_to_collection(object, container)
                # If the container is empty remove them
        if not container.objects and not container.children:
            bpy.data.collections.remove(container)
        return container
