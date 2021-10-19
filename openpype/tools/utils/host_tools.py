"""Single access point to all tools usable in hosts.

It is possible to create `HostToolsHelper` in host implementaion or
use singleton approach with global functions (using helper anyway).
"""

import avalon.api


class HostToolsHelper:
    """Create and cache tool windows in memory.

    Almost all methods expect parent widget but the parent is used only on
    first tool creation.

    Class may also contain tools that are available only for one or few hosts.
    """
    def __init__(self, parent=None):
        self._log = None
        # Global parent for all tools (may and may not be set)
        self._parent = parent

        # Prepare attributes for all tools
        self._workfiles_tool = None
        self._loader_tool = None
        self._creator_tool = None
        self._subset_manager_tool = None
        self._scene_inventory_tool = None
        self._library_loader_tool = None
        self._look_assigner_tool = None

    @property
    def log(self):
        if self._log is None:
            from openpype.api import Logger

            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def get_workfiles_tool(self, parent):
        """Create, cache and return workfiles tool window."""
        if self._workfiles_tool is None:
            from avalon import style
            from openpype.tools.workfiles.app import (
                Window, validate_host_requirements
            )
            # Host validation
            host = avalon.api.registered_host()
            validate_host_requirements(host)

            workfiles_window = Window(parent=parent)
            workfiles_window.setStyleSheet(style.load_stylesheet())
            self._workfiles_tool = workfiles_window

        return self._workfiles_tool

    def show_workfiles(self, parent=None, use_context=None, save=None):
        """Workfiles tool for changing context and saving workfiles."""
        if use_context is None:
            use_context = True

        if save is None:
            save = True

        workfiles_tool = self.get_workfiles_tool(parent)
        if use_context:
            context = {
                "asset": avalon.api.Session["AVALON_ASSET"],
                "silo": avalon.api.Session["AVALON_SILO"],
                "task": avalon.api.Session["AVALON_TASK"]
            }
            workfiles_tool.set_context(context)

        if save:
            workfiles_tool.set_save_enabled(save)

        workfiles_tool.refresh()
        workfiles_tool.show()
        # Pull window to the front.
        workfiles_tool.raise_()
        workfiles_tool.activateWindow()

    def get_loader_tool(self, parent):
        """Create, cache and return loader tool window."""
        if self._loader_tool is None:
            from avalon import style
            from openpype.tools.loader import LoaderWindow

            loader_window = LoaderWindow(parent=parent or self._parent)
            loader_window.setStyleSheet(style.load_stylesheet())
            self._loader_tool = loader_window

        return self._loader_tool

    def show_loader(self, parent=None, use_context=None):
        """Loader tool for loading representations."""
        if use_context is None:
            use_context = False
        loader_tool = self.get_loader_tool(parent)

        if use_context:
            context = {"asset": avalon.api.Session["AVALON_ASSET"]}
            loader_tool.set_context(context, refresh=True)
        else:
            loader_tool.refresh()

        loader_tool.show()
        loader_tool.raise_()
        loader_tool.activateWindow()
        loader_tool.refresh()

    def get_creator_tool(self, parent):
        """Create, cache and return creator tool window."""
        if self._creator_tool is None:
            from avalon import style
            from avalon.tools.creator.app import Window

            creator_window = Window(parent=parent or self._parent)
            creator_window.setStyleSheet(style.load_stylesheet())
            self._creator_tool = creator_window

        return self._creator_tool

    def show_creator(self, parent=None):
        """Show tool to create new instantes for publishing."""
        creator_tool = self.get_creator_tool(parent)
        creator_tool.refresh()
        creator_tool.show()

        # Pull window to the front.
        creator_tool.raise_()
        creator_tool.activateWindow()

    def get_subset_manager_tool(self, parent):
        """Create, cache and return subset manager tool window."""
        if self._subset_manager_tool is None:
            from avalon import style
            from avalon.tools.subsetmanager import Window

            subset_manager_window = Window(parent=parent or self._parent)
            subset_manager_window.setStyleSheet(style.load_stylesheet())
            self._subset_manager_tool = subset_manager_window

        return self._subset_manager_tool

    def show_subset_manager(self, parent=None):
        """Show tool display/remove existing created instances."""
        subset_manager_tool = self.get_subset_manager_tool(parent)
        subset_manager_tool.show()

        # Pull window to the front.
        subset_manager_tool.raise_()
        subset_manager_tool.activateWindow()

    def get_scene_inventory_tool(self, parent):
        """Create, cache and return scene inventory tool window."""
        if self._scene_inventory_tool is None:
            from avalon import style
            from avalon.tools.sceneinventory.app import Window

            scene_inventory_window = Window(parent=parent or self._parent)
            scene_inventory_window.setStyleSheet(style.load_stylesheet())
            self._scene_inventory_tool = scene_inventory_window

        return self._scene_inventory_tool

    def show_scene_inventory(self, parent=None):
        """Show tool maintain loaded containers."""
        scene_inventory_tool = self.get_scene_inventory_tool(parent)
        scene_inventory_tool.show()
        scene_inventory_tool.refresh()

        # Pull window to the front.
        scene_inventory_tool.raise_()
        scene_inventory_tool.activateWindow()

    def get_library_loader_tool(self, parent):
        """Create, cache and return library loader tool window."""
        if self._library_loader_tool is None:
            from avalon import style
            from openpype.tools.libraryloader import LibraryLoaderWindow

            library_window = LibraryLoaderWindow(
                parent=parent or self._parent
            )
            library_window.setStyleSheet(style.load_stylesheet())
            self._library_loader_tool = library_window

        return self._library_loader_tool

    def show_library_loader(self, parent=None):
        """Loader tool for loading representations from library project."""
        library_loader_tool = self.get_library_loader_tool(parent)
        library_loader_tool.show()
        library_loader_tool.raise_()
        library_loader_tool.activateWindow()
        library_loader_tool.refresh()

    def show_publish(self, parent=None):
        """Publish UI."""
        from avalon.tools import publish

        publish.show(parent)

    def get_look_assigner_tool(self, parent):
        """Create, cache and return look assigner tool window."""
        if self._look_assigner_tool is None:
            from avalon import style
            import mayalookassigner

            mayalookassigner_window = mayalookassigner.App(parent)
            mayalookassigner_window.setStyleSheet(style.load_stylesheet())
            self._look_assigner_tool = mayalookassigner_window
        return self._look_assigner_tool

    def show_look_assigner(self, parent=None):
        """Look manager is Maya specific tool for look management."""
        look_assigner_tool = self.get_look_assigner_tool(parent)
        look_assigner_tool.show()

    def get_tool_by_name(self, tool_name, parent=None, *args, **kwargs):
        """Show tool by it's name.

        This is helper for
        """
        if tool_name == "workfiles":
            return self.get_workfiles_tool(parent, *args, **kwargs)

        elif tool_name == "loader":
            return self.get_loader_tool(parent, *args, **kwargs)

        elif tool_name == "libraryloader":
            return self.get_library_loader_tool(parent, *args, **kwargs)

        elif tool_name == "creator":
            return self.get_creator_tool(parent, *args, **kwargs)

        elif tool_name == "subsetmanager":
            return self.get_subset_manager_tool(parent, *args, **kwargs)

        elif tool_name == "sceneinventory":
            return self.get_scene_inventory_tool(parent, *args, **kwargs)

        elif tool_name == "lookassigner":
            return self.get_look_assigner_tool(parent, *args, **kwargs)

        elif tool_name == "publish":
            self.log.info("Can't return publish tool window.")

        else:
            self.log.warning(
                "Can't show unknown tool name: \"{}\"".format(tool_name)
            )

    def show_tool_by_name(self, tool_name, parent=None, *args, **kwargs):
        """Show tool by it's name.

        This is helper for
        """
        if tool_name == "workfiles":
            self.show_workfiles(parent, *args, **kwargs)

        elif tool_name == "loader":
            self.show_loader(parent, *args, **kwargs)

        elif tool_name == "libraryloader":
            self.show_library_loader(parent, *args, **kwargs)

        elif tool_name == "creator":
            self.show_creator(parent, *args, **kwargs)

        elif tool_name == "subsetmanager":
            self.show_subset_manager(parent, *args, **kwargs)

        elif tool_name == "sceneinventory":
            self.show_scene_inventory(parent, *args, **kwargs)

        elif tool_name == "lookassigner":
            self.show_look_assigner(parent, *args, **kwargs)

        elif tool_name == "publish":
            self.show_publish(parent, *args, **kwargs)

        else:
            self.log.warning(
                "Can't show unknown tool name: \"{}\"".format(tool_name)
            )


