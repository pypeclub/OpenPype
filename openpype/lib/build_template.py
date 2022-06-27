import imp
import openpype
from .abstract_template_loader import (
    AbstractPlaceholder,
    AbstractTemplateLoader)

import importlib

from .build_template_exceptions import (
    TemplateLoadingFailed,
    TemplateAlreadyImported,
    MissingHostTemplateModule,
    MissingTemplatePlaceholderClass,
    MissingTemplateLoaderClass
)

_module_path_format = 'openpype.hosts.{host}.template_loader'

def build_workfile_template(*args):

    # raise MissingHostTemplateModule(
    #         "No template loader found for host ")
    template_loader = build_template_loader()
    try:
        template_loader.import_template(template_loader.template_path)
    except TemplateAlreadyImported as err:
        template_loader.template_already_imported(err)
    except TemplateLoadingFailed as err:
        template_loader.template_loading_failed(err)
    else:
        template_loader.populate_template()


def update_workfile_template(*args):
    template_loader = build_template_loader()
    template_loader.update_missing_containers()


def build_template_loader():
    from openpype.pipeline.context_tools import registered_host
    host_name = registered_host().__name__.partition('.')[2]
    host_name = host_name.partition('.')[2]
    module_path = _module_path_format.format(host=host_name)
    print(10,module_path)
    print(11,host_name)
    try :
        module = importlib.import_module(module_path)
    except :
        raise Exception(host_name + "    " +registered_host().__name__ )
    if not module:
        raise MissingHostTemplateModule(
            "No template loader found for host {}".format(host_name))

    template_loader_class = openpype.lib.classes_from_module(
        AbstractTemplateLoader, module)
    template_placeholder_class = openpype.lib.classes_from_module(
        AbstractPlaceholder, module)

    if not template_loader_class:
        raise MissingTemplateLoaderClass()
    template_loader_class = template_loader_class[0]

    if not template_placeholder_class:
        raise MissingTemplatePlaceholderClass()
    template_placeholder_class = template_placeholder_class[0]
    return template_loader_class(template_placeholder_class)
