# -*- coding: utf-8 -*-
"""Package to deal with saving and retrieving user specific settings."""
import os
from datetime import datetime
from abc import ABCMeta, abstractmethod
import json

# disable lru cache in Python 2
try:
    from functools import lru_cache
except ImportError:
    def lru_cache(maxsize):
        def max_size(func):
            def wrapper(*args, **kwargs):
                value = func(*args, **kwargs)
                return value
            return wrapper
        return max_size

# ConfigParser was renamed in python3 to configparser
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import platform

import appdirs
import six

from .import validate_mongo_connection


@six.add_metaclass(ABCMeta)
class ASettingRegistry():
    """Abstract class defining structure of **SettingRegistry** class.

    It is implementing methods to store secure items into keyring, otherwise
    mechanism for storing common items must be implemented in abstract
    methods.

    Attributes:
        _name (str): Registry names.

    """

    def __init__(self, name):
        # type: (str) -> ASettingRegistry
        super(ASettingRegistry, self).__init__()

        if six.PY3:
            import keyring
            # hack for cx_freeze and Windows keyring backend
            if platform.system() == "Windows":
                from keyring.backends import Windows
                keyring.set_keyring(Windows.WinVaultKeyring())

        self._name = name
        self._items = {}

    def set_item(self, name, value):
        # type: (str, str) -> None
        """Set item to settings registry.

        Args:
            name (str): Name of the item.
            value (str): Value of the item.

        """
        self._set_item(name, value)

    @abstractmethod
    def _set_item(self, name, value):
        # type: (str, str) -> None
        # Implement it
        pass

    def __setitem__(self, name, value):
        self._items[name] = value
        self._set_item(name, value)

    def get_item(self, name):
        # type: (str) -> str
        """Get item from settings registry.

        Args:
            name (str): Name of the item.

        Returns:
            value (str): Value of the item.

        Raises:
            ValueError: If item doesn't exist.

        """
        return self._get_item(name)

    @abstractmethod
    def _get_item(self, name):
        # type: (str) -> str
        # Implement it
        pass

    def __getitem__(self, name):
        return self._get_item(name)

    def delete_item(self, name):
        # type: (str) -> None
        """Delete item from settings registry.

        Args:
            name (str): Name of the item.

        """
        self._delete_item(name)

    @abstractmethod
    def _delete_item(self, name):
        # type: (str) -> None
        """Delete item from settings.

        Note:
            see :meth:`pype.lib.local_settings.ARegistrySettings.delete_item`

        """
        pass

    def __delitem__(self, name):
        del self._items[name]
        self._delete_item(name)

    def set_secure_item(self, name, value):
        # type: (str, str) -> None
        """Set sensitive item into system's keyring.

        This uses `Keyring module`_ to save sensitive stuff into system's
        keyring.

        Args:
            name (str): Name of the item.
            value (str): Value of the item.

        .. _Keyring module:
            https://github.com/jaraco/keyring

        """
        if six.PY2:
            raise NotImplementedError(
                "Keyring not available on Python 2 hosts")
        import keyring
        keyring.set_password(self._name, name, value)

    @lru_cache(maxsize=32)
    def get_secure_item(self, name):
        # type: (str) -> str
        """Get value of sensitive item from system's keyring.

        See also `Keyring module`_

        Args:
            name (str): Name of the item.

        Returns:
            value (str): Value of the item.

        Raises:
            ValueError: If item doesn't exist.

        .. _Keyring module:
            https://github.com/jaraco/keyring

        """
        if six.PY2:
            raise NotImplementedError(
                "Keyring not available on Python 2 hosts")
        import keyring
        value = keyring.get_password(self._name, name)
        if not value:
            raise ValueError(
                "Item {}:{} does not exist in keyring.".format(
                    self._name, name))
        return value

    def delete_secure_item(self, name):
        # type: (str) -> None
        """Delete value stored in system's keyring.

        See also `Keyring module`_

        Args:
            name (str): Name of the item to be deleted.

        .. _Keyring module:
            https://github.com/jaraco/keyring

        """
        if six.PY2:
            raise NotImplementedError(
                "Keyring not available on Python 2 hosts")
        import keyring
        self.get_secure_item.cache_clear()
        keyring.delete_password(self._name, name)


