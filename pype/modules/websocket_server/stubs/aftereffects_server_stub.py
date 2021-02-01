from pype.modules.websocket_server import WebSocketServer
"""
    Stub handling connection from server to client.
    Used anywhere solution is calling client methods.
"""
import json
import attr

import logging
log = logging.getLogger(__name__)


@attr.s
class AEItem(object):
    """
        Object denoting Item in AE. Each item is created in AE by any Loader,
        but contains same fields, which are being used in later processing.
    """
    # metadata
    id = attr.ib()  # id created by AE, could be used for querying
    name = attr.ib()  # name of item
    item_type = attr.ib(default=None)  # item type (footage, folder, comp)
    # all imported elements, single for
    # regular image, array for Backgrounds
    members = attr.ib(factory=list)
    workAreaStart = attr.ib(default=None)
    workAreaDuration = attr.ib(default=None)
    frameRate = attr.ib(default=None)
    file_name = attr.ib(default=None)


class AfterEffectsServerStub():
    """
        Stub for calling function on client (Photoshop js) side.
        Expects that client is already connected (started when avalon menu
        is opened).
        'self.websocketserver.call' is used as async wrapper
    """

    def __init__(self):
        self.websocketserver = WebSocketServer.get_instance()
        self.client = self.websocketserver.get_client()

    def open(self, path):
        """
            Open file located at 'path' (local).
        Args:
            path(string): file path locally
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.open', path=path)
                                  )

    def get_metadata(self):
        """
            Get complete stored JSON with metadata from AE.Metadata.Label
            field.

            It contains containers loaded by any Loader OR instances creted
            by Creator.

        Returns:
            (dict)
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_metadata')
                                        )
        try:
            metadata = json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Unparsable metadata {}".format(res))
        return metadata or []

    def read(self, item, layers_meta=None):
        """
            Parses item metadata from Label field of active document.
            Used as filter to pick metadata for specific 'item' only.

        Args:
            item (AEItem): pulled info from AE
            layers_meta (dict): full list from Headline
                (load and inject for better performance in loops)
        Returns:
            (dict):
        """
        if layers_meta is None:
            layers_meta = self.get_metadata()

        for item_meta in layers_meta:
            if 'container' in item_meta.get('id') and \
                    str(item.id) == str(item_meta.get('members')[0]):
                return item_meta

        log.debug("Couldn't find layer metadata")

    def imprint(self, item, data, all_items=None, items_meta=None):
        """
            Save item metadata to Label field of metadata of active document
        Args:
            item (AEItem):
            data(string): json representation for single layer
            all_items (list of item): for performance, could be
                injected for usage in loop, if not, single call will be
                triggered
            items_meta(string): json representation from Headline
                           (for performance - provide only if imprint is in
                           loop - value should be same)
        Returns: None
        """
        if not items_meta:
            items_meta = self.get_metadata()

        result_meta = []
        # fix existing
        is_new = True

        for item_meta in items_meta:
            if item_meta.get('members') \
                    and str(item.id) == str(item_meta.get('members')[0]):
                is_new = False
                if data:
                    item_meta.update(data)
                    result_meta.append(item_meta)
            else:
                result_meta.append(item_meta)

        if is_new:
            result_meta.append(data)

        # Ensure only valid ids are stored.
        if not all_items:
            # loaders create FootageItem now
            all_items = self.get_items(comps=True,
                                       folders=True,
                                       footages=True)
        item_ids = [int(item.id) for item in all_items]
        cleaned_data = []
        for meta in result_meta:
            # for creation of instance OR loaded container
            if 'instance' in meta.get('id') or \
                    int(meta.get('members')[0]) in item_ids:
                cleaned_data.append(meta)

        payload = json.dumps(cleaned_data, indent=4)

        self.websocketserver.call(self.client.call
                                  ('AfterEffects.imprint', payload=payload))

    def get_active_document_full_name(self):
        """
            Returns just a name of active document via ws call
        Returns(string): file name
        """
        res = self.websocketserver.call(self.client.call(
              'AfterEffects.get_active_document_full_name'))

        return res

    def get_active_document_name(self):
        """
            Returns just a name of active document via ws call
        Returns(string): file name
        """
        res = self.websocketserver.call(self.client.call(
              'AfterEffects.get_active_document_name'))

        return res

    def get_items(self, comps, folders=False, footages=False):
        """
            Get all items from Project panel according to arguments.
            There are multiple different types:
                CompItem (could have multiple layers - source for Creator,
                    will be rendered)
                FolderItem (collection type, currently used for Background
                    loading)
                FootageItem (imported file - created by Loader)
        Args:
            comps (bool): return CompItems
            folders (bool): return FolderItem
            footages (bool: return FootageItem

        Returns:
            (list) of namedtuples
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_items',
                                         comps=comps,
                                         folders=folders,
                                         footages=footages)
                                        )
        return self._to_records(res)

    def get_selected_items(self, comps, folders=False, footages=False):
        """
            Same as get_items but using selected items only
        Args:
            comps (bool): return CompItems
            folders (bool): return FolderItem
            footages (bool: return FootageItem

        Returns:
            (list) of namedtuples

        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_selected_items',
                                         comps=comps,
                                         folders=folders,
                                         footages=footages)
                                        )
        return self._to_records(res)

    def import_file(self, path, item_name, import_options=None):
        """
            Imports file as a FootageItem. Used in Loader
        Args:
            path (string): absolute path for asset file
            item_name (string): label for created FootageItem
            import_options (dict): different files (img vs psd) need different
                config

        """
        res = self.websocketserver.call(self.client.call(
                'AfterEffects.import_file',
                path=path,
                item_name=item_name,
                import_options=import_options)
              )
        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Couldn't import {} file".format(path))

    def replace_item(self, item, path, item_name):
        """ Replace FootageItem with new file

            Args:
                item (dict):
                path (string):absolute path
                item_name (string): label on item in Project list

        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.replace_item',
                                   item_id=item.id,
                                   path=path, item_name=item_name))

    def rename_item(self, item, item_name):
        """ Replace item with item_name

            Args:
                item (dict):
                item_name (string): label on item in Project list

        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.rename_item',
                                   item_id=item.id,
                                   item_name=item_name))

    def delete_item(self, item_id):
        """ Deletes *Item in a file
            Args:
                item_id (int):

        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.delete_item',
                                   item_id=item_id
                                   ))

    def is_saved(self):
        # TODO
        return True

    def set_label_color(self, item_id, color_idx):
        """
            Used for highlight additional information in Project panel.
            Green color is loaded asset, blue is created asset
        Args:
            item_id (int):
            color_idx (int): 0-16 Label colors from AE Project view
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.set_label_color',
                                   item_id=item_id,
                                   color_idx=color_idx
                                   ))

    def get_work_area(self, item_id):
        """ Get work are information for render purposes
            Args:
                item_id (int):

            Returns:
                (namedtuple)

        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_work_area',
                                         item_id=item_id
                                         ))

        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Couldn't get work area")

    def set_work_area(self, item, start, duration, frame_rate):
        """
            Set work area to predefined values (from Ftrack).
            Work area directs what gets rendered.
            Beware of rounding, AE expects seconds, not frames directly.

        Args:
            item (dict):
            start (float): workAreaStart in seconds
            duration (float): in seconds
            frame_rate (float): frames in seconds
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.set_work_area',
                                   item_id=item.id,
                                   start=start,
                                   duration=duration,
                                   frame_rate=frame_rate
                                   ))

    def save(self):
        """
            Saves active document
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.save'))

    def saveAs(self, project_path, as_copy):
        """
            Saves active project to aep (copy) or png or jpg
        Args:
            project_path(string): full local path
            as_copy: <boolean>
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.saveAs',
                                   image_path=project_path,
                                   as_copy=as_copy))

    def get_render_info(self):
        """ Get render queue info for render purposes

            Returns:
                (namedtuple): with 'file_name' field
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_render_info'))

        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Render queue needs to have file extension in 'Output to'")

    def get_audio_url(self, item_id):
        """ Get audio layer absolute url for comp

            Args:
                item_id (int): composition id
            Returns:
                (str): absolute path url
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_audio_url',
                                         item_id=item_id))

        return res

    def close(self):
        self.client.close()

    def import_background(self, comp_id, comp_name, files):
        """
            Imports backgrounds images to existing or new composition.

            If comp_id is not provided, new composition is created, basic
            values (width, heights, frameRatio) takes from first imported
            image.

            All images from background json are imported as a FootageItem and
            separate layer is created for each of them under composition.

            Order of imported 'files' is important.

            Args:
                comp_id (int): id of existing composition (null if new)
                comp_name (str): used when new composition
                files (list): list of absolute paths to import and
                add as layers

            Returns:
                (AEItem): object with id of created folder, all imported images
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.import_background',
                                         comp_id=comp_id,
                                         comp_name=comp_name,
                                         files=files))

        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Import background failed.")

    def reload_background(self, comp_id, comp_name, files):
        """
            Reloads backgrounds images to existing composition.

            It actually deletes complete folder with imported images and
            created composition for safety.

            Args:
                comp_id (int): id of existing composition to be overwritten
                comp_name (str): new name of composition (could be same as old
                    if version up only)
                files (list): list of absolute paths to import and
                    add as layers
            Returns:
                (AEItem): object with id of created folder, all imported images
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.reload_background',
                                         comp_id=comp_id,
                                         comp_name=comp_name,
                                         files=files))

        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Reload of background failed.")

    def add_item_as_layer(self, comp_id, item_id):
        """
            Adds already imported FootageItem ('item_id') as a new
            layer to composition ('comp_id').

            Args:
                comp_id (int): id of target composition
                item_id (int): FootageItem.id
                comp already found previously
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.add_item_as_layer',
                                         comp_id=comp_id,
                                         item_id=item_id))

        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Adding new layer failed.")

    def _to_records(self, res):
        """
            Converts string json representation into list of AEItem
            dot notation access to work.
        Returns: <list of AEItem>
            res(string): - json representation
        """
        if not res:
            return []

        try:
            layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Received broken JSON {}".format(res))
        if not layers_data:
            return []

        ret = []
        # convert to AEItem to use dot donation
        if isinstance(layers_data, dict):
            layers_data = [layers_data]
        for d in layers_data:
            # currently implemented and expected fields
            item = AEItem(d.get('id'),
                          d.get('name'),
                          d.get('type'),
                          d.get('members'),
                          d.get('workAreaStart'),
                          d.get('workAreaDuration'),
                          d.get('frameRate'),
                          d.get('file_name'))

            ret.append(item)
        return ret
