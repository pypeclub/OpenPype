from pype.api import get_system_settings


def get_ftrack_settings():
    return get_system_settings()["modules"]["ftrack"]


def get_ftrack_url_from_settings():
    return get_ftrack_settings()["ftrack_server"]


def get_ftrack_event_mongo_info():
    ftrack_settings = get_ftrack_settings()
    database_name = ftrack_settings["mongo_database_name"]
    collection_name = ftrack_settings["mongo_collection_name"]
    return database_name, collection_name
