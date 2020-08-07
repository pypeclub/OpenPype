from collections import OrderedDict
import avalon.api
import avalon.nuke
from pype import api as pype

import nuke


class CrateRead(avalon.nuke.Creator):
    # change this to template preset
    name = "ReadCopy"
    label = "Create Read Copy"
    hosts = ["nuke"]
    family = "source"
    families = family
    icon = "film"
    defaults = ["Effect", "Backplate", "Fire", "Smoke"]

    def __init__(self, *args, **kwargs):
        super(CrateRead, self).__init__(*args, **kwargs)
        self.nodes = nuke.selectedNodes()
        data = OrderedDict()
        data['family'] = self.family
        data['families'] = self.families

        for k, v in self.data.items():
            if k not in data.keys():
                data.update({k: v})

        self.data = data

    def process(self):
        self.name = self.data["subset"]
        nodes = self.nodes

        if not nodes or len(nodes) == 0:
            msg = "Please select Read node"
            self.log.error(msg)
            nuke.message(msg)
        else:
            count_reads = 0
            for node in nodes:
                if node.Class() != 'Read':
                    continue
                avalon_data = self.data
                avalon_data['subset'] = "{}".format(self.name)
                self.change_read_node(self.data["subset"], node, avalon_data)
                count_reads += 1

            if count_reads < 1:
                msg = "Please select Read node"
                self.log.error(msg)
                nuke.message(msg)
        return

    def change_read_node(self, name, node, data):
        node = avalon.nuke.lib.imprint(node, data)
        node['tile_color'].setValue(16744935)
