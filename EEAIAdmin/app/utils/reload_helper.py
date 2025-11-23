import os
import json
import logging
from datetime import datetime
from typing import Optional

from app.utils.json_loader import reload_json_folder, reload_json_and_xml_folder  # import the reusable loader

logger = logging.getLogger(__name__)


def _touch_reload_marker(data_folder: str) -> None:
    try:
        marker = os.path.join(data_folder, '.last_reload')
        with open(marker, 'w', encoding='utf-8') as mf:
            mf.write(datetime.utcnow().isoformat() + 'Z')
        try:
            os.utime(marker, None)
        except Exception:
            pass
    except Exception:
        logger.debug("Failed to write .last_reload marker")


def _reload_document_classifier_instances() -> Optional[int]:
    """If `app.utils.document_classifier` is loaded, call its
    `reload_all_document_classifier_instances()` helper on the existing
    module object (so live instances registered in the old module are
    updated). Returns the number of reloaded instances, or None if the
    module isn't importable or helper missing.
    """
    try:
        import importlib
        import sys

        mod_name = 'app.utils.document_classifier'
        existing_mod = sys.modules.get(mod_name)

        if existing_mod and hasattr(existing_mod, 'reload_all_document_classifier_instances'):
            try:
                count = existing_mod.reload_all_document_classifier_instances()
                return int(count or 0)
            except Exception:
                logger.exception('Failed to call reload_all_document_classifier_instances on existing module')
                return 0

        # If not loaded, try importing the module and call the helper if present
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, 'reload_all_document_classifier_instances'):
                try:
                    return int(mod.reload_all_document_classifier_instances() or 0)
                except Exception:
                    logger.exception('Failed to call reload_all_document_classifier_instances on imported module')
                    return 0
        except Exception:
            logger.debug('document_classifier module could not be imported')

        # Fallback: if the Flask app attached a singleton `document_classifier`, call its reload
        try:
            from flask import current_app
            dc = getattr(current_app, 'document_classifier', None)
            if dc and hasattr(dc, 'reload_from_disk'):
                try:
                    dc.reload_from_disk()
                    logger.info('✅ Reloaded app.document_classifier singleton via fallback')
                    return 1
                except Exception:
                    logger.exception('Failed to reload current_app.document_classifier')
                    return 0
        except Exception:
            # running outside a flask request/context or current_app unavailable
            logger.debug('current_app.document_classifier fallback not available')
            return None

    except Exception:
        logger.debug('document classifier reload helper execution failed')
        return None


def reload_all_jsons() -> bool:
    """
    Reload JSON/YAML/XML files in the `app/data` folder and update the
    global `app.json_data_cache` in-place so other modules holding
    references see changes immediately.
    """
    try:
        import importlib

        # Prefer the application's own `app/data` folder so reloads match runtime loads
        app_pkg = importlib.import_module('app')
        app_pkg_dir = os.path.dirname(os.path.abspath(app_pkg.__file__))
        data_folder = os.path.join(app_pkg_dir, 'data')
        data_folder = os.path.abspath(data_folder)
        logger.info(f"✅ JSON folder path resolved to: {data_folder}")

        # Ensure the global cache exists on the app package
        if not hasattr(app_pkg, 'json_data_cache'):
            logger.info("Creating `json_data_cache` on app module")
            setattr(app_pkg, 'json_data_cache', {})

        json_data_cache = app_pkg.json_data_cache

        # Reload JSONs (and YAML/XML if present) using the shared loader
        new_data = reload_json_and_xml_folder(data_folder)

        if not isinstance(new_data, dict):
            logger.error(f"Unexpected data returned from loader: {type(new_data)}")
            return False

        # Update cache in-place so other modules holding references see changes immediately
        try:
            json_data_cache.clear()
            json_data_cache.update(new_data)
            # record a timestamp so it's easy to verify which process updated the cache
            try:
                json_data_cache['_last_reloaded'] = datetime.utcnow().isoformat() + 'Z'
            except Exception:
                pass
        except Exception as e:
            logger.exception(f"Failed to update json_data_cache in-place: {e}")
            return False

        logger.info(f"✅ JSON folder reloaded successfully from {data_folder}; {len(new_data)} entries updated")

        # Touch a marker file so other processes can detect the reload
        _touch_reload_marker(data_folder)

        # Reload any live DocumentClassifier instances (they may be created in multiple places)
        reloaded = _reload_document_classifier_instances()
        if reloaded is None:
            logger.debug("No DocumentClassifier helper available to reload instances")
        else:
            logger.info(f"✅ Reloaded {reloaded} DocumentClassifier instance(s) after JSON reload")

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
        import importlib
        if not folder_path:
            # prefer the app package data directory when no path provided
            app_pkg = importlib.import_module('app')
            app_pkg_dir = os.path.dirname(os.path.abspath(app_pkg.__file__))
            folder_path = os.path.join(app_pkg_dir, 'data')
        folder_path = os.path.abspath(folder_path)

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

        # Replace contents of cache in-place so references remain valid
        app_pkg.app_data_cache.clear()
        try:
            app_pkg.app_data_cache.update(new_data)
            try:
                app_pkg.app_data_cache['_last_reloaded'] = datetime.utcnow().isoformat() + 'Z'
            except Exception:
                pass
        except Exception as e:
            logger.exception(f"Failed to update app_data_cache with new data: {e}")
            return False

        # Touch marker and reload any live DocumentClassifier instances
        _touch_reload_marker(folder_path)
        reloaded = _reload_document_classifier_instances()
        if reloaded is None:
            logger.debug("No DocumentClassifier helper available to reload instances")
        else:
            logger.info(f"✅ Reloaded {reloaded} DocumentClassifier instance(s) after app data reload")

        logger.info(f"✅ App data reloaded successfully from {folder_path}")
        return True

    except Exception as e:
        logger.exception(f"⚠️ Failed to reload app data: {e}")
        return False
