from openpype.hosts.nuke.api.lib_template_builder import (
    delete_placeholder_attributes, get_placeholder_attributes,
    hide_placeholder_attributes)
from openpype.lib.abstract_template_loader import (
    AbstractPlaceholder,
    AbstractTemplateLoader)
# from openpype.lib.build_template_exceptions import TemplateAlreadyImported
import nuke
from collections import defaultdict
from openpype.hosts.nuke.api.lib import (
    find_free_space_to_paste_nodes, get_extremes, get_io, imprint,
    refresh_node, refresh_nodes, reset_selection,
    get_names_from_nodes, get_nodes_from_names)
PLACEHOLDER_SET = 'PLACEHOLDERS_SET'


class NukeTemplateLoader(AbstractTemplateLoader):
    """Concrete implementation of AbstractTemplateLoader for Nuke

    """

    def import_template(self, path):
        """Import template into current scene.
        Block if a template is already loaded.

        Args:
            path (str): A path to current template (usually given by
            get_template_path implementation)

        Returns:
            bool: Wether the template was succesfully imported or not
        """
        
        # TODO check if the template is already imported

        nuke.nodePaste(path)
        reset_selection()
    
        return True

    def preload(self, placeholder, loaders_by_name, last_representation):
        placeholder.data["nodes_init"] = nuke.allNodes()
        placeholder.data["_id"] = last_representation['_id']

        reset_selection()
        groups_name = placeholder.data['group_name']

        if groups_name:
            # nuke.nodeCopy("%clipboard%")
            # for n in nuke.selectedNodes():
            #     nuke.delete(n)
            group = nuke.toNode(groups_name)
            group.begin()
            # nuke.nodePaste("%clipboard%")
            for n in nuke.selectedNodes():
                refresh_node(n)

    def populate_template(self, ignored_ids=None):
        place_holders = self.get_template_nodes()            
        while len(place_holders) > 0:
            super().populate_template(ignored_ids)
            place_holders = self.get_template_nodes()

    @staticmethod
    def get_template_nodes():
        placeholders = []
        allGroups = [nuke.thisGroup()]
        while len(allGroups) > 0:
            group = allGroups.pop(0)
            for node in group.nodes():
                if "builder_type" in node.knobs().keys() and (
                    'is_placeholder' not in node.knobs().keys()
                        or 'is_placeholder' in node.knobs().keys()
                        and node.knob('is_placeholder').value()):
                    if 'empty' in node.knobs().keys()\
                            and node.knob('empty').value():
                        continue
                    placeholders += [node]
                if isinstance(node, nuke.Group):
                    allGroups.append(node)

        return placeholders

    def update_missing_containers(self):
        nodes_byId = {}
        nodes_byId = defaultdict(lambda: [], nodes_byId)
        for n in nuke.allNodes():
            refresh_node(n)
            if 'id_rep' in n.knobs().keys():
                nodes_byId[n.knob('id_rep').getValue()] = []
        for n in nuke.allNodes():
            if 'id_rep' in n.knobs().keys():
                nodes_byId[n.knob('id_rep').getValue()] += [n.name()]
        for s in nodes_byId.values():
            n = None
            for name in s:
                n = nuke.toNode(name)
                if 'builder_type' in n.knobs().keys():
                    break
            if n is not None and 'builder_type' in n.knobs().keys():

                placeholder = nuke.nodes.NoOp()
                placeholder.setName('PLACEHOLDER')
                placeholder.knob('tile_color').setValue(4278190335)
                attributes = get_placeholder_attributes(n, enumerate=True)
                imprint(placeholder, attributes)
                x = int(n.knob('x').getValue())
                y = int(n.knob('y').getValue())
                placeholder.setXYpos(x, y)
                imprint(placeholder, {'nb_children': 1})
                refresh_node(placeholder)

        self.populate_template(self.get_loaded_containers_by_id())

    def get_loaded_containers_by_id(self):
        ids = []
        for n in nuke.allNodes():
            if 'id_rep' in n.knobs():
                ids.append(n.knob('id_rep').getValue())

        # Removes duplicates in the list
        ids = list(set(ids))
        return ids

    def get_placeholders(self):
        placeholders = super().get_placeholders()
        return placeholders
   
    def delete_placeholder(self, placeholder):
        #  min_x, min_y , max_x, max_y = get_extremes(nodes_loaded)
        node = placeholder.data['node']
        lastLoaded = placeholder.data['last_loaded']
        if 'delete' in placeholder.data.keys()\
                and placeholder.data['delete'] is False:
            imprint(node, {"empty": True})
        else:
            if lastLoaded:
                if 'last_loaded' in node.knobs().keys():
                    for s in node.knob('last_loaded').values():
                        n = nuke.toNode(s)
                        try:
                            delete_placeholder_attributes(n)
                        except Exception:
                            pass

                lastLoaded_names = []
                for loadedNode in lastLoaded:
                    lastLoaded_names.append(loadedNode.name())
                imprint(node, {'last_loaded': lastLoaded_names})
                
                for n in lastLoaded:
                    refresh_node(n)
                    refresh_node(node)
                    if 'builder_type' not in n.knobs().keys():
                        attributes = get_placeholder_attributes(node, True)
                        imprint(n, attributes)
                        imprint(n, {'is_placeholder': False})
                        hide_placeholder_attributes(n)
                        n.knob('is_placeholder').setVisible(False)
                        imprint(n, {'x': node.xpos(), 'y': node.ypos()})
                        n.knob('x').setVisible(False)
                        n.knob('y').setVisible(False)
            nuke.delete(node)


