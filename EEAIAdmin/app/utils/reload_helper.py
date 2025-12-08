import os
import json
import logging
from datetime import datetime
from typing import Optional
import threading
import time

from app.utils.json_loader import (
    reload_json_folder,
    reload_json_and_xml_folder,
    reload_single_file,
)  # import the reusable loader

logger = logging.getLogger(__name__)

# Module-level lock to avoid concurrent reloads within the same process
_reload_lock = threading.Lock()
# Minimum seconds between reloads performed by this process
_RELOAD_DEBOUNCE_SECONDS = 2


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
    """If `app.backend.Smart_Document_Capture.Document_Classification.document_classifier` is loaded, call its
    `reload_all_document_classifier_instances()` helper on the existing
    module object (so live instances registered in the old module are
    updated). Returns the number of reloaded instances, or None if the
    module isn't importable or helper missing.
    """
    try:
        import importlib
        import sys

        mod_name = 'app.backend.Smart_Document_Capture.Document_Classification.document_classifier'
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
    Reload JSON/YAML/XML files in the root `data` folder and update the
    global `app.json_data_cache` in-place so other modules holding
    references see changes immediately.
    """
    try:
        import importlib

        # Resolve to the repository-level data folder (parent of app package)
        app_pkg = importlib.import_module('app')
        app_pkg_dir = os.path.dirname(os.path.abspath(app_pkg.__file__))
        repo_root = os.path.dirname(app_pkg_dir)  # go up one level from app/
        data_folder = os.path.join(repo_root, 'data')
        data_folder = os.path.abspath(data_folder)
        logger.info(f"✅ JSON folder path resolved to: {data_folder}")

        # Ensure the global cache exists on the app package
        if not hasattr(app_pkg, 'json_data_cache'):
            logger.info("Creating `json_data_cache` on app module")
            setattr(app_pkg, 'json_data_cache', {})

        json_data_cache = app_pkg.json_data_cache

        # Prevent concurrent reloads and very-frequent repeated reloads
        try:
            last_reload = getattr(app_pkg, '_last_json_reload', 0)
        except Exception:
            last_reload = 0

        # If last reload was very recent, skip reloading to avoid thrashing
        now = time.time()
        if last_reload and (now - last_reload) < _RELOAD_DEBOUNCE_SECONDS:
            logger.debug(f'⏱️ Skipping reload_all_jsons: debounced ({now - last_reload:.2f}s < {_RELOAD_DEBOUNCE_SECONDS}s)')
            return False

        # Check if ANY file in the data folder has changed since last_reload
        # This is a real check—regardless of marker mtime
        any_file_changed = False
        try:
            if not json_data_cache:  # First load, no real timestamp yet
                any_file_changed = True
            elif last_reload > 0:
                # Check actual file mtimes
                for root, _, files in os.walk(data_folder):
                    for filename in files:
                        if not filename.endswith(('.json', '.yaml', '.yml', '.xml')):
                            continue
                        full_path = os.path.join(root, filename)
                        try:
                            mtime = os.path.getmtime(full_path)
                            if mtime > last_reload:
                                logger.debug(f"📝 File changed: {filename} (mtime={mtime}, last_reload={last_reload})")
                                any_file_changed = True
                                break
                        except Exception:
                            continue
                    if any_file_changed:
                        break
        except Exception as e:
            logger.debug(f"Error checking file mtimes: {e}")

        if not any_file_changed:
            logger.debug('✅ No files changed since last reload')
            return False

        # Acquire process-wide lock so only one thread performs the reload at a time
        acquired = _reload_lock.acquire(timeout=10)
        if not acquired:
            logger.warning('Another thread/process is performing reload_all_jsons; skipping')
            return False

        try:
            # If this is the first time (cache empty) or last_reload==0, perform a full reload
            perform_full_reload = not bool(json_data_cache)

            if perform_full_reload:
                new_data = reload_json_and_xml_folder(data_folder)
            else:
                # Find files changed since last_reload and reload only them
                changed_files = []
                for root, _, files in os.walk(data_folder):
                    for filename in files:
                        if not filename.endswith(('.json', '.yaml', '.yml', '.xml')):
                            continue
                        full_path = os.path.join(root, filename)
                        try:
                            mtime = os.path.getmtime(full_path)
                        except Exception:
                            continue
                        if mtime and (not last_reload or mtime > last_reload):
                            changed_files.append(full_path)

                if not changed_files:
                    logger.debug('No changed files detected for reload_all_jsons')
                    return False

                # Reload each changed file and update cache
                for fp in changed_files:
                    key, content = reload_single_file(fp, data_folder)
                    if key is None:
                        continue
                    try:
                        json_data_cache[key] = content
                    except Exception:
                        logger.exception(f'Failed to update cache for {key}')

                # Remove keys that no longer exist on disk
                current_keys = set()
                for root, _, files in os.walk(data_folder):
                    for filename in files:
                        if not filename.endswith(('.json', '.yaml', '.yml', '.xml')):
                            continue
                        rel = os.path.relpath(os.path.join(root, filename), data_folder)
                        k = os.path.splitext(rel.replace('\\', '/'))[0]
                        current_keys.add(k)

                # keys to delete from cache
                keys_to_delete = [k for k in json_data_cache.keys() if k not in current_keys and not k.startswith('_')]
                for k in keys_to_delete:
                    try:
                        del json_data_cache[k]
                    except Exception:
                        logger.debug(f'Failed to delete stale key from cache: {k}')

                # set new_data as the updated cache for logging
                new_data = dict(json_data_cache)

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

            logger.info(f"✅ JSON folder reloaded successfully from {data_folder}; {len(new_data)} entries updated. Cache keys: {list(json_data_cache.keys())[:10]}...")

            # Touch a marker file so other processes can detect the reload
            _touch_reload_marker(data_folder)

            # Record the successful reload time on the app package so subsequent calls are debounced
            try:
                app_pkg._last_json_reload = time.time()
            except Exception:
                logger.debug('Could not set app_pkg._last_json_reload')

            # Reload any live DocumentClassifier instances (they may be created in multiple places)
            reloaded = _reload_document_classifier_instances()
            if reloaded is None:
                logger.debug("No DocumentClassifier helper available to reload instances")
            else:
                logger.info(f"✅ Reloaded {reloaded} DocumentClassifier instance(s) after JSON reload")

            return True
        finally:
            try:
                _reload_lock.release()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"⚠️ Failed to reload JSONs: {e}")
        return False



