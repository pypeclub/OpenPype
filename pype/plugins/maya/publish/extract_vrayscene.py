# -*- coding: utf-8 -*-
"""Extract vrayscene from specified families."""
import os
import re

import avalon.maya
import pype.api
from pype.hosts.maya.render_setup_tools import export_in_rs_layer

from maya import cmds


class ExtractVrayscene(pype.api.Extractor):
    """Extractor for vrscene."""

    label = "VRay Scene (.vrscene)"
    hosts = ["maya"]
    families = ["vrayscene_layer"]

    def process(self, instance):
        """Plugin entry point."""
        if instance.data.get("exportOnFarm"):
            self.log.info("vrayscenes will be exported on farm.")
            raise NotImplementedError(
                "exporting vrayscenes is not implemented")

        # handle sequence
        if instance.data.get("vraySceneMultipleFiles"):
            self.log.info("vrayscenes will be exported on farm.")
            raise NotImplementedError(
                "exporting vrayscene sequences not implemented yet")

        vray_settings = cmds.ls(type="VRaySettingsNode")
        if not vray_settings:
            node = cmds.createNode("VRaySettingsNode")
        else:
            node = vray_settings[0]

        # setMembers on vrayscene_layer shoudl contain layer name.
        layer_name = instance.data.get("layer")

        staging_dir = self.staging_dir(instance)
        self.log.info("staging: {}".format(staging_dir))
        template = cmds.getAttr("{}.vrscene_filename".format(node))
        start_frame = instance.data.get(
            "frameStartHandle") if instance.data.get(
                "vraySceneMultipleFiles") else None
        formatted_name = self.format_vray_output_filename(
            os.path.basename(instance.data.get("source")),
            layer_name,
            template,
            start_frame
        )

        file_path = os.path.join(
            staging_dir, "vrayscene", *formatted_name.split("/"))

        # Write out vrscene file
        self.log.info("Writing: '%s'" % file_path)
        with avalon.maya.maintained_selection():
            if "*" not in instance.data["setMembers"]:
                export_in_rs_layer(
                    file_path,
                    instance.data["setMembers"],
                    export=lambda: cmds.file(
                        file_path, type="V-Ray Scene", pr=True, es=True))

            else:
                cmds.file(file_path, type="V-Ray Scene", pr=True, ea=True)

        # render_setup.switchToLayer(current_layer)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        files = file_path

        representation = {
            'name': 'vrscene',
            'ext': 'vrscene',
            'files': os.path.basename(files),
            "stagingDir": os.path.dirname(files),
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s"
                      % (instance.name, staging_dir))

    @staticmethod
    def format_vray_output_filename(
            filename, layer, template, start_frame=None):
        """Format the expected output file of the Export job.

        Example:
            filename: /mnt/projects/foo/shot010_v006.mb
            template: <Scene>/<Layer>/<Layer>
            result: "shot010_v006/CHARS/CHARS.vrscene"

        Args:
            filename (str): path to scene file.
            layer (str): layer name.
            template (str): token template.
            start_frame (int, optional): start frame - if set we use
                mutliple files export mode.

        Returns:
            str: formatted path.

        """
        # format template to match pythons format specs
        template = re.sub(r"<(\w+?)>", r"{\1}", template.lower())

        # Ensure filename has no extension
        file_name, _ = os.path.splitext(filename)
        mapping = {
            "scene": file_name,
            "layer": layer
        }

        output_path = template.format(**mapping)

        if start_frame:
            filename_zero = "{}_{:04d}.vrscene".format(
                output_path, start_frame)
        else:
            filename_zero = "{}.vrscene".format(output_path)

        result = filename_zero.replace("\\", "/")

        return result