class NukePlaceholder(AbstractPlaceholder):
    """Concrete implementation of AbstractPlaceholder for Nuke

    """

    optional_attributes = {'asset', 'subset', 'hierarchy'}

    def get_data(self, node):
        user_data = dict()
        dictKnobs = node.knobs()
        for attr in self.attributes.union(self.optional_attributes):
            if attr in dictKnobs.keys():
                user_data[attr] = dictKnobs[attr].getValue()
        user_data['node'] = node
        if 'nodes_toReplace' in dictKnobs.keys():
            names = dictKnobs['nodes_toReplace'].values()
            nodes = []
            for name in names:
                nodes.append(nuke.toNode(name))
            user_data['nodes_toReplace'] = nodes
        else:
            user_data['nodes_toReplace'] = [node]

        if 'nb_children' in dictKnobs.keys():
            user_data['nb_children'] = int(dictKnobs['nb_children'].getValue())
        else:
            user_data['nb_children'] = 0
        if 'siblings' in dictKnobs.keys():
            user_data['siblings'] = dictKnobs['siblings'].values()
        else:
            user_data['siblings'] = []

        fullName = node.fullName()
        user_data['group_name'] = fullName.rpartition('.')[0]
        user_data['last_loaded'] = []

        self.data = user_data

    def parent_in_hierarchy(self, containers):
        return 

    def create_sib_copies(self):
        # creating copies of the palce_holder siblings (the ones who were
        # loaded with it) for the new nodes added
        copies = {}
        siblings = get_nodes_from_names(self.data['siblings'])
        for n in siblings:
            reset_selection()
            n.setSelected(True)
            nuke.nodeCopy("%clipboard%")
            reset_selection()
            nuke.nodePaste("%clipboard%")
            new_node = nuke.selectedNodes()[0]
            x_init = int(new_node.knob('x_init').getValue())
            y_init = int(new_node.knob('y_init').getValue())
            new_node.setXYpos(x_init, y_init)
            if isinstance(new_node, nuke.BackdropNode):
                w_init = new_node.knob('w_init').getValue()
                h_init = new_node.knob('h_init').getValue()
                new_node.knob('bdwidth').setValue(w_init)
                new_node.knob('bdheight').setValue(h_init)
                refresh_node(n)

            if 'id_rep' in n.knobs().keys():
                n.removeKnob(n.knob('id_rep'))
            copies[n.name()] = new_node
        return copies

    def fix_z_order(self):
        # fix the problem of Z-order
        orders_bd = []
        nodes_loaded = self.data['last_loaded']
        for n in nodes_loaded:
            if isinstance(n, nuke.BackdropNode):
                orders_bd.append(n.knob("z_order").getValue())
        
        if orders_bd:

            min_order = min(orders_bd)
            siblings = self.data["siblings"]

            orders_sib = []
            for s in siblings:
                n = nuke.toNode(s)
                if isinstance(n, nuke.BackdropNode):
                    orders_sib.append(n.knob("z_order").getValue())
            if orders_sib:
                max_order = max(orders_sib)
                for n in nodes_loaded:
                    if isinstance(n, nuke.BackdropNode):
                        z_order = n.knob("z_order").getValue()
                        n.knob("z_order").setValue(
                            z_order + max_order - min_order + 1)

    def update_nodes(self, nodes):
        # Adjust backdrop dimensions and node positions by getting
        # the difference of dimensions between what was
        node = self.data['node']
        width_ph = node.screenWidth()
        height_ph = node.screenHeight()
        nodes_loaded = self.data['last_loaded']
        min_x, min_y, max_x, max_y = get_extremes(nodes_loaded)

        # difference of heights
        diff_y = max_y - min_y - height_ph
        # difference of widths
        diff_x = max_x - min_x - width_ph

        if diff_y > 0 or diff_x > 0:
            for n in nodes:
                refresh_node(n)
                if n != node and n not in nodes_loaded:
                    width = n.screenWidth()
                    height = n.screenHeight()
                    if not isinstance(n, nuke.BackdropNode)\
                            or isinstance(n, nuke.BackdropNode)\
                            and node not in n.getNodes():
                        if n.xpos() + width >= node.xpos() + width_ph:

                            n.setXpos(n.xpos() + diff_x)

                        if n.ypos() + height >= node.ypos() + height_ph:
                            n.setYpos(n.ypos() + diff_y)

                    else:
                        width = n.knob("bdwidth").getValue()
                        height = n.knob("bdheight").getValue()
                        n.knob("bdwidth").setValue(width + diff_x)
                        n.knob("bdheight").setValue(height + diff_y)

                    refresh_node(n)

    def imprint_inits(self):
        for n in nuke.allNodes():
            refresh_node(n)
            imprint(n, {'x_init': n.xpos(), 'y_init': n.ypos()})
            n.knob('x_init').setVisible(False)
            n.knob('y_init').setVisible(False)
            width = n.screenWidth()
            height = n.screenHeight()
            if 'bdwidth' in n.knobs().keys():
                imprint(n, {'w_init': width, 'h_init': height})
                n.knob('w_init').setVisible(False)
                n.knob('h_init').setVisible(False)

    def imprint_siblings(self):
        nodes_loaded = self.data['last_loaded']
        d = {"id_rep": str(self.data['_id'])}

        for n in nodes_loaded:
            if "builder_type" in n.knobs().keys()\
                    and ('is_placeholder' not in n.knobs().keys()
                         or 'is_placeholder' in n.knobs().keys()
                         and n.knob('is_placeholder').value()):
                
                siblingss = list(set(nodes_loaded) - set([n]))
                siblings_name = []
                for s in siblingss:
                    siblings_name.append(s.name())
                siblings = {"siblings": siblings_name}
                imprint(n, siblings)

            elif 'builder_type' not in n.knobs().keys():
                # save the id of representation for all imported nodes
                imprint(n, d)
                # n.knob('id_rep').setVisible(False)
                refresh_node(n)
    
    def set_loaded_connections(self):
        node = self.data['node']
        input, output = get_io(self.data['last_loaded'])
        for n in node.dependent():
            for i in range(n.inputs()):
                if n.input(i) == node:
                    n.setInput(i, output)

        for n in node.dependencies():
            for i in range(node.inputs()):
                if node.input(i) == n:
                    input.setInput(0, n)

    def set_copies_connections(self, copies):
        input, output = get_io(self.data['last_loaded'])
        siblings = get_nodes_from_names(self.data['siblings'])
        inp, out = get_io(siblings)
        inp_copy, out_copy = (copies[inp.name()], copies[out.name()])

        for node_init in siblings:
            if node_init != out:
                node_copy = copies[node_init.name()]
                for n in node_init.dependent():
                    for i in range(n.inputs()):
                        if n.input(i) == node_init:
                            if n in siblings:
                                copies[n.name()].setInput(i, node_copy)
                            else:
                                input.setInput(0, node_copy)

                for n in node_init.dependencies():
                    for i in range(node_init.inputs()):
                        if node_init.input(i) == n:
                            if node_init == inp:
                                inp_copy.setInput(i, n)
                            elif n in siblings:
                                node_copy.setInput(i, copies[n.name()])
                            else:
                                node_copy.setInput(i, output)

        inp.setInput(0, out_copy)

    def clean(self):

        # deselect all selected nodes
        node = self.data['node']

        # getting the latest nodes added
        nodes_init = self.data["nodes_init"]
        nodes_loaded = list(set(nuke.allNodes()) - set(nodes_init))
        if not nodes_loaded:
            self.data['delete'] = False
            return

        self.data['last_loaded'] = nodes_loaded
        reset_selection()
        refresh_nodes(nodes_loaded)
       
        # positioning of the loaded nodes
        min_x, min_y, _, _ = get_extremes(nodes_loaded)
        
        for n in nodes_loaded:
            xpos = (n.xpos() - min_x) + node.xpos()
            ypos = (n.ypos() - min_y) + node.ypos()
            n.setXYpos(xpos, ypos)
        refresh_nodes(nodes_loaded)

        self.fix_z_order()
        self.imprint_siblings()

        if self.data['nb_children'] == 0:
            self.imprint_inits()
            self.update_nodes(nuke.allNodes())

            # update dependecies and dependent
            self.set_loaded_connections()

        elif self.data['siblings']:
            siblings = get_nodes_from_names(self.data['siblings'])
            refresh_nodes(siblings)

            copies = self.create_sib_copies()
            new_nodes = list(copies.values())
            self.update_nodes(new_nodes)
            node.removeKnob(node.knob('siblings'))
            new_nodes_name = get_names_from_nodes(new_nodes)
            imprint(node, {'siblings': new_nodes_name})
            self.set_copies_connections(copies)

            min_xx, min_yy, max_xx, max_yy = get_extremes(new_nodes)
            minX, _, maxX, _ = get_extremes(siblings)
            offset_y = max_yy - min_yy + 20
            offset_x = abs(max_xx - min_xx - maxX + minX)
            
            for n in nuke.allNodes():

                if (n.ypos() >= min_yy
                        and n not in nodes_loaded + new_nodes
                        and n != node):
                    n.setYpos(n.ypos() + offset_y)

                if isinstance(n, nuke.BackdropNode)\
                        and set(new_nodes) <= set(n.getNodes()):
                    height = n.knob("bdheight").getValue()
                    n.knob("bdheight").setValue(height + offset_y)
                    width = n.knob("bdwidth").getValue()
                    n.knob("bdwidth").setValue(width + offset_x)

            new_siblings = []
            for n in new_nodes:
                new_siblings.append(n.name())
            self.data['siblings'] = new_siblings

        else:
            xpointer, ypointer = find_free_space_to_paste_nodes(
                nodes_loaded, direction="bottom", offset=200
            )
            n = nuke.createNode("NoOp")
            reset_selection()
            nuke.delete(n)
            for n in nodes_loaded:
                xpos = (n.xpos() - min_x) + xpointer
                ypos = (n.ypos() - min_y) + ypointer
                n.setXYpos(xpos, ypos)

        self.data['nb_children'] += 1
        reset_selection()
        # go back to root group
        nuke.root().begin()

    def convert_to_db_filters(self, current_asset, linked_asset):
        if self.data['builder_type'] == "context_asset":
            return [{
                "type": "representation",
                "context.asset": {
                    "$eq": current_asset, "$regex": self.data['asset']},
                "context.subset": {"$regex": self.data['subset']},
                "context.hierarchy": {"$regex": self.data['hierarchy']},
                "context.representation": self.data['representation'],
                "context.family": self.data['family'],
            }]

        elif self.data['builder_type'] == "linked_asset":
            return [{
                "type": "representation",
                "context.asset": {
                    "$eq": asset_name, "$regex": self.data['asset']},
                "context.subset": {"$regex": self.data['subset']},
                "context.hierarchy": {"$regex": self.data['hierarchy']},
                "context.representation": self.data['representation'],
                "context.family": self.data['family'],
            } for asset_name in linked_asset]

        else:
            return [{
                "type": "representation",
                "context.asset": {"$regex": self.data['asset']},
                "context.subset": {"$regex": self.data['subset']},
                "context.hierarchy": {"$regex": self.data['hierarchy']},
                "context.representation": self.data['representation'],
                "context.family": self.data['family'],
            }]

    def err_message(self):
        return (
            "Error while trying to load a representation.\n"
            "Either the subset wasn't published or the template is malformed."
            "\n\n"
            "Builder was looking for:\n{attributes}".format(
                attributes="\n".join([
                    "{}: {}".format(key.title(), value)
                    for key, value in self.data.items()]
                )
            )
        )
