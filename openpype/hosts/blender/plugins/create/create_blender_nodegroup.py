"""Create a blender nodegroup asset."""
import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.utils import NODETREE_TYPES


class CreateBlenderNodegroup(plugin.Creator):
    """A grouped package of loaded content"""

    name = "blenderNodegroupMain"
    label = "Blender Nodegroup"
    family = "blender.nodegroup"
    icon = "microchip"

    bl_types = frozenset({bpy.types.Object, *NODETREE_TYPES})
