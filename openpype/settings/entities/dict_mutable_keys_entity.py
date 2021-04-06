import re
import copy

from .lib import (
    NOT_SET,
    OverrideState
)
from . import EndpointEntity
from .exceptions import (
    DefaultsNotDefined,
    InvalidKeySymbols,
    StudioDefaultsNotDefined,
    RequiredKeyModified,
    EntitySchemaError
)
from openpype.settings.constants import (
    METADATA_KEYS,
    M_DYNAMIC_KEY_LABEL,
    M_ENVIRONMENT_KEY,
    KEY_REGEX,
    KEY_ALLOWED_SYMBOLS
)


class DictMutableKeysEntity(EndpointEntity):
    """Dictionary entity that has mutable keys.

    Keys of entity's children can be modified, removed or added. Children have
    defined entity type so it is not possible to have 2 different entity types
    as children.

    TODOs:
    - cleanup children on pop
        - remove child's reference to parent
        - clear callbacks
    """
    schema_types = ["dict-modifiable"]
    _default_label_wrap = {
        "use_label_wrap": True,
        "collapsible": True,
        "collapsed": True
    }

    _miss_arg = object()

    def __getitem__(self, key):
        if key not in self.children_by_key:
            self.add_key(key)
        return self.children_by_key[key]

    def __setitem__(self, key, value):
        self.set_key_value(key, value)

    def __iter__(self):
        for key in self.keys():
            yield key

    def __contains__(self, key):
        return key in self.children_by_key

    def pop(self, key, *args, **kwargs):
        if key in self.required_keys:
            raise RequiredKeyModified(self.path, key)
        result = self.children_by_key.pop(key, *args, **kwargs)
        self.on_change()
        return result

    def get(self, key, default=None):
        return self.children_by_key.get(key, default)

    def keys(self):
        return self.children_by_key.keys()

    def values(self):
        return self.children_by_key.values()

    def items(self):
        return self.children_by_key.items()

    def clear(self):
        for key in tuple(self.children_by_key.keys()):
            self.pop(key)

    def set(self, value):
        new_value = self.convert_to_valid_type(value)

        prev_keys = set(self.keys())

        for _key, _value in new_value.items():
            self.set_key_value(_key, _value)
            if _key in prev_keys:
                prev_keys.remove(_key)

        for key in prev_keys:
            self.pop(key)

    def set_key_value(self, key, value):
        # TODO Check for value type if is Settings entity?
        child_obj = self.children_by_key.get(key)
        if not child_obj:
            if not KEY_REGEX.match(key):
                raise InvalidKeySymbols(self.path, key)

            child_obj = self.add_key(key)

        child_obj.set(value)

    def change_key(self, old_key, new_key):
        if old_key in self.required_keys:
            raise RequiredKeyModified(self.path, old_key)

        if new_key == old_key:
            return

        if not KEY_REGEX.match(new_key):
            raise InvalidKeySymbols(self.path, new_key)

        self.children_by_key[new_key] = self.children_by_key.pop(old_key)
        self._on_key_label_change()

    def _on_key_label_change(self):
        if self._override_state is OverrideState.STUDIO:
            self._has_studio_override = True
        elif self._override_state is OverrideState.PROJECT:
            self._has_project_override = True
        self.on_change()

    def _add_key(self, key):
        if key in self.children_by_key:
            self.pop(key)

        if not KEY_REGEX.match(key):
            raise InvalidKeySymbols(self.path, key)

        if self.value_is_env_group:
            item_schema = copy.deepcopy(self.item_schema)
            item_schema["env_group_key"] = key
        else:
            item_schema = self.item_schema

        new_child = self.create_schema_object(item_schema, self, True)
        self.children_by_key[key] = new_child
        return new_child

    def add_key(self, key):
        new_child = self._add_key(key)
        new_child.set_override_state(self._override_state)
        self.on_change()
        return new_child

    def change_child_key(self, child_entity, new_key):
        old_key = None
        for key, child in self.children_by_key.items():
            if child is child_entity:
                old_key = key
                break

        self.change_key(old_key, new_key)

    def get_child_key(self, child_entity):
        for key, child in self.children_by_key.items():
            if child is child_entity:
                return key
        return None

    # Label methods
    def get_child_label(self, child_entity):
        return self.children_label_by_id.get(child_entity.id)

    def set_child_label(self, child_entity, label):
        self.children_label_by_id[child_entity.id] = label
        self._on_key_label_change()

    def get_key_label(self, key):
        child_entity = self.children_by_key[key]
        return self.get_child_label(child_entity)

    def set_key_label(self, key, label):
        child_entity = self.children_by_key[key]
        self.set_child_label(child_entity, label)

    def _item_initalization(self):
        self._default_metadata = {}
        self._studio_override_metadata = {}
        self._project_override_metadata = {}

        self.initial_value = None

        self._ignore_child_changes = False

        self.valid_value_types = (dict, )
        self.value_on_not_set = {}

        self.children_by_key = {}
        self.children_label_by_id = {}

        self.value_is_env_group = (
            self.schema_data.get("value_is_env_group") or False
        )
        self.required_keys = self.schema_data.get("required_keys") or []
        self.collapsible_key = self.schema_data.get("collapsible_key") or False
        # GUI attributes
        self.hightlight_content = (
            self.schema_data.get("highlight_content") or False
        )

        object_type = self.schema_data.get("object_type") or {}
        if not isinstance(object_type, dict):
            # Backwards compatibility
            object_type = {
                "type": object_type
            }
            input_modifiers = self.schema_data.get("input_modifiers") or {}
            if input_modifiers:
                self.log.warning((
                    "Used deprecated key `input_modifiers` to define item."
                    " Rather use `object_type` as dictionary with modifiers."
                ))
                object_type.update(input_modifiers)
        self.item_schema = object_type

        if self.value_is_env_group:
            self.item_schema["env_group_key"] = ""

        if not self.group_item:
            self.is_group = True

    def schema_validations(self):
        super(DictMutableKeysEntity, self).schema_validations()

        if not self.schema_data.get("object_type"):
            reason = (
                "Modifiable dictionary must have specified `object_type`."
            )
            raise EntitySchemaError(self, reason)

        # TODO Ability to store labels should be defined with different key
        if self.collapsible_key and not self.file_item:
            reason = (
                "Modifiable dictionary with collapsible keys is not under"
                " file item so can't store metadata."
            )
            raise EntitySchemaError(self, reason)

        for child_obj in self.children_by_key.values():
            child_obj.schema_validations()

    def get_child_path(self, child_obj):
        result_key = None
        for key, _child_obj in self.children_by_key.items():
            if _child_obj is child_obj:
                result_key = key
                break

        if result_key is None:
            raise ValueError("Didn't found child {}".format(child_obj))

        return "/".join([self.path, result_key])

    def on_child_change(self, _child_entity):
        if self._ignore_child_changes:
            return

        if self._override_state is OverrideState.STUDIO:
            self._has_studio_override = True
        elif self._override_state is OverrideState.PROJECT:
            self._has_project_override = True

        self.on_change()

    def _metadata_for_current_state(self):
        if (
            self._override_state is OverrideState.PROJECT
            and self._project_override_value is not NOT_SET
        ):
            return self._project_override_metadata

        if (
            self._override_state >= OverrideState.STUDIO
            and self._studio_override_value is not NOT_SET
        ):
            return self._studio_override_metadata

        return self._default_metadata

    def set_override_state(self, state):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        # TODO change metadata
        self._override_state = state
        # Ignore if is dynamic item and use default in that case
        if not self.is_dynamic_item and not self.is_in_dynamic_item:
            if state > OverrideState.DEFAULTS:
                if not self.has_default_value:
                    raise DefaultsNotDefined(self)

            elif state > OverrideState.STUDIO:
                if not self.had_studio_override:
                    raise StudioDefaultsNotDefined(self)

        if state is OverrideState.STUDIO:
            self._has_studio_override = self.had_studio_override

        elif state is OverrideState.PROJECT:
            self._has_project_override = self.had_project_override
            self._has_studio_override = self.had_studio_override

        using_project_overrides = False
        using_studio_overrides = False
        if (
            state is OverrideState.PROJECT
            and self.had_project_override
        ):
            using_project_overrides = True
            value = self._project_override_value
            metadata = self._project_override_metadata

        elif (
            state >= OverrideState.STUDIO
            and self.had_studio_override
        ):
            using_studio_overrides = True
            value = self._studio_override_value
            metadata = self._studio_override_metadata

        else:
            value = self._default_value
            metadata = self._default_metadata

        if value is NOT_SET:
            value = self.value_on_not_set

        new_value = copy.deepcopy(value)

        # Simulate `clear` method without triggering value change
        for key in tuple(self.children_by_key.keys()):
            self.children_by_key.pop(key)

        for required_key in self.required_keys:
            if required_key not in new_value:
                new_value[required_key] = NOT_SET

        # Create new children
        children_label_by_id = {}
        metadata_labels = metadata.get(M_DYNAMIC_KEY_LABEL) or {}
        for _key, _value in new_value.items():
            if not KEY_REGEX.match(_key):
                # Replace invalid characters with underscore
                # - this is safety to not break already existing settings
                _key = re.sub(
                    r"[^{}]+".format(KEY_ALLOWED_SYMBOLS),
                    "_",
                    _key
                )

            child_entity = self._add_key(_key)
            child_entity.update_default_value(_value)
            if using_project_overrides:
                child_entity.update_project_value(_value)
            elif using_studio_overrides:
                child_entity.update_studio_value(_value)

            label = metadata_labels.get(_key)
            if label:
                children_label_by_id[child_entity.id] = label
            child_entity.set_override_state(state)

        self.children_label_by_id = children_label_by_id

        self.initial_value = self.settings_value()

    def children_key_by_id(self):
        return {
            child_entity.id: key
            for key, child_entity in self.children_by_key.items()
        }

    @property
    def value(self):
        output = {}
        for key, child_entity in self.children_by_key.items():
            output[key] = child_entity.value
        return output

    @property
    def metadata(self):
        output = {}
        if not self.children_label_by_id:
            return output

        children_key_by_id = self.children_key_by_id()
        label_metadata = {}
        for child_id, label in self.children_label_by_id.items():
            key = children_key_by_id.get(child_id)
            if key:
                label_metadata[key] = label

        output[M_DYNAMIC_KEY_LABEL] = label_metadata

        return output

    @property
    def has_unsaved_changes(self):
        if (
            self._override_state is OverrideState.PROJECT
            and self._has_project_override != self.had_project_override
        ):
            return True

        elif (
            self._override_state is OverrideState.STUDIO
            and self._has_studio_override != self.had_studio_override
        ):
            return True

        if self._child_has_unsaved_changes:
            return True

        if self.metadata != self._metadata_for_current_state():
            return True

        if self.settings_value() != self.initial_value:
            return True

        return False

    @property
    def _child_has_unsaved_changes(self):
        for child_obj in self.children_by_key.values():
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def has_studio_override(self):
        return self._has_studio_override or self._child_has_studio_override

    @property
    def _child_has_studio_override(self):
        if self._override_state >= OverrideState.STUDIO:
            for child_obj in self.children_by_key.values():
                if child_obj.has_studio_override:
                    return True
        return False

    @property
    def has_project_override(self):
        return self._has_project_override or self._child_has_project_override

    @property
    def _child_has_project_override(self):
        if self._override_state >= OverrideState.PROJECT:
            for child_obj in self.children_by_key.values():
                if child_obj.has_project_override:
                    return True
        return False

    def _settings_value(self):
        output = {}
        for key, child_entity in self.children_by_key.items():
            child_value = child_entity.settings_value()
            # TODO child should have setter of env group key se child can
            #   know what env group represents.
            if self.value_is_env_group:
                if key not in child_value[M_ENVIRONMENT_KEY]:
                    _metadata = child_value[M_ENVIRONMENT_KEY]
                    _m_keykey = tuple(_metadata.keys())[0]
                    env_keys = child_value[M_ENVIRONMENT_KEY].pop(_m_keykey)
                    child_value[M_ENVIRONMENT_KEY][key] = env_keys
            output[key] = child_value
        output.update(self.metadata)
        return output

    def _prepare_value(self, value):
        metadata = {}
        if isinstance(value, dict):
            for key in METADATA_KEYS:
                if key in value:
                    metadata[key] = value.pop(key)
        return value, metadata

    def update_default_value(self, value):
        value = self._check_update_value(value, "default")
        has_default_value = value is not NOT_SET
        if has_default_value:
            for required_key in self.required_keys:
                if required_key not in value:
                    has_default_value = False
                    break
        self.has_default_value = has_default_value
        value, metadata = self._prepare_value(value)
        self._default_value = value
        self._default_metadata = metadata

    def update_studio_value(self, value):
        value = self._check_update_value(value, "studio override")
        value, metadata = self._prepare_value(value)
        self._studio_override_value = value
        self._studio_override_metadata = metadata
        self.had_studio_override = value is not NOT_SET

    def update_project_value(self, value):
        value = self._check_update_value(value, "project override")
        value, metadata = self._prepare_value(value)
        self._project_override_value = value
        self._project_override_metadata = metadata
        self.had_project_override = value is not NOT_SET

    def _discard_changes(self, on_change_trigger):
        self.set_override_state(self._override_state)
        on_change_trigger.append(self.on_change)

    def _add_to_studio_default(self, _on_change_trigger):
        self._has_studio_override = True
        self.on_change()

    def _remove_from_studio_default(self, on_change_trigger):
        value = self._default_value
        if value is NOT_SET:
            value = self.value_on_not_set

        new_value = copy.deepcopy(value)
        self._ignore_child_changes = True

        # Simulate `clear` method without triggering value change
        for key in tuple(self.children_by_key.keys()):
            child_obj = self.children_by_key.pop(key)

        # Create new children
        for _key, _value in new_value.items():
            child_obj = self._add_key(_key)
            child_obj.update_default_value(_value)
            child_obj.set_override_state(self._override_state)

        self._ignore_child_changes = False

        self._has_studio_override = False

        on_change_trigger.append(self.on_change)

    def _add_to_project_override(self, _on_change_trigger):
        self._has_project_override = True
        self.on_change()

    def _remove_from_project_override(self, on_change_trigger):
        if self._override_state is not OverrideState.PROJECT:
            return

        if not self.has_project_override:
            return

        if self._has_studio_override:
            value = self._studio_override_value
        elif self.has_default_value:
            value = self._default_value
        else:
            value = self.value_on_not_set

        new_value = copy.deepcopy(value)

        self._ignore_child_changes = True

        # Simulate `clear` method without triggering value change
        for key in tuple(self.children_by_key.keys()):
            child_obj = self.children_by_key.pop(key)

        # Create new children
        for _key, _value in new_value.items():
            child_obj = self._add_key(_key)
            child_obj.update_default_value(_value)
            if self._has_studio_override:
                child_obj.update_studio_value(_value)
            child_obj.set_override_state(self._override_state)

        self._ignore_child_changes = False

        self._has_project_override = False

        on_change_trigger.append(self.on_change)

    def reset_callbacks(self):
        super(DictMutableKeysEntity, self).reset_callbacks()
        for child_entity in self.children_by_key.values():
            child_entity.reset_callbacks()
