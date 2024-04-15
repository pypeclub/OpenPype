import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


class ValidateTyFlowData(pyblish.api.InstancePlugin):
    """Validate TyFlow plugins or relevant operators are set correctly."""

    order = pyblish.api.ValidatorOrder
    families = ["pointcloud"]
    hosts = ["max"]
    label = "TyFlow Data"

    def process(self, instance):
        """
        Notes:
            1. Validate the container only include tyFlow objects
            2. Validate if tyFlow operator Export Particle exists

        """
        errors = []
        invalid_object = self.get_tyflow_object(instance)
        if invalid_object:
            errors.append(f"Non tyFlow object found: {invalid_object}")

        invalid_operator = self.get_tyflow_operator(instance)
        if invalid_operator:
            errors.append(invalid_operator)
        if errors:
            bullet_point_invalid_statement = "\n".join(
                "- {}".format(error) for error
                in errors
            )
            report = (
                "TyFlow Data has invalid values(s).\n\n"
                f"{bullet_point_invalid_statement}\n\n"
            )
            raise PublishValidationError(
                report,
                title="Invalid value(s) for TyFlow Data")


    def get_tyflow_object(self, instance):
        """Get the nodes which are not tyFlow object(s)
        and editable mesh(es)

        Args:
            instance (pyblish.api.Instance): instance

        Returns:
            list: invalid nodes which are not tyFlow
                object(s) and editable mesh(es).
        """
        container = instance.data["instance_node"]
        self.log.debug(f"Validating tyFlow container for {container}")

        allowed_classes = [rt.tyFlow, rt.Editable_Mesh]
        return [
            member for member in instance.data["members"]
            if rt.ClassOf(member) not in allowed_classes
        ]

    def get_tyflow_operator(self, instance):
        """Check if the Export Particle Operators in the node
        connections.

        Args:
            instance (str): instance node

        Returns:
            invalid(list): list of invalid nodes which are not
            export particle operators or with the invalid export
            modes
        """
        invalid = []
        members = instance.data["members"]
        for member in members:
            obj = member.baseobject
            # There must be at least one animation with export
            # particles enabled
            anim_names = rt.GetSubAnimNames(obj)
            has_export_particle = False
            for anim_name in anim_names:
                # get name of the related tyFlow node
                sub_anim = rt.GetSubAnim(obj, anim_name)
                # Isolate only the events
                if not rt.isKindOf(sub_anim, rt.tyEvent):
                    continue
                # Look through all the nodes in the events
                node_names = rt.GetSubAnimNames(sub_anim)
                for node_name in node_names:
                    node_sub_anim = rt.GetSubAnim(sub_anim, node_name)
                    if rt.hasProperty(node_sub_anim, "exportMode"):
                        # check if the current export mode of the operator
                        # is valid for the tycache export.
                        if node_sub_anim.exportMode == 1 or \
                            node_sub_anim.exportMode == 2 or \
                                node_sub_anim.exportMode == 6:
                            has_export_particle = True
                            break

            if has_export_particle:
                break

            if not has_export_particle:
                invalid.append(f"{member.name} has invalid Export Mode.")

        return invalid


class ValidateTyFlowTySplineData(ValidateTyFlowData):
    families = ["tycache", "tyspline"]
    hosts = ["max"]
    label = "TyFlow Data (TyCache)"

    def process(self, instance):
        """
        Notes:
            1. Validate the container only include tyFlow objects
            2. Validate if tyFlow operator Export Particle exists
            3. Validate if tyFlow operator Spline Paths exists

        """
        errors = []
        invalid_operator = self.get_tyflow_operator(instance)
        if invalid_operator:
            errors.append(invalid_operator)
        no_spline_nodes = self.get_invalid_tycache_spline_nodes(instance)
        if no_spline_nodes:
            errors.append(no_spline_nodes)
        if errors:
            bullet_point_invalid_statement = "\n".join(
                "- {}".format(error) for error
                in errors
            )
            report = (
                "TyFlow Data has invalid values(s).\n\n"
                f"{bullet_point_invalid_statement}\n\n"
            )
            raise PublishValidationError(
                report,
                title="Invalid value(s) for TyFlow Data")

    def get_invalid_tycache_spline_nodes(self, instance):
        """Check if there is spline paths operators before the export

        Args:
            instance (pyblish.api.Instance): instance

        Returns:
            invalid: list of invalid nodes which are not
            with spline paths operators
        """
        invalid = []
        node_sub_anim = instance.data["operator"]
        if node_sub_anim is not None:
            if rt.hasProperty(node_sub_anim, "exportMode"):
                # check if the current export mode of the operator
                # is valid for the tycache export.
                if instance.data["exportMode"] == 2:
                    family = instance.data["productType"]
                    self.log.debug(
                        "Skipping to check tycache spline"
                        f" nodes for {family} instance")
                    return invalid
            if not rt.hasProperty(node_sub_anim, "splinePathsNode"):
                invalid.append(
                    f"{node_sub_anim.name} has no tycache spline nodes.")

        return invalid

    def get_tyflow_operator(self, instance):
        invalid = []
        node_sub_anim = instance.data["operator"]
        has_export_particle = []
        if node_sub_anim is not None:
            if rt.hasProperty(node_sub_anim, "exportMode"):
                if node_sub_anim.exportMode == 2 or \
                        node_sub_anim.exportMode == 6:
                    has_export_particle.append("True")
                else:
                    has_export_particle.append("False")
                    if "False" in has_export_particle:
                        invalid.append(
                            f"{node_sub_anim.name} has invalid Export Mode.")

        return invalid
