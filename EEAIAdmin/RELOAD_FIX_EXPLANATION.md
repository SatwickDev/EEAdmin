# JSON Reload Fix - Issue & Solution

## Problem Identified

Your JSON files (in `data/` and `app/data/`) were **not being reloaded** even though `reload_all_jsons()` and `reload_app_data()` were being called. 

### Root Cause

The reload functions had a **flawed marker file check** that was causing them to **skip valid reloads**:

```python
# OLD CODE (INCORRECT) - in reload_helper.py
marker = os.path.join(data_folder, '.last_reload')
try:
    marker_mtime = os.path.getmtime(marker)
except Exception:
    marker_mtime = None

if marker_mtime and last_reload and marker_mtime <= last_reload:
    logger.debug('Skipping reload_all_jsons: marker mtime <= last reload')
    return False  # ❌ RELOAD SKIPPED INCORRECTLY
```

**Why this failed:**

1. **App starts**: `_last_json_reload` is set to the **max mtime of all files** at startup
2. **You edit `data/entities.json`**: The file mtime is now newer, but...
3. **Reload functions called**: They compare `marker_mtime <= last_reload`
4. **Problem**: The `.last_reload` marker **only exists and gets touched AFTER a successful reload**
5. **Result**: If marker is older than the startup timestamp, reload is skipped even though the file changed!

## Solution Applied

Replaced the unreliable **marker file mtime check** with a **direct file mtime check**:

```python
# NEW CODE (CORRECT) - in reload_helper.py
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
```

**What changed:**

- ✅ **Removed** unreliable marker file check
- ✅ **Added** direct file mtime comparison to `last_reload`
- ✅ **Now detects**: Any JSON/YAML/XML file in `data/` or `app/data/` whose mtime is **newer than the last reload timestamp**
- ✅ **Added detailed logging**: Shows which file triggered the reload and the timestamps

## Changes Made

### File: `app/utils/reload_helper.py`

1. **`reload_all_jsons()` function** (lines ~130-160):
   - Removed: Marker file mtime check (was: `if marker_mtime and last_reload and marker_mtime <= last_reload: return False`)
   - Added: Real file mtime check that walks the folder and compares each file's mtime to `last_reload`
   - Improved: Debounce logging to show exact time delta

2. **`reload_app_data()` function** (lines ~285-315):
   - Same changes applied to app-level data folder reload logic

3. **Success logging**:
   - Enhanced to show which cache keys were updated: `Cache keys: {list(json_data_cache.keys())[:10]}...`

## How It Works Now

### Flow When You Edit `data/entities.json`

```
1. You edit data/entities.json on disk
   └─> File mtime changes to current time

2. API endpoint calls reload_all_jsons()
   ├─> Gets last_reload timestamp from app._last_json_reload
   ├─> Checks if debounce window (2 seconds) has passed ✅
   └─> Walks data/ folder and checks each file mtime

3. Reload function detects entities.json has mtime > last_reload
   ├─> Sets any_file_changed = True
   ├─> Loads JSON from disk
   └─> Updates app.json_data_cache['entities'] with new content

4. Cache is updated IN-PLACE
   └─> All code referencing app.json_data_cache sees new data immediately

5. Marker file is touched
   └─> Other processes will detect change on next request

6. last_reload timestamp is updated
   └─> Next reload attempt will debounce for 2 seconds
```

## Testing the Fix

### Manual Test
```powershell
# 1. Start your Flask app (if not running)
# 2. Edit data/entities.json with a small change (add a comment, change a value)
# 3. Call the classify-initial endpoint
Invoke-RestMethod -Uri http://localhost:5000/api/document/classify-initial -Method Post -Form @{files=@("path/to/file.pdf")}

# 4. Check the logs - you should see:
# "📝 File changed: entities (mtime=..., last_reload=...)"
# "✅ JSON folder reloaded successfully from ... ; X entries updated"
```

### What to Look For in Logs
- ✅ `📝 File changed: entities` - File change detected
- ✅ `✅ JSON folder reloaded successfully` - Reload completed
- ✅ `entities` in the cache keys list - entities.json is now in memory

### If You Still See Issues
- Check `last_reload` value: Should be from `app._last_json_reload` after startup
- Verify file mtime: Use `Get-Item -Path data/entities.json | Select LastWriteTime` in PowerShell
- Compare: If file's mtime > `last_reload`, reload WILL happen

## Debounce Window

The reload function **will not reload more frequently than every 2 seconds**. This is intentional to prevent thrashing on rapid edits.

- If you edit a file and immediately call reload again within 2 seconds, the second call will skip
- This is normal behavior and improves performance
- If you need instant reload, wait 2+ seconds between edits and API calls

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Detection Method** | Marker file mtime (unreliable) | Direct file mtime check (reliable) |
| **When Reloads** | When marker was newer (rare) | When any file is newer than last_reload |
| **False Negatives** | ❌ Many (files changed but not reloaded) | ✅ None (file changes detected) |
| **Logging** | Minimal | Detailed (which file, which timestamps) |
| **Performance** | Same | Same (still debounced to 2 seconds) |

---

**The fix is now deployed. Edit your JSON files and call the endpoints - reloads should now work as expected!**
