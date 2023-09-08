from openpype.pipeline import CreatedInstance

from openpype.lib import BoolDef
import openpype.hosts.photoshop.api as api
from openpype.hosts.photoshop.lib import PSAutoCreator
from openpype.pipeline.create import get_subset_name
from openpype.client import get_asset_by_name


class AutoImageCreator(PSAutoCreator):
    """Creates flatten image from all visible layers.

    Used in simplified publishing as auto created instance.
    Must be enabled in Setting and template for subset name provided
    """
    identifier = "auto_image"
    family = "image"

    # Settings
    default_variant = ""
    # - Mark by default instance for review
    mark_for_review = True
    active_on_create = True

    def create(self, options=None):
        existing_instance = None
        for instance in self.create_context.instances:
            if instance.creator_identifier == self.identifier:
                existing_instance = instance
                break

        context = self.create_context
        project_name = context.get_current_project_name()
        asset_name = context.get_current_asset_name()
        task_name = context.get_current_task_name()
        host_name = context.host_name
        asset_doc = get_asset_by_name(project_name, asset_name)

        if existing_instance is None:
            subset_name = get_subset_name(
                self.family, self.default_variant, task_name, asset_doc,
                project_name, host_name
            )

            publishable_ids = [layer.id for layer in api.stub().get_layers()
                               if layer.visible]
            data = {
                "asset": asset_name,
                "task": task_name,
                # ids are "virtual" layers, won't get grouped as 'members' do
                # same difference in color coded layers in WP
                "ids": publishable_ids
            }

            if not self.active_on_create:
                data["active"] = False

            creator_attributes = {"mark_for_review": self.mark_for_review}
            data.update({"creator_attributes": creator_attributes})

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(new_instance)
            api.stub().imprint(new_instance.get("instance_id"),
                               new_instance.data_to_store())

        elif (  # existing instance from different context
            existing_instance["asset"] != asset_name
            or existing_instance["task"] != task_name
        ):
            subset_name = get_subset_name(
                self.family, self.default_variant, task_name, asset_doc,
                project_name, host_name
            )

            existing_instance["asset"] = asset_name
            existing_instance["task"] = task_name
            existing_instance["subset"] = subset_name

            api.stub().imprint(existing_instance.get("instance_id"),
                               existing_instance.data_to_store())

    def get_pre_create_attr_defs(self):
        return [
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            )
        ]

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "mark_for_review",
                label="Review"
            )
        ]

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings["photoshop"]["create"]["AutoImageCreator"]
        )

        self.active_on_create = plugin_settings["active_on_create"]
        self.default_variant = plugin_settings["default_variant"]
        self.mark_for_review = plugin_settings["mark_for_review"]
        self.enabled = plugin_settings["enabled"]

    def get_detail_description(self):
        return """Creator for flatten image.

        Studio might configure simple publishing workflow. In that case
        `image` instance is automatically created which will publish flat
        image from all visible layers.

        Artist might disable this instance from publishing or from creating
        review for it though.
        """

    def collect_instances(self):
        """Overwrite method to refresh all visible layer ids."""
        for instance_data in cache_and_get_instances(self):
            creator_id = instance_data.get("creator_identifier")

            if creator_id == self.identifier:
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

