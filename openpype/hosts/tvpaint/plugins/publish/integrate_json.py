import json
import re
import os

import pyblish.api


class IntegrateJson(pyblish.api.InstancePlugin):
    """Integrate a JSON file."""

    label = "Integrate Json File"
    order = pyblish.api.IntegratorOrder + 0.05

    hosts = ["tvpaint"]
    families = ["renderLayer", "renderPass"]

    def process(self, instance):
        self.log.info(
            "* Processing instance \"{}\"".format(instance.data["label"])
        )

        if not instance.data.get('json_output_dir'):
            return

        for repre in instance.data.get("representations"):
            if repre['name'] != 'png' or 'review' in repre['tags']:
                continue

            if "renderLayer" in instance.data.get('families'):
                instance.context.data['custom_published_path'] = repre['published_path']
                continue

            layer_name = instance.data.get('layer_names')[0]

            published_layer_data = self._update_with_published_file(
                instance.context.data['tvpaint_layers_data'],
                repre['published_path'],
                layer_name
            )

            json_repre = self._get_json_repre(instance.data)
            json_publish_path = json_repre['published_path']
            new_json_publish_path = self._set_new_json_publish_path(
                instance.context.data['custom_published_path'],
            )

            with open(json_publish_path, "r+") as publish_json, \
                    open(new_json_publish_path, "w") as new_publish_json:
                published_data = json.load(publish_json)

                published_data['project']['clip']['layers'].append(
                    published_layer_data
                )
                new_publish_json.seek(0)
                json.dump(published_data, new_publish_json, indent=4)
                new_publish_json.truncate()

            self.log.debug('Add layer_data to Json file: {}'.format(
                new_json_publish_path
            ))

            repre['published_path'] = new_json_publish_path
            self.log.debug("New representation: {}".format(repre))

    def _update_with_published_file(self, layer_data, publish_path, layer_name):
        """Update published file path in the json file extracted.
        """
        for layer in layer_data:
            if layer['name'] == layer_name:
                for link in layer['link']:
                    link_frame = re.search(r'\.(\d*)\.png$', link['file']).groups()[0]
                    new_file_path = re.sub(
                        r'(.*\.)(\d*)(\.png)$',
                        '\g<1>{}\g<3>'.format(link_frame),
                        publish_path
                    )
                    link['file'] = new_file_path

        self.log.debug("Updated layer_data: {}".format(layer_data))
        return layer_data

    def _get_json_repre(self, context):
        """Get the json representation of the instance.
        Raises error if more than one representation is found.
        """
        json_repre = []
        for repre in context.get("representations"):
            if repre['name'] != 'json':
                continue
            json_repre.append(repre)

        if len(json_repre) != 1:
            raise Exception(
                'Exporting multiple json is not supported: {}'.format(
                    json_repre
                )
            )

        return json_repre[0]

    def _set_new_json_publish_path(self, custom_published_path):
        published_path = os.path.dirname(custom_published_path)
        filename = os.path.splitext(os.path.basename(custom_published_path))[0]
        filename = filename.split('.')[0] + '.json'
        json_published_path = os.path.join(published_path, filename)

        return json_published_path
