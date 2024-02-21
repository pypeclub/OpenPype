from pathlib import Path
import tempfile

from openpype.hosts.blender.hooks import pre_add_run_python_script_arg
from openpype.lib import PreLaunchHook


class SetSceneProperties(PreLaunchHook):
    """Set required scene data for custom scripts
    """

    order = pre_add_run_python_script_arg.AddPythonScriptToLaunchArgs.order - 1
    app_groups = [
        "blender",
    ]
    script_file_name = 'set_scene_properties.py'

    def get_formatted_outputs_paths(self):
        data = self.launch_context.data

        # This value is hardcoded because the farm's workers are based on Linux.
        # In the future there should be a way to get this info somewhere.
        target_os = "linux"
        current_os = data['env']['OS']
        hierarchy = data['workdir_data']['hierarchy']
        entity_name = data['asset_name']
        task_name = data['task_name']

        target_work_dir = self._get_correct_work_dir(data, target_os)
        current_work_dir = self._get_correct_work_dir(data, current_os)
        if not target_work_dir:
            self.log.warning(f"Can't find correct work directory for os {target_os}. Can't set default output path.")
            return '/tmp/'

        if not current_work_dir:
            self.log.warning(f"Can't find correct work directory for os {current_work_dir}. Can't set default output path.")
            return '/tmp/'

        try:
            base_output_path = Path(
                    data['project_name'],
                    hierarchy,
                    entity_name,
                    'publish',
                    'render',
                )
            deadline_render_layer_path = self._generate_render_path_with_version(
                target_work_dir, base_output_path, data['project_name'], entity_name
            )
            deadline_output_path = self._generate_render_path_without_version(
                current_work_dir, base_output_path, data['project_name'], entity_name
            )
            playblast_render_path = self._generate_playblast_path(
                current_work_dir, base_output_path, task_name, data['project_name'], entity_name
            )
            return deadline_render_layer_path, deadline_output_path, playblast_render_path

        except IndexError as err:
            self.log.warning("Value is missing from launch_context data. Can't set default output path.")
            self.log.warning(err)
            tempdir = tempfile.gettempdir(),
            return tempdir, tempdir, tempdir

    def _get_correct_work_dir(self, data, given_os):
        work_directories = data['project_doc']['config']['roots']['work']
        retrieved_work_dir = None
        for retrieved_os, work_folder_path in work_directories.items():
            if given_os.lower().startswith(retrieved_os.lower()):
                retrieved_work_dir = work_folder_path
                break

        return retrieved_work_dir


    def _generate_render_path_with_version(self, work_dir, base_path, project_name, entity_name):
        return Path(
            work_dir,
            base_path,
            '{version}',
            '{render_layer_name}',
            '_'.join([project_name, entity_name, '{render_layer_name}', '{version}'])
        )

    def _generate_render_path_without_version(self, work_dir, base_path, project_name, entity_name):
        return Path(
            work_dir,
            base_path,
            '{render_layer_name}',
            '_'.join([project_name, entity_name, '{render_layer_name}'])
        )

    def _generate_playblast_path(self, work_dir, base_path, task_name, project_name, entity_name):
        subset_name = f'playblast{task_name}Main'
        file_suffix = '{version}.{extension}'
        return Path(
            work_dir,
            base_path,
            subset_name,
            '{version}',
            f'{entity_name}_{subset_name}_{file_suffix}'
        )

    def execute(self):
        hooks_folder_path = Path(__file__).parent
        custom_script_folder = hooks_folder_path.parent.joinpath("blender_addon", "startup", "custom_scripts")

        script_file = custom_script_folder.joinpath(self.script_file_name)
        if not script_file.exists() or not script_file.is_file():
            raise FileNotFoundError(f"Can't find {self.script_file_name} in {custom_script_folder}.")

        self.launch_context.data.setdefault("python_scripts", []).append(
            custom_script_folder.joinpath(self.script_file_name)
        )
        deadline_render_layer_path, deadline_output_path, playblast_render_path = self.get_formatted_outputs_paths()
        self.launch_context.data.setdefault("script_args", []).extend(
            [
                '--render-layer-path',
                deadline_render_layer_path,
                '--output-path',
                deadline_output_path,
                '--playblast-render-path',
                playblast_render_path
            ]
        )