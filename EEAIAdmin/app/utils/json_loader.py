import os
import json
import yaml


def reload_json_folder(folder_path: str):
    """
    Recursively load all JSON files in the folder and its subfolders.
    """
    data_cache = {}

    folder_path = os.fspath(folder_path)  # ✅ ensures it's a str/path
    for root, _, files in os.walk(folder_path):

        for filename in files:
            full_path = os.path.join(root, filename)
            # ✅ Convert to string explicitly for type checking
            relative_path = os.path.relpath(str(full_path), str(folder_path))
            key = relative_path.replace("\\", "/").replace(".json", "")

            if filename.endswith(".json"):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data_cache[key] = json.load(f)
                except Exception as e:
                    print(f"⚠️ Could not load {relative_path}: {e}")

            # --- Load YAML / YML files ---
            elif filename.endswith(('.yaml', '.yml')):

                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data_cache[key] = yaml.safe_load(f)
                    #print(f"✅ YAML loaded: {filename}")
                except yaml.YAMLError as e:
                    print(f"⚠️ Error loading YAML {relative_path}: {e}")
        # for file, content in data_cache.items():
        #     print(f"{file} loaded, keys: {list(content.keys())}")

    return data_cache
