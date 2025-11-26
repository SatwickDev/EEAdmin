import os
import json
import yaml
import logging
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


def reload_json_folder(folder_path: str):
    """
    Recursively load all JSON files in the folder and its subfolders.
    """
    data_cache = {}

    folder_path = os.fspath(folder_path)  # ✅ ensures it's a str/path
    logger.debug(f"reload_json_folder called with folder_path (type={type(folder_path)}): {folder_path}")
    for root, _, files in os.walk(folder_path):
        # Diagnostic: ensure root is a string path; if not, log and skip to avoid TypeError
        if not isinstance(root, (str, bytes, os.PathLike)):
            logger.error(f"Unexpected root type from os.walk: {type(root)}; value: {repr(root)}. Skipping this iteration.")
            continue

        for filename in files:
            full_path = os.path.join(root, filename)
            # ✅ Convert to string explicitly for type checking
            relative_path = os.path.relpath(str(full_path), str(folder_path))
            key = relative_path.replace("\\", "/")
            # normalize key without extension
            key = os.path.splitext(key)[0]

            if filename.endswith(".json"):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data_cache[key] = json.load(f)
                except Exception as e:
                    logger.exception(f"⚠️ Could not load JSON {relative_path}: {e}")

            # --- Load YAML / YML files ---
            elif filename.endswith(('.yaml', '.yml')):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data_cache[key] = yaml.safe_load(f)
                except Exception as e:
                    logger.exception(f"⚠️ Error loading YAML {relative_path}: {e}")

            # --- XML files ---
            elif filename.endswith('.xml'):
                try:
                    # Defensive: read file content and parse string to avoid path-based issues
                    if not isinstance(full_path, (str, bytes, os.PathLike)):
                        logger.error(f"Invalid full_path type for XML parse: {type(full_path)} (file: {relative_path})")
                        continue
                    with open(full_path, 'r', encoding='utf-8') as xf:
                        xml_text = xf.read()
                    # Parse from string so ET doesn't receive unexpected objects
                    xml_root = ET.fromstring(xml_text)
                    data_cache[key] = _etree_to_dict(xml_root)
                except Exception as e:
                    logger.exception(f"⚠️ Error loading/parsing XML {relative_path} from {full_path}: {e}")
        # for file, content in data_cache.items():
        #     print(f"{file} loaded, keys: {list(content.keys())}")

    return data_cache


def reload_json_and_xml_folder(folder_path: str):
    """
    Extended loader that explicitly handles JSON, YAML and XML files.
    Kept as a separate function for clarity and backward compatibility.
    """
    return reload_json_folder(folder_path)


def reload_single_file(full_path: str, base_folder: str):
    """
    Load a single JSON/YAML/XML file and return a tuple `(key, content)`
    where `key` matches the same normalized key used by
    `reload_json_folder` (relative path without extension, forward slashes).
    Returns `(None, None)` on error or if file type is unsupported.
    """
    try:
        full_path = os.path.abspath(os.fspath(full_path))
        base_folder = os.path.abspath(os.fspath(base_folder))
    except Exception as e:
        logger.exception(f"Invalid path types for reload_single_file: {e}")
        return None, None

    if not os.path.isfile(full_path):
        logger.debug(f"reload_single_file: path not a file: {full_path}")
        return None, None

    rel = os.path.relpath(full_path, base_folder)
    key = rel.replace("\\", "/")
    key = os.path.splitext(key)[0]

    filename = os.path.basename(full_path)
    try:
        if filename.endswith('.json'):
            with open(full_path, 'r', encoding='utf-8') as f:
                return key, json.load(f)

        if filename.endswith(('.yaml', '.yml')):
            with open(full_path, 'r', encoding='utf-8') as f:
                return key, yaml.safe_load(f)

        if filename.endswith('.xml'):
            with open(full_path, 'r', encoding='utf-8') as xf:
                xml_text = xf.read()
            xml_root = ET.fromstring(xml_text)
            return key, _etree_to_dict(xml_root)

        # unsupported file type
        logger.debug(f"reload_single_file: unsupported extension for {full_path}")
        return None, None
    except Exception as e:
        logger.exception(f"Error loading single file {full_path}: {e}")
        return None, None


def _etree_to_dict(elem):
    """Convert an ElementTree element into a nested dict.

    Simple conversion: element tag -> dict with attributes, text and children.
    """
    d = {}
    # include attributes
    if elem.attrib:
        d.update({f"@{k}": v for k, v in elem.attrib.items()})

    # child elements
    children = list(elem)
    if children:
        child_dict = {}
        for child in children:
            child_res = _etree_to_dict(child)
            tag = child.tag
            # if tag already present, coerce into list
            if tag in child_dict:
                if not isinstance(child_dict[tag], list):
                    child_dict[tag] = [child_dict[tag]]
                child_dict[tag].append(child_res)
            else:
                child_dict[tag] = child_res
        d.update(child_dict)
    # text content
    text = (elem.text or '').strip()
    if text and (children or elem.attrib):
        d['#text'] = text
    elif text:
        return text

    return d