class IniSettingRegistry(ASettingRegistry):
    """Class using :mod:`configparser`.

    This class is using :mod:`configparser` (ini) files to store items.

    """

    def __init__(self, name, path):
        # type: (str, str) -> IniSettingRegistry
        super(IniSettingRegistry, self).__init__(name)
        # get registry file
        version = os.getenv("OPENPYPE_VERSION", "N/A")
        self._registry_file = os.path.join(path, "{}.ini".format(name))
        if not os.path.exists(self._registry_file):
            with open(self._registry_file, mode="w") as cfg:
                print("# Settings registry", cfg)
                print("# Generated by Pype {}".format(version), cfg)
                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                print("# {}".format(now), cfg)

    def set_item_section(
            self, section, name, value):
        # type: (str, str, str) -> None
        """Set item to specific section of ini registry.

        If section doesn't exists, it is created.

        Args:
            section (str): Name of section.
            name (str): Name of the item.
            value (str): Value of the item.

        """
        value = str(value)
        config = configparser.ConfigParser()

        config.read(self._registry_file)
        if not config.has_section(section):
            config.add_section(section)
        current = config[section]
        current[name] = value

        with open(self._registry_file, mode="w") as cfg:
            config.write(cfg)

    def _set_item(self, name, value):
        # type: (str, str) -> None
        self.set_item_section("MAIN", name, value)

    def set_item(self, name, value):
        # type: (str, str) -> None
        """Set item to settings ini file.

        This saves item to ``DEFAULT`` section of ini as each item there
        must reside in some section.

        Args:
            name (str): Name of the item.
            value (str): Value of the item.

        """
        # this does the some, overridden just for different docstring.
        # we cast value to str as ini options values must be strings.
        super(IniSettingRegistry, self).set_item(name, str(value))

    def get_item(self, name):
        # type: (str) -> str
        """Gets item from settings ini file.

        This gets settings from ``DEFAULT`` section of ini file as each item
        there must reside in some section.

        Args:
            name (str): Name of the item.

        Returns:
            str: Value of item.

        Raises:
            ValueError: If value doesn't exist.

        """
        return super(IniSettingRegistry, self).get_item(name)

    @lru_cache(maxsize=32)
    def get_item_from_section(self, section, name):
        # type: (str, str) -> str
        """Get item from section of ini file.

        This will read ini file and try to get item value from specified
        section. If that section or item doesn't exist, :exc:`ValueError`
        is risen.

        Args:
            section (str): Name of ini section.
            name (str): Name of the item.

        Returns:
            str: Item value.

        Raises:
            ValueError: If value doesn't exist.

        """
        config = configparser.ConfigParser()
        config.read(self._registry_file)
        try:
            value = config[section][name]
        except KeyError:
            raise ValueError(
                "Registry doesn't contain value {}:{}".format(section, name))
        return value

    def _get_item(self, name):
        # type: (str) -> str
        return self.get_item_from_section("MAIN", name)

    def delete_item_from_section(self, section, name):
        # type: (str, str) -> None
        """Delete item from section in ini file.

        Args:
            section (str): Section name.
            name (str): Name of the item.

        Raises:
            ValueError: If item doesn't exist.

        """
        self.get_item_from_section.cache_clear()
        config = configparser.ConfigParser()
        config.read(self._registry_file)
        try:
            _ = config[section][name]
        except KeyError:
            raise ValueError(
                "Registry doesn't contain value {}:{}".format(section, name))
        config.remove_option(section, name)

        # if section is empty, delete it
        if len(config[section].keys()) == 0:
            config.remove_section(section)

        with open(self._registry_file, mode="w") as cfg:
            config.write(cfg)

    def _delete_item(self, name):
        """Delete item from default section.

        Note:
            See :meth:`~pype.lib.IniSettingsRegistry.delete_item_from_section`

        """
        self.delete_item_from_section("MAIN", name)


