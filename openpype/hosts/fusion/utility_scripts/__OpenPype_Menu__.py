import os
import sys
import openpype

from openpype.api import Logger

log = Logger().get_logger(__name__)


def main(env):
    from openpype.hosts.fusion.api import menu
    import avalon.fusion
    # Registers pype's Global pyblish plugins
    openpype.install()

    # activate resolve from pype
    avalon.api.install(avalon.fusion)

    log.info(f"Avalon registred hosts: {avalon.api.registered_host()}")

    menu.launch_openpype_menu()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
