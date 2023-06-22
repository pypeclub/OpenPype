"""Host API required for Work Files."""

from pathlib import Path
from typing import List, Optional

import bpy

from openpype.pipeline import legacy_io
from openpype.client.entities import get_last_version_by_subset_name
from openpype.settings.lib import get_project_settings


class OpenFileCacher:
    """Store information about opening file.

    When file is opening QApplcation events should not be processed.
    """
    opening_file = False

    @classmethod
    def post_load(cls):
        cls.opening_file = False

    @classmethod
    def set_opening(cls):
        cls.opening_file = True


def open_file(filepath: str) -> Optional[str]:
    """Open the scene file in Blender."""
    OpenFileCacher.set_opening()

    preferences = bpy.context.preferences
    load_ui = preferences.filepaths.use_load_ui
    use_scripts = preferences.filepaths.use_scripts_auto_execute
    result = bpy.ops.wm.open_mainfile(
        filepath=filepath,
        load_ui=load_ui,
        use_scripts=use_scripts,
    )

    if result == {'FINISHED'}:
        return filepath
    return None


def save_file(filepath: str, copy: bool = False) -> Optional[str]:
    """Save the open scene file."""

    result = bpy.ops.wm.save_as_mainfile(
        filepath=filepath,
        compress=get_compress_setting(),
        relative_remap=bpy.context.preferences.filepaths.use_relative_paths,
        copy=copy,
    )

    if result == {'FINISHED'}:
        return filepath
    return None


def current_file() -> Optional[str]:
    """Return the path of the open scene file."""

    current_filepath = bpy.data.filepath
    if Path(current_filepath).is_file():
        return current_filepath
    return None


def has_unsaved_changes() -> bool:
    """Does the open scene file have unsaved changes?"""

    return bpy.data.is_dirty


def get_compress_setting():
    project_name = legacy_io.active_project()
    project_setting = get_project_settings(project_name)
    return project_setting["blender"]["general"].get(
        "compress", bpy.context.preferences.filepaths.use_file_compression
    )


def file_extensions() -> List[str]:
    """Return the supported file extensions for Blender scene files."""

    return [".blend"]


def work_root(session: dict) -> str:
    """Return the default root to browse for work files."""

    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        return str(Path(work_dir, scene_dir))
    return work_dir


def check_workfile_up_to_date() -> bool:
    """Check if the current workfile is out of date.

    This is based on last modification date, so if a user modifies an out of
    date workfile, this will return `False`. Also, in case of partial publish,
    this will return `True`.

    Returns:
        bool: True if the current workfile is up to date.
    """
    session = legacy_io.Session

    # Get date and time of the latest published workfile
    last_published_version = get_last_version_by_subset_name(
        legacy_io.active_project(),
        f"workfile{session.get('AVALON_TASK')}",
        asset_name=session.get("AVALON_ASSET"),
        fields=["data"]
    )

    # Check if version exists
    if not last_published_version:
        return True

    scene = bpy.context.scene

    last_published_time = last_published_version["data"]["time"]
    if scene.get("op_published_time"):
        return last_published_time <= scene["op_published_time"]
    else:
        return False
