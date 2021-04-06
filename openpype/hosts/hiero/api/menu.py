import os
import sys
import hiero.core
from openpype.api import Logger
from avalon.api import Session
from hiero.ui import findMenuAction

from . import tags

log = Logger().get_logger(__name__)

self = sys.modules[__name__]
self._change_context_menu = None


def update_menu_task_label(*args):
    """Update the task label in Avalon menu to current session"""

    object_name = self._change_context_menu
    found_menu = findMenuAction(object_name)

    if not found_menu:
        log.warning("Can't find menuItem: {}".format(object_name))
        return

    label = "{}, {}".format(Session["AVALON_ASSET"],
                            Session["AVALON_TASK"])

    menu = found_menu.menu()
    self._change_context_menu = label
    menu.setTitle(label)


def menu_install():
    """
    Installing menu into Hiero

    """
    from . import (
        publish, launch_workfiles_app, reload_config,
        apply_colorspace_project, apply_colorspace_clips
    )
    # here is the best place to add menu
    from avalon.tools import cbloader, creator, sceneinventory
    from avalon.vendor.Qt import QtGui

    menu_name = os.environ['AVALON_LABEL']

    context_label = "{0}, {1}".format(
        Session["AVALON_ASSET"], Session["AVALON_TASK"]
    )

    self._change_context_menu = context_label

    try:
        check_made_menu = findMenuAction(menu_name)
    except Exception:
        check_made_menu = None

    if not check_made_menu:
        # Grab Hiero's MenuBar
        menu = hiero.ui.menuBar().addMenu(menu_name)
    else:
        menu = check_made_menu.menu()

    context_label_action = menu.addAction(context_label)
    context_label_action.setEnabled(False)

    menu.addSeparator()

    workfiles_action = menu.addAction("Work Files...")
    workfiles_action.setIcon(QtGui.QIcon("icons:Position.png"))
    workfiles_action.triggered.connect(launch_workfiles_app)

    default_tags_action = menu.addAction("Create Default Tags...")
    default_tags_action.setIcon(QtGui.QIcon("icons:Position.png"))
    default_tags_action.triggered.connect(tags.add_tags_to_workfile)

    menu.addSeparator()

    publish_action = menu.addAction("Publish...")
    publish_action.setIcon(QtGui.QIcon("icons:Output.png"))
    publish_action.triggered.connect(
        lambda *args: publish(hiero.ui.mainWindow())
    )

    creator_action = menu.addAction("Create...")
    creator_action.setIcon(QtGui.QIcon("icons:CopyRectangle.png"))
    creator_action.triggered.connect(creator.show)

    loader_action = menu.addAction("Load...")
    loader_action.setIcon(QtGui.QIcon("icons:CopyRectangle.png"))
    loader_action.triggered.connect(cbloader.show)

    sceneinventory_action = menu.addAction("Manage...")
    sceneinventory_action.setIcon(QtGui.QIcon("icons:CopyRectangle.png"))
    sceneinventory_action.triggered.connect(sceneinventory.show)
    menu.addSeparator()

    reload_action = menu.addAction("Reload pipeline...")
    reload_action.setIcon(QtGui.QIcon("icons:ColorAdd.png"))
    reload_action.triggered.connect(reload_config)

    menu.addSeparator()
    apply_colorspace_p_action = menu.addAction("Apply Colorspace Project...")
    apply_colorspace_p_action.setIcon(QtGui.QIcon("icons:ColorAdd.png"))
    apply_colorspace_p_action.triggered.connect(apply_colorspace_project)

    apply_colorspace_c_action = menu.addAction("Apply Colorspace Clips...")
    apply_colorspace_c_action.setIcon(QtGui.QIcon("icons:ColorAdd.png"))
    apply_colorspace_c_action.triggered.connect(apply_colorspace_clips)

    self.context_label_action = context_label_action
    self.workfile_actions = workfiles_action
    self.default_tags_action = default_tags_action
    self.publish_action = publish_action
    self.reload_action = reload_action