class _SingletonPoint:
    """Singleton access to host tools.

    Some hosts don't have ability to create 'HostToolsHelper' object anc can
    only register function callbacks. For those cases is created this singleton
    point where 'HostToolsHelper' is created "in shared memory".
    """
    helper = None

    @classmethod
    def _create_helper(cls):
        if cls.helper is None:
            cls.helper = HostToolsHelper()

    @classmethod
    def show_tool_by_name(cls, tool_name, parent=None, *args, **kwargs):
        cls._create_helper()
        cls.helper.show_tool_by_name(tool_name, parent, *args, **kwargs)

    @classmethod
    def get_tool_by_name(cls, tool_name, parent=None, *args, **kwargs):
        cls._create_helper()
        return cls.helper.get_tool_by_name(tool_name, parent, *args, **kwargs)


# Function callbacks using singleton acces point
def get_tool_by_name(tool_name, parent=None, *args, **kwargs):
    return _SingletonPoint.get_tool_by_name(tool_name, parent, *args, **kwargs)


def show_tool_by_name(tool_name, parent=None, *args, **kwargs):
    _SingletonPoint.show_tool_by_name(tool_name, parent, *args, **kwargs)


def show_workfiles(parent=None, use_context=None, save=None):
    _SingletonPoint.show_tool_by_name(
        "workfiles", parent, use_context=use_context, save=save
    )


def show_loader(parent=None, use_context=None):
    _SingletonPoint.show_tool_by_name(
        "loader", parent, use_context=use_context
    )


def show_library_loader(parent=None):
    _SingletonPoint.show_tool_by_name("libraryloader", parent)


def show_creator(parent=None):
    _SingletonPoint.show_tool_by_name("creator", parent)


def show_subset_manager(parent=None):
    _SingletonPoint.show_tool_by_name("subsetmanager", parent)


def show_scene_inventory(parent=None):
    _SingletonPoint.show_tool_by_name("sceneinventory", parent)


def show_look_assigner(parent=None):
    _SingletonPoint.show_tool_by_name("lookassigner", parent)


def show_publish(parent=None):
    _SingletonPoint.show_tool_by_name("publish", parent)
