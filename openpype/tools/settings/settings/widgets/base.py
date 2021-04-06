from Qt import QtWidgets, QtGui, QtCore
from .lib import CHILD_OFFSET
from .widgets import ExpandingWidget


class BaseWidget(QtWidgets.QWidget):
    allow_actions = True

    def __init__(self, category_widget, entity, entity_widget):
        self.category_widget = category_widget
        self.entity = entity
        self.entity_widget = entity_widget

        self.ignore_input_changes = entity_widget.ignore_input_changes

        self._is_invalid = False
        self._style_state = None

        super(BaseWidget, self).__init__(entity_widget.content_widget)
        if not self.entity.gui_type:
            self.entity.on_change_callbacks.append(self._on_entity_change)

        self.label_widget = None
        self.create_ui()

    def trigger_hierarchical_style_update(self):
        self.category_widget.hierarchical_style_update()

    def create_ui_for_entity(self, *args, **kwargs):
        return self.category_widget.create_ui_for_entity(*args, **kwargs)

    @property
    def is_invalid(self):
        return self._is_invalid

    @staticmethod
    def get_style_state(
        is_invalid, is_modified, has_project_override, has_studio_override
    ):
        """Return stylesheet state by intered booleans."""
        if is_invalid:
            return "invalid"
        if is_modified:
            return "modified"
        if has_project_override:
            return "overriden"
        if has_studio_override:
            return "studio"
        return ""

    def hierarchical_style_update(self):
        raise NotImplementedError(
            "{} not implemented `hierarchical_style_update`".format(
                self.__class__.__name__
            )
        )

    def get_invalid(self):
        raise NotImplementedError(
            "{} not implemented `get_invalid`".format(
                self.__class__.__name__
            )
        )

    def _on_entity_change(self):
        """Not yet used."""
        print("{}: Warning missing `_on_entity_change` implementation".format(
            self.__class__.__name__
        ))

    def _discard_changes_action(self, menu, actions_mapping):
        # TODO use better condition as unsaved changes may be caused due to
        #   changes in schema.
        if not self.entity.can_discard_changes:
            return

        def discard_changes():
            self.ignore_input_changes.set_ignore(True)
            self.entity.discard_changes()
            self.ignore_input_changes.set_ignore(False)

        action = QtWidgets.QAction("Discard changes")
        actions_mapping[action] = discard_changes
        menu.addAction(action)

    def _add_to_studio_default(self, menu, actions_mapping):
        """Set values as studio overrides."""
        # Skip if not in studio overrides
        if not self.entity.can_add_to_studio_default:
            return

        action = QtWidgets.QAction("Add to studio default")
        actions_mapping[action] = self.entity.add_to_studio_default
        menu.addAction(action)

    def _remove_from_studio_default_action(self, menu, actions_mapping):
        if not self.entity.can_remove_from_studio_default:
            return

        def remove_from_studio_default():
            self.ignore_input_changes.set_ignore(True)
            self.entity.remove_from_studio_default()
            self.ignore_input_changes.set_ignore(False)
        action = QtWidgets.QAction("Remove from studio default")
        actions_mapping[action] = remove_from_studio_default
        menu.addAction(action)

    def _add_to_project_override_action(self, menu, actions_mapping):
        if not self.entity.can_add_to_project_override:
            return

        action = QtWidgets.QAction("Add to project project override")
        actions_mapping[action] = self.entity.add_to_project_override
        menu.addAction(action)

    def _remove_from_project_override_action(self, menu, actions_mapping):
        if not self.entity.can_remove_from_project_override:
            return

        def remove_from_project_override():
            self.ignore_input_changes.set_ignore(True)
            self.entity.remove_from_project_override()
            self.ignore_input_changes.set_ignore(False)
        action = QtWidgets.QAction("Remove from project override")
        actions_mapping[action] = remove_from_project_override
        menu.addAction(action)

    def show_actions_menu(self, event=None):
        if event and event.button() != QtCore.Qt.RightButton:
            return

        if not self.allow_actions:
            if event:
                return self.mouseReleaseEvent(event)
            return

        menu = QtWidgets.QMenu(self)

        actions_mapping = {}

        self._discard_changes_action(menu, actions_mapping)
        self._add_to_studio_default(menu, actions_mapping)
        self._remove_from_studio_default_action(menu, actions_mapping)
        self._add_to_project_override_action(menu, actions_mapping)
        self._remove_from_project_override_action(menu, actions_mapping)

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()

    def mouseReleaseEvent(self, event):
        if self.allow_actions and event.button() == QtCore.Qt.RightButton:
            return self.show_actions_menu()

        return super(BaseWidget, self).mouseReleaseEvent(event)


