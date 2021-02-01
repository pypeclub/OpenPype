# -*- coding: utf-8 -*-
"""Avalon/Pyblish plugin tools."""
import os
import inspect
import logging
import re
import json
import pype.api
import tempfile

from ..api import config


log = logging.getLogger(__name__)


def filter_pyblish_plugins(plugins):
    """Filter pyblish plugins by presets.

    This servers as plugin filter / modifier for pyblish. It will load plugin
    definitions from presets and filter those needed to be excluded.

    Args:
        plugins (dict): Dictionary of plugins produced by :mod:`pyblish-base`
            `discover()` method.

    """
    from pyblish import api

    host = api.current_host()

    presets = config.get_presets().get('plugins', {})

    # iterate over plugins
    for plugin in plugins[:]:
        # skip if there are no presets to process
        if not presets:
            continue

        file = os.path.normpath(inspect.getsourcefile(plugin))
        file = os.path.normpath(file)

        # host determined from path
        host_from_file = file.split(os.path.sep)[-3:-2][0]
        plugin_kind = file.split(os.path.sep)[-2:-1][0]

        try:
            config_data = presets[host]["publish"][plugin.__name__]
        except KeyError:
            try:
                config_data = presets[host_from_file][plugin_kind][plugin.__name__]  # noqa: E501
            except KeyError:
                continue

        for option, value in config_data.items():
            if option == "enabled" and value is False:
                log.info('removing plugin {}'.format(plugin.__name__))
                plugins.remove(plugin)
            else:
                log.info('setting {}:{} on plugin {}'.format(
                    option, value, plugin.__name__))

                setattr(plugin, option, value)


def source_hash(filepath, *args):
    """Generate simple identifier for a source file.
    This is used to identify whether a source file has previously been
    processe into the pipeline, e.g. a texture.
    The hash is based on source filepath, modification time and file size.
    This is only used to identify whether a specific source file was already
    published before from the same location with the same modification date.
    We opt to do it this way as opposed to Avalanch C4 hash as this is much
    faster and predictable enough for all our production use cases.
    Args:
        filepath (str): The source file path.
    You can specify additional arguments in the function
    to allow for specific 'processing' values to be included.
    """
    # We replace dots with comma because . cannot be a key in a pymongo dict.
    file_name = os.path.basename(filepath)
    time = str(os.path.getmtime(filepath))
    size = str(os.path.getsize(filepath))
    return "|".join([file_name, time, size] + list(args)).replace(".", ",")


def get_unique_layer_name(layers, name):
    """
        Gets all layer names and if 'name' is present in them, increases
        suffix by 1 (eg. creates unique layer name - for Loader)
    Args:
        layers (list): of strings, names only
        name (string):  checked value

    Returns:
        (string): name_00X (without version)
    """
    names = {}
    for layer in layers:
        layer_name = re.sub(r'_\d{3}$', '', layer)
        if layer_name in names.keys():
            names[layer_name] = names[layer_name] + 1
        else:
            names[layer_name] = 1
    occurrences = names.get(name, 0)

    return "{}_{:0>3d}".format(name, occurrences + 1)


def get_background_layers(file_url):
    """
        Pulls file name from background json file, enrich with folder url for
        AE to be able import files.

        Order is important, follows order in json.

        Args:
            file_url (str): abs url of background json

        Returns:
            (list): of abs paths to images
    """
    with open(file_url) as json_file:
        data = json.load(json_file)

    layers = list()
    bg_folder = os.path.dirname(file_url)
    for child in data['children']:
        if child.get("filename"):
            layers.append(os.path.join(bg_folder, child.get("filename")).
                          replace("\\", "/"))
        else:
            for layer in child['children']:
                if layer.get("filename"):
                    layers.append(os.path.join(bg_folder,
                                               layer.get("filename")).
                                  replace("\\", "/"))
    return layers


def oiio_supported():
    """
        Checks if oiiotool is configured for this platform.

        Expects full path to executable.

        'should_decompress' will throw exception if configured,
        but not present or not working.
        Returns:
            (bool)
    """
    oiio_path = os.getenv("PYPE_OIIO_PATH", "")
    if not oiio_path or not os.path.exists(oiio_path):
        log.debug("OIIOTool is not configured or not present at {}".
                  format(oiio_path))
        return False

    return True


def decompress(target_dir, file_url,
               input_frame_start=None, input_frame_end=None, log=None):
    """
        Decompresses DWAA 'file_url' .exr to 'target_dir'.

        Creates uncompressed files in 'target_dir', they need to be cleaned.

        File url could be for single file or for a sequence, in that case
        %0Xd will be as a placeholder for frame number AND input_frame* will
        be filled.
        In that case single oiio command with '--frames' will be triggered for
        all frames, this should be faster then looping and running sequentially

        Args:
            target_dir (str): extended from stagingDir
            file_url (str): full urls to source file (with or without %0Xd)
            input_frame_start (int) (optional): first frame
            input_frame_end (int) (optional): last frame
            log (Logger) (optional): pype logger
    """
    is_sequence = input_frame_start is not None and \
        input_frame_end is not None and \
        (int(input_frame_end) > int(input_frame_start))

    oiio_cmd = []
    oiio_cmd.append(os.getenv("PYPE_OIIO_PATH"))

    oiio_cmd.append("--compression none")

    base_file_name = os.path.basename(file_url)
    oiio_cmd.append(file_url)

    if is_sequence:
        oiio_cmd.append("--frames {}-{}".format(input_frame_start,
                                                input_frame_end))

    oiio_cmd.append("-o")
    oiio_cmd.append(os.path.join(target_dir, base_file_name))

    subprocess_exr = " ".join(oiio_cmd)

    if not log:
        log = logging.getLogger(__name__)

    log.debug("Decompressing {}".format(subprocess_exr))
    pype.api.subprocess(
        subprocess_exr, shell=True, logger=log
    )


def get_decompress_dir():
    """
        Creates temporary folder for decompressing.
        Its local, in case of farm it is 'local' to the farm machine.

        Should be much faster, needs to be cleaned up later.
    """
    return os.path.normpath(
        tempfile.mkdtemp(prefix="pyblish_tmp_")
    )


def should_decompress(file_url):
    """
        Tests that 'file_url' is compressed with DWAA.

        Uses 'oiio_supported' to check that OIIO tool is available for this
        platform.

        Shouldn't throw exception as oiiotool is guarded by check function.
        Currently implemented this way as there is no support for Mac and Linux
        In the future, it should be more strict and throws exception on
        misconfiguration.

        Args:
            file_url (str): path to rendered file (in sequence it would be
                first file, if that compressed it is expected that whole seq
                will be too)
        Returns:
            (bool): 'file_url' is DWAA compressed and should be decompressed
                and we can decompress (oiiotool supported)
    """
    if oiio_supported():
        output = pype.api.subprocess([
            os.getenv("PYPE_OIIO_PATH"),
            "--info", "-v", file_url])
        return "compression: \"dwaa\"" in output or \
            "compression: \"dwab\"" in output

    return False