class JSONSettingRegistry(ASettingRegistry):
    """Class using json file as storage."""

    def __init__(self, name, path):
        # type: (str, str) -> JSONSettingRegistry
        super(JSONSettingRegistry, self).__init__(name)
        #: str: name of registry file
        self._registry_file = os.path.join(path, "{}.json".format(name))
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        header = {
            "__metadata__": {
                "pype-version": os.getenv("OPENPYPE_VERSION", "N/A"),
                "generated": now
            },
            "registry": {}
        }

        if not os.path.exists(os.path.dirname(self._registry_file)):
            os.makedirs(os.path.dirname(self._registry_file), exist_ok=True)
        if not os.path.exists(self._registry_file):
            with open(self._registry_file, mode="w") as cfg:
                json.dump(header, cfg, indent=4)

    @lru_cache(maxsize=32)
    def _get_item(self, name):
        # type: (str) -> object
        """Get item value from registry json.

        Note:
            See :meth:`pype.lib.JSONSettingRegistry.get_item`

        """
        with open(self._registry_file, mode="r") as cfg:
            data = json.load(cfg)
            try:
                value = data["registry"][name]
            except KeyError:
                raise ValueError(
                    "Registry doesn't contain value {}".format(name))
        return value

    def get_item(self, name):
        # type: (str) -> object
        """Get item value from registry json.

        Args:
            name (str): Name of the item.

        Returns:
            value of the item

        Raises:
            ValueError: If item is not found in registry file.

        """
        return self._get_item(name)

    def _set_item(self, name, value):
        # type: (str, object) -> None
        """Set item value to registry json.

        Note:
            See :meth:`pype.lib.JSONSettingRegistry.set_item`

        """
        with open(self._registry_file, "r+") as cfg:
            data = json.load(cfg)
            data["registry"][name] = value
            cfg.truncate(0)
            cfg.seek(0)
            json.dump(data, cfg, indent=4)

    def set_item(self, name, value):
        # type: (str, object) -> None
        """Set item and its value into json registry file.

        Args:
            name (str): name of the item.
            value (Any): value of the item.

        """
        self._set_item(name, value)

    def _delete_item(self, name):
        # type: (str) -> None
        self._get_item.cache_clear()
        with open(self._registry_file, "r+") as cfg:
            data = json.load(cfg)
            del data["registry"][name]
            cfg.truncate(0)
            cfg.seek(0)
            json.dump(data, cfg, indent=4)


class PypeSettingsRegistry(JSONSettingRegistry):
    """Class handling Pype general settings registry.

    Attributes:
        vendor (str): Name used for path construction.
        product (str): Additional name used for path construction.

    """

    def __init__(self):
        self.vendor = "pypeclub"
        self.product = "pype"
        path = appdirs.user_data_dir(self.product, self.vendor)
        super(PypeSettingsRegistry, self).__init__("pype_settings", path)


def _create_local_site_id(registry=None):
    """Create a local site identifier."""
    from uuid import uuid4

    if registry is None:
        registry = PypeSettingsRegistry()

    new_id = str(uuid4())

    print("Created local site id \"{}\"".format(new_id))

    registry.set_item("localId", new_id)

    return new_id


def get_local_site_id():
    """Get local site identifier.

    Identifier is created if does not exists yet.
    """
    registry = PypeSettingsRegistry()
    try:
        return registry.get_item("localId")
    except ValueError:
        return _create_local_site_id()


def change_openpype_mongo_url(new_mongo_url):
    """Change mongo url in pype registry.

    Change of OpenPype mongo URL require restart of running pype processes or
    processes using pype.
    """

    validate_mongo_connection(new_mongo_url)
    registry = PypeSettingsRegistry()
    registry.set_secure_item("pypeMongo", new_mongo_url)
