import qtawesome
from qtpy import QtWidgets, QtCore, QtGui

from openpype.style import (
    get_default_entity_icon_color,
    get_disabled_entity_icon_color,
)
from openpype.tools.utils.delegates import PrettyTimeDelegate

from .utils import TreeView

FILENAME_ROLE = QtCore.Qt.UserRole + 1
FILEPATH_ROLE = QtCore.Qt.UserRole + 2
DATE_MODIFIED_ROLE = QtCore.Qt.UserRole + 3


class WorkAreaFilesModel(QtGui.QStandardItemModel):
    """A model for displaying files.

    Args:
        controller (AbstractControl): The control object.
    """

    def __init__(self, controller):
        super(WorkAreaFilesModel, self).__init__()

        self.setColumnCount(2)

        controller.register_event_callback(
            "selection.task.changed",
            self._on_task_changed
        )

        self._file_icon = qtawesome.icon(
            "fa.file-o",
            color=get_default_entity_icon_color()
        )
        self._controller = controller
        self._items_by_filename = {}
        self._missing_context_item = None
        self._missing_context_used = False
        self._empty_root_item = None
        self._empty_item_used = False
        self._published_mode = False
        self._last_folder_id = None
        self._last_task_id = None

        self._add_empty_item()

    def _get_missing_context_item(self):
        if self._missing_context_item is None:
            message = "Select folder and task"
            item = QtGui.QStandardItem(message)
            icon = qtawesome.icon(
                "fa.times",
                color=get_disabled_entity_icon_color()
            )
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            item.setColumnCount(self.columnCount())
            self._missing_context_item = item
        return self._missing_context_item

    def clear(self):
        self._items_by_filename = {}
        self._remove_missing_context_item()
        self._remove_empty_item()
        super(WorkAreaFilesModel, self).clear()

    def _add_missing_context_item(self):
        if self._missing_context_used:
            return
        self.clear()
        root_item = self.invisibleRootItem()
        root_item.appendRow(self._get_missing_context_item())
        self._missing_context_used = True

    def _remove_missing_context_item(self):
        if not self._missing_context_used:
            return
        root_item = self.invisibleRootItem()
        root_item.takeRow(self._missing_context_item.row())
        self._missing_context_used = False

    def _get_empty_root_item(self):
        if self._empty_root_item is None:
            message = "Work Area is empty.."
            item = QtGui.QStandardItem(message)
            icon = qtawesome.icon(
                "fa.exclamation-circle",
                color=get_disabled_entity_icon_color()
            )
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setFlags(QtCore.Qt.NoItemFlags)
            item.setColumnCount(self.columnCount())
            self._empty_root_item = item
        return self._empty_root_item

    def _add_empty_item(self):
        if self._empty_item_used:
            return
        self.clear()
        root_item = self.invisibleRootItem()
        root_item.appendRow(self._get_empty_root_item())
        self._empty_item_used = True

    def _remove_empty_item(self):
        if not self._empty_item_used:
            return
        root_item = self.invisibleRootItem()
        root_item.takeRow(self._empty_root_item.row())
        self._empty_item_used = False

    def _on_task_changed(self, event):
        self._last_folder_id = event["folder_id"]
        self._last_task_id = event["task_id"]
        if not self._published_mode:
            self._fill_items()

    def _fill_items(self):
        folder_id = self._last_folder_id
        task_id = self._last_task_id
        if not folder_id or not task_id:
            self._add_missing_context_item()
            return

        file_items = self._controller.get_workarea_file_items(
            folder_id, task_id
        )
        root_item = self.invisibleRootItem()
        if not file_items:
            self._add_empty_item()
            return
        self._remove_empty_item()
        self._remove_missing_context_item()

        items_to_remove = set(self._items_by_filename.keys())
        new_items = []
        for file_item in file_items:
            filename = file_item.filename
            if filename in self._items_by_filename:
                items_to_remove.discard(filename)
                item = self._items_by_filename[filename]
            else:
                item = QtGui.QStandardItem()
                new_items.append(item)
                item.setColumnCount(self.columnCount())
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                )
                item.setData(self._file_icon, QtCore.Qt.DecorationRole)
                item.setData(file_item.filename, QtCore.Qt.DisplayRole)
                item.setData(file_item.filename, FILENAME_ROLE)

            item.setData(file_item.filepath, FILEPATH_ROLE)
            item.setData(file_item.modified, DATE_MODIFIED_ROLE)

            self._items_by_filename[file_item.filename] = item

        if new_items:
            root_item.appendRows(new_items)

        for filename in items_to_remove:
            item = self._items_by_filename.pop(filename)
            root_item.removeRow(item.row())

        if root_item.rowCount() == 0:
            self._add_empty_item()

    def flags(self, index):
        # Use flags of first column for all columns
        if index.column() != 0:
            index = self.index(index.row(), 0, index.parent())
        return super(WorkAreaFilesModel, self).flags(index)

    def headerData(self, section, orientation, role):
        # Show nice labels in the header
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
        ):
            if section == 0:
                return "Name"
            elif section == 1:
                return "Date modified"

        return super(WorkAreaFilesModel, self).headerData(
            section, orientation, role
        )

    def data(self, index, role=None):
        if role is None:
            role = QtCore.Qt.DisplayRole

        # Handle roles for first column
        if index.column() == 1:
            if role == QtCore.Qt.DecorationRole:
                return None

            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                role = DATE_MODIFIED_ROLE
            index = self.index(index.row(), 0, index.parent())

        return super(WorkAreaFilesModel, self).data(index, role)

    def set_published_mode(self, published_mode):
        if self._published_mode == published_mode:
            return
        self._published_mode = published_mode
        if not published_mode:
            self._fill_items()


class WorkAreaFilesWidget(QtWidgets.QWidget):
    selection_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(WorkAreaFilesWidget, self).__init__(parent)

        view = TreeView(self)
        view.setSortingEnabled(True)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # Smaller indentation
        view.setIndentation(3)

        model = WorkAreaFilesModel(controller)
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(model)
        proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy_model.setDynamicSortFilter(True)

        view.setModel(proxy_model)

        time_delegate = PrettyTimeDelegate()
        view.setItemDelegateForColumn(1, time_delegate)

        # Default to a wider first filename column it is what we mostly care
        # about and the date modified is relatively small anyway.
        view.setColumnWidth(0, 330)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(view, 1)

        selection_model = view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)
        view.double_clicked_left.connect(self._on_left_double_click)

        self._view = view
        self._model = model
        self._proxy_model = proxy_model
        self._time_delegate = time_delegate
        self._controller = controller

        self._published_mode = False

    def set_published_mode(self, published_mode):
        self._model.set_published_mode(published_mode)
        self._published_mode = published_mode

    def set_text_filter(self, text_filter):
        self._proxy_model.setFilterFixedString(text_filter)

    def get_selected_path(self):
        selection_model = self._view.selectionModel()
        for index in selection_model.selectedIndexes():
            filepath = index.data(FILEPATH_ROLE)
            if filepath is not None:
                return filepath
        return None

    def open_current_file(self):
        path = self.get_selected_path()
        if path:
            self._controller.open_workfile(path)

    def _on_selection_change(self):
        filepath = self.get_selected_path()
        self._controller.set_selected_workfile_path(filepath)

    def _on_left_double_click(self):
        self.open_current_file()
