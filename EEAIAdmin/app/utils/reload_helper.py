import os
import json
import logging
from app.utils.json_loader import reload_json_folder, reload_json_and_xml_folder  # import the reusable loader

logger = logging.getLogger(__name__)

def reload_all_jsons():
    """
    Reload all JSON files in the data folder and update the global cache.
    """
    try:
        # Folder path where your JSON files live
        data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
        logger.info(f"✅ JSON folder path:: {data_folder}")

        # Import the global cache (make sure it’s defined in app/__init__.py or main.py)
        from app import json_data_cache

        # Reload JSONs
        new_data = reload_json_folder(data_folder)
        # Clear old cache and update with new data
        json_data_cache.clear()
        json_data_cache.update(new_data)

        logger.info(f"✅ JSON folder reloaded successfully from {data_folder}")
        return True

    except Exception as e:
        logger.warning(f"⚠️ Failed to reload JSONs: {e}")
        return False


def reload_app_data(folder_path: str = None):
    """
    Reload JSON, YAML and XML files from the `app/data` folder and update `app.app_data_cache`.

    If `folder_path` is provided it will be used; otherwise defaults to the repository `app/data` directory.
    """
    try:
        if not folder_path:
            folder_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

        # Validate folder_path type early to provide clearer errors
        if not isinstance(folder_path, (str, bytes, os.PathLike)):
            # Handle common mistake where an XML Element or other object is passed
            try:
                from xml.etree.ElementTree import Element
                if isinstance(folder_path, Element):
                    logger.error("Provided folder_path is an XML Element object — expected a filesystem path string.")
                else:
                    logger.error(f"Provided folder_path has unexpected type: {type(folder_path)} — expected str or PathLike.")
            except Exception:
                logger.error(f"Provided folder_path has unexpected type: {type(folder_path)} — expected str or PathLike.")
            return False

        logger.info(f"✅ App data folder path:: {folder_path}")

        # Import or create the global app_data_cache on the app package
        import importlib
        app_pkg = importlib.import_module('app')

        if not hasattr(app_pkg, 'app_data_cache'):
            logger.info("Creating `app_data_cache` on app module")
            setattr(app_pkg, 'app_data_cache', {})

        # Reload data (JSON/YAML/XML)
        try:
            new_data = reload_json_and_xml_folder(folder_path)
        except Exception as e:
            logger.exception(f"Failed while loading files from {folder_path}: {e}")
            return False

        # Sanity check the returned data
        if not isinstance(new_data, dict):
            logger.error(f"reload_json_and_xml_folder returned unexpected type: {type(new_data)}")
            return False

        # Replace contents of cache
        app_pkg.app_data_cache.clear()
        try:
            app_pkg.app_data_cache.update(new_data)
        except Exception as e:
            logger.exception(f"Failed to update app_data_cache with new data: {e}")
            return False

        logger.info(f"✅ App data reloaded successfully from {folder_path}")
        return True

    except Exception as e:
        logger.exception(f"⚠️ Failed to reload app data: {e}")
        return False
