from Qt import QtWidgets, QtCore, QtGui


UNIQUE_ID_ROLE = QtCore.Qt.UserRole + 1
ASSET_NAME_ROLE = QtCore.Qt.UserRole + 2
FAMILY_ROLE = QtCore.Qt.UserRole + 3
FAMILY_ICON_ROLE = QtCore.Qt.UserRole + 4
VERSION_ROLE = QtCore.Qt.UserRole + 5
VERSION_ID_ROLE = QtCore.Qt.UserRole + 6
VERSION_EDIT_ROLE = QtCore.Qt.UserRole + 7
TIME_ROLE = QtCore.Qt.UserRole + 8
AUTHOR_ROLE = QtCore.Qt.UserRole + 9
FRAMES_ROLE = QtCore.Qt.UserRole + 10
DURATION_ROLE = QtCore.Qt.UserRole + 11
HANDLES_ROLE = QtCore.Qt.UserRole + 12
STEP_ROLE = QtCore.Qt.UserRole + 13


class VersionsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(VersionsWidget, self).__init__(parent)

        versions_view = QtWidgets.QTreeView(self)
        versions_model = VersionsModel(controller)
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(versions_model)
        versions_view.setModel(proxy_model)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(versions_view, 1)

        self._versions_view = versions_view
        self._versions_model = versions_model
        self._proxy_model = proxy_model

        self._controller = controller


class VersionsModel(QtGui.QStandardItemModel):
    column_labels = (
        "Subset",
        "Asset",
        "Family",
        "Version",
        "Time",
        "Author",
        "Frames",
        "Duration",
        "Handles",
        "Step"
    )

    def __init__(self, controller):
        super(VersionsModel, self).__init__()

        controller.event_system.add_callback(
            "versions.clear", self._on_versions_clear
        )
        # controller.event_system.add_callback(
        #     "versions.refresh.started", self._on_version_refresh_start
        # )
        controller.event_system.add_callback(
            "versions.refresh.finished", self._on_version_refresh_finish
        )

        self._controller = controller

        self._items_by_id = {}

    def _on_versions_clear(self):
        self._versions_model.clear()

    def _on_version_refresh_finish(self):
        subset_items = (
            self._controller.get_current_containers_subset_items()
        )
        items_ids_to_remove = set(self._items_by_id.keys())
        new_items = []
        for subset_item in subset_items:
            item_id = subset_item.id
            if item_id in self._items_by_id:
                items_ids_to_remove.remove(item_id)
                item = self._items_by_id[item_id]
            else:
                item = QtGui.QStandardItem()
                item.setData(item_id, UNIQUE_ID_ROLE)
                self._items_by_id[item_id] = item
                new_items.append(item)

            version_labels = subset_item.get_version_labels_by_id()
            version_labels_dict = dict(version_labels)
            version_id = item.data(VERSION_ID_ROLE)
            if version_id and version_id in version_labels_dict:
                version_label = version_labels_dict[version_id]
            else:
                version_id, version_label = version_labels[0]

            item.setData(subset_item.subset_name, QtCore.Qt.DisplayRole)
            item.setData(subset_item.asset_name, ASSET_NAME_ROLE)
            item.setData(subset_item.family, FAMILY_ROLE)
            item.setData(None, FAMILY_ICON_ROLE)
            item.setData(version_label, VERSION_ROLE)
            item.setData(version_id, VERSION_ID_ROLE)
            item.setData(version_labels, VERSION_EDIT_ROLE)
            item.setData(None, TIME_ROLE)
            item.setData(subset_item.author, AUTHOR_ROLE)
            item.setData(subset_item.duration, DURATION_ROLE)
            item.setData(subset_item.handles, HANDLES_ROLE)
            item.setData(subset_item.step, STEP_ROLE)

        items_to_remove = [
            self._items_by_id.pop(item_id)
            for item_id in items_ids_to_remove
        ]
        root_item = self.invisibleRootItem()
        for item in items_to_remove:
            root_item.removeRow(item.row())

        if new_items:
            root_item.appendRows(new_items)
