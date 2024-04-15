# -*- coding: utf-8 -*-
import pyblish.api
from pymxs import runtime as rt
from openpype.hosts.max.api.lib import (
    get_tyflow_export_particle_operators
)


class CollectFrameRange(pyblish.api.InstancePlugin):
    """Collect Frame Range."""

    order = pyblish.api.CollectorOrder + 0.011
    label = "Collect Frame Range"
    hosts = ['max']
    families = ["camera", "maxrender",
                "pointcache", "pointcloud",
                "review", "tycache",
                "tyspline", "redshiftproxy"]

    def process(self, instance):
        if instance.data["family"] == "maxrender":
            instance.data["frameStartHandle"] = int(rt.rendStart)
            instance.data["frameEndHandle"] = int(rt.rendEnd)

        elif instance.data["family"] == "tycache" or "tyspline":
            operator = instance.data["operator"]
            instance.data["frameStartHandle"] = rt.getProperty(operator, "frameStart")
            instance.data["frameEndHandle"] = rt.getProperty(operator, "frameEnd")

        else:
            instance.data["frameStartHandle"] = int(rt.animationRange.start)
            instance.data["frameEndHandle"] = int(rt.animationRange.end)
