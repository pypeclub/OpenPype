from openpype.client import get_asset_by_name
from openpype.pipeline import LauncherAction
from openpype_modules.clockify.clockify_api import ClockifyAPI
from openpype.lib.local_settings import OpenPypeSecureRegistry


class ClockifyStart(LauncherAction):

    name = "clockify_start_timer"
    label = "Clockify - Start Timer"
    icon = "app_icons/clockify.png"
    order = 500
    clockapi = ClockifyAPI()
    clockapi.set_api()
    user_id = clockapi.user_id
    workspace_id = clockapi.workspace_id

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_TASK" in session:
            return True
        return False

    def process(self, session, **kwargs):
        user_id = self.user_id
        workspace_id = self.workspace_id
        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]
        task_name = session["AVALON_TASK"]

        description = asset_name
        asset_doc = get_asset_by_name(
            project_name, asset_name, fields=["data.parents"]
        )
        if asset_doc is not None:
            desc_items = asset_doc.get("data", {}).get("parents", [])
            desc_items.append(asset_name)
            desc_items.append(task_name)
            description = "/".join(desc_items)

        project_id = self.clockapi.get_project_id(project_name, workspace_id)
        tag_ids = []
        tag_ids.append(self.clockapi.get_tag_id(task_name, workspace_id))
        self.clockapi.start_time_entry(
            description, project_id, tag_ids=tag_ids, 
            workspace_id=workspace_id, user_id=user_id
        )
