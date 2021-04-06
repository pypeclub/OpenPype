import sys
import time
import logging

from openpype.hosts.maya.api.lib import assign_look_by_version

from avalon import style, io
from avalon.tools import lib
from avalon.vendor.Qt import QtWidgets, QtCore

from maya import cmds
# old api for MFileIO
import maya.OpenMaya
import maya.api.OpenMaya as om

from . import widgets
from . import commands

module = sys.modules[__name__]
module.window = None


class App(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.log = logging.getLogger(__name__)

        # Store callback references
        self._callbacks = []

        filename = commands.get_workfile()

        self.setObjectName("lookManager")
        self.setWindowTitle("Look Manager 1.3.0 - [{}]".format(filename))
        self.setWindowFlags(QtCore.Qt.Window)
        self.setParent(parent)

        # Force to delete the window on close so it triggers
        # closeEvent only once. Otherwise it's retriggered when
        # the widget gets garbage collected.
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.resize(750, 500)

        self.setup_ui()

        self.setup_connections()

        # Force refresh check on initialization
        self._on_renderlayer_switch()

    def setup_ui(self):
        """Build the UI"""

        # Assets (left)
        asset_outliner = widgets.AssetOutliner()

        # Looks (right)
        looks_widget = QtWidgets.QWidget()
        looks_layout = QtWidgets.QVBoxLayout(looks_widget)

        look_outliner = widgets.LookOutliner()  # Database look overview

        assign_selected = QtWidgets.QCheckBox("Assign to selected only")
        assign_selected.setToolTip("Whether to assign only to selected nodes "
                                   "or to the full asset")
        remove_unused_btn = QtWidgets.QPushButton("Remove Unused Looks")

        looks_layout.addWidget(look_outliner)
        looks_layout.addWidget(assign_selected)
        looks_layout.addWidget(remove_unused_btn)

        # Footer
        status = QtWidgets.QStatusBar()
        status.setSizeGripEnabled(False)
        status.setFixedHeight(25)
        warn_layer = QtWidgets.QLabel("Current Layer is not "
                                      "defaultRenderLayer")
        warn_layer.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        warn_layer.setStyleSheet("color: #DD5555; font-weight: bold;")
        warn_layer.setFixedHeight(25)

        footer = QtWidgets.QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(status)
        footer.addWidget(warn_layer)

        # Build up widgets
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_splitter = QtWidgets.QSplitter()
        main_splitter.setStyleSheet("QSplitter{ border: 0px; }")
        main_splitter.addWidget(asset_outliner)
        main_splitter.addWidget(looks_widget)
        main_splitter.setSizes([350, 200])
        main_layout.addWidget(main_splitter)
        main_layout.addLayout(footer)

        # Set column width
        asset_outliner.view.setColumnWidth(0, 200)
        look_outliner.view.setColumnWidth(0, 150)

        # Open widgets
        self.asset_outliner = asset_outliner
        self.look_outliner = look_outliner
        self.status = status
        self.warn_layer = warn_layer

        # Buttons
        self.remove_unused = remove_unused_btn
        self.assign_selected = assign_selected

    def setup_connections(self):
        """Connect interactive widgets with actions"""

        self.asset_outliner.selection_changed.connect(
            self.on_asset_selection_changed)

        self.asset_outliner.refreshed.connect(
            lambda: self.echo("Loaded assets.."))

        self.look_outliner.menu_apply_action.connect(self.on_process_selected)
        self.remove_unused.clicked.connect(commands.remove_unused_looks)

        # Maya renderlayer switch callback
        callback = om.MEventMessage.addEventCallback(
            "renderLayerManagerChange",
            self._on_renderlayer_switch
        )
        self._callbacks.append(callback)

    def closeEvent(self, event):

        # Delete callbacks
        for callback in self._callbacks:
            om.MMessage.removeCallback(callback)

        return super(App, self).closeEvent(event)

    def _on_renderlayer_switch(self, *args):
        """Callback that updates on Maya renderlayer switch"""

        if maya.OpenMaya.MFileIO.isNewingFile():
            # Don't perform a check during file open or file new as
            # the renderlayers will not be in a valid state yet.
            return

        layer = cmds.editRenderLayerGlobals(query=True,
                                            currentRenderLayer=True)
        if layer != "defaultRenderLayer":
            self.warn_layer.show()
        else:
            self.warn_layer.hide()

    def echo(self, message):
        self.status.showMessage(message, 1500)

    def refresh(self):
        """Refresh the content"""

        # Get all containers and information
        self.asset_outliner.clear()
        found_items = self.asset_outliner.get_all_assets()
        if not found_items:
            self.look_outliner.clear()

    def on_asset_selection_changed(self):
        """Get selected items from asset loader and fill look outliner"""

        items = self.asset_outliner.get_selected_items()
        self.look_outliner.clear()
        self.look_outliner.add_items(items)

    def on_process_selected(self):
        """Process all selected looks for the selected assets"""

        assets = self.asset_outliner.get_selected_items()
        assert assets, "No asset selected"

        # Collect the looks we want to apply (by name)
        look_items = self.look_outliner.get_selected_items()
        looks = {look["subset"] for look in look_items}

        selection = self.assign_selected.isChecked()
        asset_nodes = self.asset_outliner.get_nodes(selection=selection)

        start = time.time()
        for i, (asset, item) in enumerate(asset_nodes.items()):

            # Label prefix
            prefix = "({}/{})".format(i+1, len(asset_nodes))

            # Assign the first matching look relevant for this asset
            # (since assigning multiple to the same nodes makes no sense)
            assign_look = next((subset for subset in item["looks"]
                               if subset["name"] in looks), None)
            if not assign_look:
                self.echo("{} No matching selected "
                          "look for {}".format(prefix, asset))
                continue

            # Get the latest version of this asset's look subset
            version = io.find_one({"type": "version",
                                   "parent": assign_look["_id"]},
                                  sort=[("name", -1)])

            subset_name = assign_look["name"]
            self.echo("{} Assigning {} to {}\t".format(prefix,
                                                       subset_name,
                                                       asset))

            # Assign look
            assign_look_by_version(nodes=item["nodes"],
                                   version_id=version["_id"])

        end = time.time()

        self.echo("Finished assigning.. ({0:.3f}s)".format(end - start))


def show():
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    # Get Maya main window
    top_level_widgets = QtWidgets.QApplication.topLevelWidgets()
    mainwindow = next(widget for widget in top_level_widgets
                      if widget.objectName() == "MayaWindow")

    with lib.application():
        window = App(parent=mainwindow)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window
