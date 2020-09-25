import glob
import os
import shutil
import six
import sys
import tempfile
import zipfile

import pyblish.api
from avalon import api, io
import pype.api


class ExtractHarmonyZip(pype.api.Extractor):
    """Extract Harmony zip"""

    # Pyblish settings
    label = "Extract Harmony zip"
    order = pyblish.api.ExtractorOrder + 0.02
    hosts = ["standalonepublisher"]
    families = ["scene"]

    # Properties
    session = None
    task_types = None
    task_statuses = None
    assetversion_statuses = None

    # Presets
    create_workfile = True
    default_task = "harmonyIngest"
    default_task_type = "Ingest"
    default_task_status = "Ingested"
    assetversion_status = "Ingested"

    def process(self, instance):
        """The main pyblish process method for Extract Harmony Zip Extractor"""
        context = instance.context
        self.session = context.data["ftrackSession"]
        asset_doc = context.data["assetEntity"]
        asset_name = instance.data["asset"]
        subset_name = instance.data["subset"]
        instance_name = instance.data["name"]
        family = instance.data["family"]
        task = context.data["anatomyData"]["task"] or self.default_task
        project_entity = instance.context.data["projectEntity"]
        ftrack_id = asset_doc["data"]["ftrackId"]
        repres = instance.data["representations"]
        submitted_staging_dir = repres[0]["stagingDir"]
        submitted_files = repres[0]["files"]

        # Get all the ftrack entities needed

        # Asset Entity
        query = 'AssetBuild where id is "{}"'.format(ftrack_id)
        asset_entity = self.session.query(query).first()

        # Project Entity
        query = 'Project where full_name is "{}"'.format(
            project_entity["name"]
        )
        project_entity = self.session.query(query).one()

        # Get Task types and Statuses for creation if needed
        self.task_types = self.get_all_task_types(project_entity)
        self.task_statuses = self.get_all_task_statuses(project_entity)

        # Get Statuses of AssetVersions
        self.assetversion_statuses = self.get_all_assetversion_statuses(
            project_entity
        )

        # Setup the status that we want for the AssetVersion
        if self.assetversion_status:
            instance.data["assetversion_status"] = self.assetversion_status

        # Create the default_task if it does not exist
        if task == self.default_task:
            existing_tasks = []
            entity_children = asset_entity.get('children', [])
            for child in entity_children:
                if child.entity_type.lower() == 'task':
                    existing_tasks.append(child['name'].lower())

            if task.lower() in existing_tasks:
                print("Task {} already exists".format(task))

            else:
                self.create_task(
                    name=task,
                    task_type=self.default_task_type,
                    task_status=self.default_task_status,
                    parent=asset_entity,
                )

        # Find latest version
        latest_version = self.find_last_version(subset_name, asset_doc)
        version_number = 1
        if latest_version is not None:
            version_number += latest_version

        self.log.info(
            "Next version of instance \"{}\" will be {}".format(
                instance_name, version_number
            )
        )

        # update instance info
        instance.data["task"] = task
        instance.data["version_name"] = "{}_{}".format(subset_name, task)
        instance.data["family"] = family
        instance.data["subset"] = subset_name
        instance.data["version"] = version_number
        instance.data["latestVersion"] = latest_version
        instance.data["anatomyData"].update({
            "subset": subset_name,
            "family": family,
            "version": version_number
        })

        # Copy `families` and check if `family` is not in current families
        families = instance.data.get("families") or list()
        if families:
            families = list(set(families))

        instance.data["families"] = families

        # Prepare staging dir for new instance and zip + sanitize scene name
        staging_dir = tempfile.mkdtemp(prefix="pyblish_tmp_")

        # Handle if the representation is a .zip and not an .xstage
        pre_staged = False
        if submitted_files.endswith(".zip"):
            submitted_zip_file = os.path.join(submitted_staging_dir,
                                              submitted_files
                                              ).replace("\\", "/")

            pre_staged = self.sanitize_prezipped_project(instance,
                                                         submitted_zip_file,
                                                         staging_dir)

        # Get the file to work with
        source_dir = str(repres[0]["stagingDir"])
        source_file = str(repres[0]["files"])

        staging_scene_dir = os.path.join(staging_dir, "scene")
        staging_scene = os.path.join(staging_scene_dir, source_file)

        # If the file is an .xstage / directory, we must stage it
        if not pre_staged:
            shutil.copytree(source_dir, staging_scene_dir)

        # Rename this latest file as 'scene.xstage'
        # This is is determined in the collector from the latest scene in a
        # submitted directory / directory the submitted .xstage is in.
        # In the case of a zip file being submitted, this is determined within
        # the self.sanitize_project() method in this extractor.
        os.rename(staging_scene,
                  os.path.join(staging_scene_dir, "scene.xstage")
                  )

        # Required to set the current directory where the zip will end up
        os.chdir(staging_dir)

        # Create the zip file
        zip_filepath = shutil.make_archive(os.path.basename(source_dir),
                                           "zip",
                                           staging_scene_dir
                                           )

        zip_filename = os.path.basename(zip_filepath)

        self.log.info("Zip file: {}".format(zip_filepath))

        # Setup representation
        new_repre = {
            "name": "zip",
            "ext": "zip",
            "files": zip_filename,
            "stagingDir": staging_dir
        }

        self.log.debug(
            "Creating new representation: {}".format(new_repre)
        )
        instance.data["representations"] = [new_repre]

        self.log.debug("Completed prep of zipped Harmony scene: {}"
                       .format(zip_filepath)
                       )

        # If this extractor is setup to also extract a workfile...
        if self.create_workfile:
            workfile_path = self.extract_workfile(instance,
                                                  staging_scene
                                                  )

            self.log.debug("Extracted Workfile to: {}".format(workfile_path))

    def extract_workfile(self, instance, staging_scene):
        """Extract a valid workfile for this corresponding publish"""

        # Since the staging scene was renamed to "scene.xstage" for publish
        # rename the staging scene in the temp stagingdir
        staging_scene = os.path.join(os.path.dirname(staging_scene),
                                     "scene.xstage")

        # Setup the data needed to form a valid work path filename
        anatomy = pype.api.Anatomy()
        project_entity = instance.context.data["projectEntity"]

        data = {"root": api.registered_root(),
                "project": {
                    "name": project_entity["name"],
                    "code": project_entity["data"].get("code", '')
                },
                "asset": instance.data["asset"],
                "hierarchy": pype.api.get_hierarchy(instance.data["asset"]),
                "family": instance.data["family"],
                "task": instance.data.get("task"),
                "subset": instance.data["subset"],
                "version": 1,
                "ext": "zip",
                }

        # Get a valid work filename first with version 1
        file_template = anatomy.templates["work"]["file"]
        anatomy_filled = anatomy.format(data)
        work_path = anatomy_filled["work"]["path"]

        # Get the final work filename with the proper version
        data["version"] = api.last_workfile_with_version(
            os.path.dirname(work_path), file_template, data, [".zip"]
        )[1]

        work_path = anatomy_filled["work"]["path"]
        base_name = os.path.splitext(os.path.basename(work_path))[0]

        staging_work_path = os.path.join(os.path.dirname(staging_scene),
                                         base_name + ".xstage"
                                         )

        # Rename this latest file after the workfile path filename
        os.rename(staging_scene, staging_work_path)

        # Required to set the current directory where the zip will end up
        os.chdir(os.path.dirname(os.path.dirname(staging_scene)))

        # Create the zip file
        zip_filepath = shutil.make_archive(base_name,
                                           "zip",
                                           os.path.dirname(staging_scene)
                                           )
        self.log.info(staging_scene)
        self.log.info(work_path)
        self.log.info(staging_work_path)
        self.log.info(os.path.dirname(os.path.dirname(staging_scene)))
        self.log.info(base_name)
        self.log.info(zip_filepath)

        # Create the work path on disk if it does not exist
        os.makedirs(os.path.dirname(work_path), exist_ok=True)
        shutil.copy(zip_filepath, work_path)

        return work_path

    def sanitize_prezipped_project(self, instance, zip_filepath, staging_dir):
        """This method is just to fix when a zip contains a folder instead of
        the project in the root of the zip file
        """
        zip = zipfile.ZipFile(zip_filepath)
        zip_contents = zipfile.ZipFile.namelist(zip)

        # Determine if any xstage file is in root of zip
        project_in_root = [pth for pth in zip_contents
                           if not "/" in pth and pth.endswith(".xstage")]

        staging_scene_dir = os.path.join(staging_dir, "scene")

        # The project is nested, so we must extract and move it
        if not project_in_root:

            staging_tmp_dir = os.path.join(staging_dir, "tmp")

            with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
                zip_ref.extractall(staging_tmp_dir)

            nested_project_folder = os.path.join(staging_tmp_dir,
                                                 zip_contents[0]
                                                 )

            shutil.copytree(nested_project_folder, staging_scene_dir)

        else:
            # The project is not nested, so we just extract to scene folder
            with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
                zip_ref.extractall(staging_scene_dir)

        latest_file = max(glob.iglob(staging_scene_dir + "/*.xstage"),
                          key=os.path.getctime).replace("\\", "/")

        instance.data["representations"][0]["stagingDir"] = staging_scene_dir
        instance.data["representations"][0]["files"] = os.path.basename(
            latest_file)

        # We have staged the scene already so return True
        return True

    def find_last_version(self, subset_name, asset_doc):
        subset_doc = io.find_one({
            "type": "subset",
            "name": subset_name,
            "parent": asset_doc["_id"]
        })

        if subset_doc is None:
            self.log.debug("Subset entity does not exist yet.")
        else:
            version_doc = io.find_one(
                {
                    "type": "version",
                    "parent": subset_doc["_id"]
                },
                sort=[("name", -1)]
            )
            if version_doc:
                return int(version_doc["name"])
        return None

    def get_all_task_types(self, project):
        tasks = {}
        proj_template = project['project_schema']
        temp_task_types = proj_template['_task_type_schema']['types']

        for type in temp_task_types:
            if type['name'] not in tasks:
                tasks[type['name']] = type

        return tasks

    def get_all_task_statuses(self, project):
        statuses = {}
        proj_template = project['project_schema']
        temp_task_statuses = proj_template.get_statuses("Task")

        for status in temp_task_statuses:
            if status['name'] not in statuses:
                statuses[status['name']] = status

        return statuses

    def get_all_assetversion_statuses(self, project):
        statuses = {}
        proj_template = project['project_schema']
        temp_task_statuses = proj_template.get_statuses("AssetVersion")

        for status in temp_task_statuses:
            if status['name'] not in statuses:
                statuses[status['name']] = status

        return statuses

    def create_task(self, name, task_type, parent, task_status):
        task_data = {
            'name': name,
            'parent': parent,
        }
        self.log.info(task_type)
        task_data['type'] = self.task_types[task_type]
        task_data['status'] = self.task_statuses[task_status]
        self.log.info(task_data)
        task = self.session.create('Task', task_data)
        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            six.reraise(tp, value, tb)

        return task
