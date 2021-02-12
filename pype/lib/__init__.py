# -*- coding: utf-8 -*-
"""Pype lib module."""

from .deprecated import (
    get_avalon_database,
    set_io_database
)

from .env_tools import (
    env_value_to_bool,
    get_paths_from_environ
)

from .avalon_context import (
    is_latest,
    any_outdated,
    get_asset,
    get_hierarchy,
    get_linked_assets,
    get_latest_version,
    BuildWorkfile,
    get_creator_by_name
)

from .hooks import PypeHook, execute_hook

from .applications import (
    ApplicationLaunchFailed,
    ApplictionExecutableNotFound,
    ApplicationNotFound,
    ApplicationManager,
    launch_application,
    ApplicationAction,
    _subprocess
)

from .plugin_tools import (
    filter_pyblish_plugins,
    source_hash,
    get_unique_layer_name,
    get_background_layers,
    oiio_supported,
    decompress,
    get_decompress_dir,
    should_decompress
)

from .path_tools import (
    version_up,
    get_version_from_path,
    get_last_version_from_path
)

from .ffmpeg_utils import (
    get_ffmpeg_tool_path,
    ffprobe_streams
)

from .packaging import make_workload_package

__all__ = [
    "get_avalon_database",
    "set_io_database",

    "env_value_to_bool",
    "get_paths_from_environ",

    "is_latest",
    "any_outdated",
    "get_asset",
    "get_hierarchy",
    "get_linked_assets",
    "get_latest_version",
    "BuildWorkfile",
    "get_creator_by_name",

    "PypeHook",
    "execute_hook",

    "ApplicationLaunchFailed",
    "ApplictionExecutableNotFound",
    "ApplicationNotFound",
    "ApplicationManager",
    "launch_application",
    "ApplicationAction",

    "filter_pyblish_plugins",
    "get_unique_layer_name",
    "get_background_layers",
    "oiio_supported",
    "decompress",
    "get_decompress_dir",
    "should_decompress",

    "version_up",
    "get_version_from_path",
    "get_last_version_from_path",

    "ffprobe_streams",
    "get_ffmpeg_tool_path",

    "source_hash",
    "_subprocess",

    "make_workload_package"
]
