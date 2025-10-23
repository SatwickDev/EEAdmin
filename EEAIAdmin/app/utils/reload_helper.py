import os
import json
import logging
from app.utils.json_loader import reload_json_folder  # import the reusable loader

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
