import tempfile
import zipfile
import os
import shutil

from avalon import api, harmony


class ImportTemplateLoader(api.Loader):
    """Import templates or workfiles."""

    families = ["scene"]
    representations = ["*"]
    label = "Import Template"
    icon = "floppy-o"

    def load(self, context, name=None, namespace=None, data=None):
        # Import template.
        temp_dir = tempfile.mkdtemp()
        zip_file = api.get_representation_path(context["representation"])
        template_path = os.path.join(temp_dir, "temp.tpl")
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(template_path)

        func = """function func(args)
        {
            var template_path = args[0];
            var drag_object = copyPaste.pasteTemplateIntoGroup(
                template_path, "Top", 1
            );
        }
        func
        """

        harmony.send({"function": func, "args": [template_path]})

        shutil.rmtree(temp_dir)

        subset_name = context["subset"]["name"]

        return harmony.containerise(
            subset_name,
            namespace,
            subset_name,
            context,
            self.__class__.__name__
        )

        def update(self, container, representation):
            pass

        def remove(self, container):
            pass


class ImportWorkfileLoader(ImportTemplateLoader):
    """Import workfiles."""

    families = ["workfile"]
    representations = ["zip"]
    label = "Import Workfile"