class InputWidget(BaseWidget):
    def create_ui(self):
        if self.entity.use_label_wrap:
            label = None
            self._create_label_wrap_ui()
        else:
            label = self.entity.label
            self.label_widget = None
            self.body_widget = None
            self.content_widget = self
            self.content_layout = self._create_layout(self)

        self._add_inputs_to_layout()

        self.entity_widget.add_widget_to_layout(self, label)

    def _create_label_wrap_ui(self):
        content_widget = QtWidgets.QWidget(self)
        content_widget.setObjectName("ContentWidget")

        content_widget.setProperty("content_state", "")
        content_layout_margins = (CHILD_OFFSET, 5, 0, 0)

        body_widget = ExpandingWidget(self.entity.label, self)
        label_widget = body_widget.label_widget
        body_widget.set_content_widget(content_widget)

        content_layout = self._create_layout(content_widget)
        content_layout.setContentsMargins(*content_layout_margins)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(body_widget)

        self.label_widget = label_widget
        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

    def _create_layout(self, parent_widget):
        layout = QtWidgets.QHBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        return layout

    def _add_inputs_to_layout(self):
        raise NotImplementedError(
            "Method `_add_inputs_to_layout` not implemented {}".format(
                self.__class__.__name__
            )
        )

    def update_style(self):
        has_unsaved_changes = self.entity.has_unsaved_changes
        if not has_unsaved_changes and self.entity.group_item:
            has_unsaved_changes = self.entity.group_item.has_unsaved_changes
        style_state = self.get_style_state(
            self.is_invalid,
            has_unsaved_changes,
            self.entity.has_project_override,
            self.entity.has_studio_override
        )
        if self._style_state == style_state:
            return

        self._style_state = style_state

        self.input_field.setProperty("input-state", style_state)
        self.input_field.style().polish(self.input_field)
        if self.label_widget:
            self.label_widget.setProperty("state", style_state)
            self.label_widget.style().polish(self.label_widget)

        if self.body_widget:
            if style_state:
                child_style_state = "child-{}".format(style_state)
            else:
                child_style_state = ""

            self.body_widget.side_line_widget.setProperty(
                "state", child_style_state
            )
            self.body_widget.side_line_widget.style().polish(
                self.body_widget.side_line_widget
            )

    @property
    def child_invalid(self):
        return self.is_invalid

    def hierarchical_style_update(self):
        self.update_style()

    def get_invalid(self):
        invalid = []
        if self.is_invalid:
            invalid.append(self)
        return invalid


class GUIWidget(BaseWidget):
    allow_actions = False
    separator_height = 2
    child_invalid = False

    def create_ui(self):
        entity_type = self.entity["type"]
        if entity_type == "label":
            self._create_label_ui()
        elif entity_type in ("separator", "splitter"):
            self._create_separator_ui()
        else:
            raise KeyError("Unknown GUI type {}".format(entity_type))

        self.entity_widget.add_widget_to_layout(self)

    def _create_label_ui(self):
        self.setObjectName("LabelWidget")

        label = self.entity["label"]
        label_widget = QtWidgets.QLabel(label, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(label_widget)

    def _create_separator_ui(self):
        splitter_item = QtWidgets.QWidget(self)
        splitter_item.setObjectName("SplitterItem")
        splitter_item.setMinimumHeight(self.separator_height)
        splitter_item.setMaximumHeight(self.separator_height)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter_item)

    def set_entity_value(self):
        return

    def hierarchical_style_update(self):
        pass

    def get_invalid(self):
        return []


class MockUpWidget(BaseWidget):
    allow_actions = False
    child_invalid = False

    def create_ui(self):
        self.setObjectName("LabelWidget")

        label = "Mockup widget for entity {}".format(self.entity.path)
        label_widget = QtWidgets.QLabel(label, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(label_widget)
        self.entity_widget.add_widget_to_layout(self)

    def set_entity_value(self):
        return

    def hierarchical_style_update(self):
        pass

    def get_invalid(self):
        return []
