# Smart Integration Strategy for Cleaned/Refactored Projects
**Project:** EEAIAdmin - Environment Variables Integration  
**Date:** December 8, 2025  
**Context:** Integration into a cleaned, refactored codebase with removed legacy code  

---

## 🎯 Overview

This guide provides a **smart, adaptive approach** for integrating environment variable configurations into a **cleaned and refactored project** where:
- ✅ Unnecessary code has been removed
- ✅ File structure may be different
- ✅ Function names may have changed
- ✅ Best practices have been applied
- ✅ Code has been optimized

**Strategy:** Analyze → Adapt → Integrate → Verify

---

## 📊 Phase 1: Project Analysis

### Step 1.1: Understand Your Updated Project Structure

```powershell
# Navigate to your updated project
cd C:\Users\saipr\Documents\GitHub\YourUpdatedProject

# Create a structure report
Get-ChildItem -Recurse -File -Include *.py | Select-Object FullName | Out-File "project_structure.txt"

# List all Python files
Get-ChildItem -Recurse -Filter "*.py" | Select-Object Name, Directory, Length
```

### Step 1.2: Identify Existing Configuration Patterns

Create `analyze_config.py`:
```python
import os
import re
from pathlib import Path

def analyze_configuration_usage(project_root):
    """Analyze how configuration is currently handled"""
    
    patterns = {
        'env_vars': r'os\.getenv\(["\']([^"\']+)["\']',
        'environ': r'os\.environ\[["\']([^"\']+)["\']\]',
        'hardcoded_mongo': r'mongodb://[^"\'\s]+',
        'hardcoded_azure': r'https://[^"\'\s]*\.openai\.azure\.com',
        'hardcoded_keys': r'["\'][a-zA-Z0-9]{20,}["\']',
        'config_imports': r'from\s+[\w.]+\s+import\s+.*config',
    }
    
    findings = {pattern: [] for pattern in patterns}
    
    for py_file in Path(project_root).rglob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8')
            
            for pattern_name, pattern in patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    findings[pattern_name].append({
                        'file': str(py_file),
                        'matches': matches
                    })
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    # Generate report
    print("=" * 80)
    print("CONFIGURATION ANALYSIS REPORT")
    print("=" * 80)
    
    print("\n📌 Environment Variables Currently Used:")
    if findings['env_vars']:
        env_vars = set()
        for finding in findings['env_vars']:
            env_vars.update(finding['matches'])
        for var in sorted(env_vars):
            print(f"  - {var}")
    else:
        print("  None found")
    
    print("\n📌 Hardcoded MongoDB URIs:")
    if findings['hardcoded_mongo']:
        for finding in findings['hardcoded_mongo']:
            print(f"  File: {finding['file']}")
            for match in finding['matches'][:2]:  # Show first 2
                print(f"    - {match}")
    else:
        print("  ✅ None found (good!)")
    
    print("\n📌 Hardcoded Azure Endpoints:")
    if findings['hardcoded_azure']:
        for finding in findings['hardcoded_azure']:
            print(f"  File: {finding['file']}")
            for match in finding['matches'][:2]:
                print(f"    - {match}")
    else:
        print("  ✅ None found (good!)")
    
    print("\n📌 Config Module Imports:")
    if findings['config_imports']:
        for finding in findings['config_imports']:
            print(f"  File: {finding['file']}")
    else:
        print("  None found")
    
    print("\n" + "=" * 80)
    
    return findings

if __name__ == "__main__":
    project_root = "."  # Current directory
    analyze_configuration_usage(project_root)
```

Run it:
```powershell
python analyze_config.py > config_analysis_report.txt
```

### Step 1.3: Compare File Structures

Create `compare_structures.py`:
```python
from pathlib import Path
import json

def get_file_structure(root_path, name="project"):
    """Get file structure as dictionary"""
    structure = {
        'name': name,
        'files': [],
        'key_dirs': {}
    }
    
    root = Path(root_path)
    
    # Check for key directories
    key_dirs = ['app', 'utils', 'config', 'core', 'services', 'managers']
    for dir_name in key_dirs:
        dir_path = root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            structure['key_dirs'][dir_name] = {
                'exists': True,
                'files': [f.name for f in dir_path.glob("*.py")]
            }
    
    # Check for specific files
    key_files = [
        'run.py', 'main.py', 'app.py',
        'config.py', 'settings.py',
        '.env', '.env.example',
        'requirements.txt'
    ]
    
    for file_name in key_files:
        file_path = root / file_name
        if file_path.exists():
            structure['files'].append(file_name)
    
    return structure

def compare_projects(old_project, new_project):
    """Compare two project structures"""
    print("=" * 80)
    print("PROJECT STRUCTURE COMPARISON")
    print("=" * 80)
    
    old_struct = get_file_structure(old_project, "Original (EEAIAdmin)")
    new_struct = get_file_structure(new_project, "Updated Project")
    
    print("\n📁 Original Project Structure:")
    print(f"  Key Files: {', '.join(old_struct['files']) if old_struct['files'] else 'None'}")
    print(f"  Key Directories: {', '.join(old_struct['key_dirs'].keys())}")
    
    print("\n📁 Updated Project Structure:")
    print(f"  Key Files: {', '.join(new_struct['files']) if new_struct['files'] else 'None'}")
    print(f"  Key Directories: {', '.join(new_struct['key_dirs'].keys())}")
    
    print("\n🔍 Structural Differences:")
    
    # Compare key directories
    old_dirs = set(old_struct['key_dirs'].keys())
    new_dirs = set(new_struct['key_dirs'].keys())
    
    common_dirs = old_dirs & new_dirs
    only_old = old_dirs - new_dirs
    only_new = new_dirs - old_dirs
    
    if common_dirs:
        print(f"  ✅ Common directories: {', '.join(common_dirs)}")
    if only_old:
        print(f"  ⚠️  Removed in new project: {', '.join(only_old)}")
    if only_new:
        print(f"  ✨ New in updated project: {', '.join(only_new)}")
    
    print("\n📝 Integration Recommendations:")
    
    # Provide recommendations based on structure
    if 'app' in new_dirs and 'utils' in old_struct['key_dirs'].get('app', {}).get('files', []):
        print("  1. ✅ app/utils/ directory exists - can copy manager files directly")
    elif 'utils' in new_dirs:
        print("  1. ⚠️  'utils' is at root level - adjust import paths")
    elif 'config' in new_dirs:
        print("  1. ℹ️  'config' directory found - consider placing managers there")
    
    if 'run.py' in new_struct['files']:
        print("  2. ✅ run.py exists - can update server configuration")
    elif 'main.py' in new_struct['files']:
        print("  2. ℹ️  main.py found instead - use it for server configuration")
    elif 'app.py' in new_struct['files']:
        print("  2. ℹ️  app.py found instead - use it for server configuration")
    
    if '.env' in new_struct['files']:
        print("  3. ⚠️  .env already exists - merge configurations carefully")
    else:
        print("  3. ✅ No .env found - can copy directly")
    
    print("\n" + "=" * 80)
    
    return old_struct, new_struct

if __name__ == "__main__":
    old_project = r"C:\Users\saipr\Documents\GitHub\EEAIAdmin"
    new_project = "."  # Current directory (your updated project)
    
    compare_projects(old_project, new_project)
```

Run it:
```powershell
python compare_structures.py
```

---

## 🔧 Phase 2: Adaptive Integration Planning

### Step 2.1: Create Integration Mapping

Based on your analysis results, create a mapping document:

Create `integration_mapping.json`:
```json
{
  "file_mappings": {
    "manager_files": {
      "source": "EEAIAdmin/app/utils/",
      "destination": "app/utils/",
      "files": [
        "api_config_manager.py",
        "mongodb_manager.py",
        "chromadb_repository_manager.py"
      ],
      "status": "pending"
    },
    "configuration_files": {
      "source": "EEAIAdmin/",
      "destination": "./",
      "files": [
        ".env"
      ],
      "action": "merge_if_exists"
    }
  },
  "code_patterns_to_replace": {
    "mongodb_connections": {
      "find_pattern": "MongoClient\\([\"']mongodb://[^\"']+[\"']\\)",
      "replace_with": "get_mongo_database() from mongodb_manager",
      "files": "**/*.py"
    },
    "chromadb_connections": {
      "find_pattern": "chromadb\\.HttpClient\\(host=[^)]+\\)",
      "replace_with": "ChromaDBRepositoryManager().get_chroma_client_for_customer()",
      "files": "**/*.py"
    },
    "azure_openai_hardcoded": {
      "find_pattern": "openai\\.api_key\\s*=\\s*[\"'][^\"']+[\"']",
      "replace_with": "configure_azure_openai(openai) from api_config_manager",
      "files": "**/*.py"
    }
  },
  "import_updates": {
    "add_imports": [
      "from app.utils.api_config_manager import configure_azure_openai, get_azure_openai_key",
      "from app.utils.mongodb_manager import get_mongo_database",
      "from app.utils.chromadb_repository_manager import ChromaDBRepositoryManager"
    ]
  }
}
```

### Step 2.2: Generate Smart Integration Script

Create `smart_integrate.py`:
```python
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Tuple

class SmartIntegrator:
    def __init__(self, source_project: str, target_project: str):
        self.source = Path(source_project)
        self.target = Path(target_project)
        self.changes_log = []
        
    def log_change(self, action: str, file: str, details: str):
        """Log integration changes"""
        self.changes_log.append({
            'action': action,
            'file': file,
            'details': details
        })
        print(f"[{action}] {file}: {details}")
    
    def find_target_directory(self, preferred_paths: List[str]) -> Path:
        """Find the best target directory from a list of preferences"""
        for path_str in preferred_paths:
            path = self.target / path_str
            if path.exists() and path.is_dir():
                return path
        
        # If none exist, return the first preference
        return self.target / preferred_paths[0]
    
    def copy_manager_files(self):
        """Copy manager files to appropriate location"""
        print("\n" + "=" * 60)
        print("COPYING MANAGER FILES")
        print("=" * 60)
        
        manager_files = [
            'api_config_manager.py',
            'mongodb_manager.py',
            'chromadb_repository_manager.py'
        ]
        
        # Try to find the best location
        source_dir = self.source / 'app' / 'utils'
        target_options = [
            'app/utils',
            'utils',
            'config',
            'core',
            'services/config',
        ]
        
        target_dir = self.find_target_directory(target_options)
        
        print(f"\n📂 Source: {source_dir}")
        print(f"📂 Target: {target_dir}")
        
        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for filename in manager_files:
            source_file = source_dir / filename
            target_file = target_dir / filename
            
            if not source_file.exists():
                self.log_change("WARNING", filename, "Source file not found")
                continue
            
            if target_file.exists():
                # Create backup
                backup_file = target_file.with_suffix('.py.backup')
                shutil.copy2(target_file, backup_file)
                self.log_change("BACKUP", str(target_file), f"Backed up to {backup_file}")
            
            shutil.copy2(source_file, target_file)
            self.log_change("COPIED", str(target_file), "Manager file copied successfully")
        
        return target_dir
    
    def merge_env_files(self):
        """Merge .env files intelligently"""
        print("\n" + "=" * 60)
        print("MERGING .env FILES")
        print("=" * 60)
        
        source_env = self.source / '.env'
        target_env = self.target / '.env'
        
        if not source_env.exists():
            self.log_change("WARNING", ".env", "Source .env not found")
            return
        
        # Read source .env
        with open(source_env, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
        
        # Parse environment variables from source
        source_vars = {}
        current_section = None
        
        for line in source_lines:
            line = line.strip()
            
            # Track sections
            if line.startswith('#') and '=' * 10 in line:
                current_section = line
            elif '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                source_vars[key] = {
                    'line': line,
                    'section': current_section
                }
        
        if target_env.exists():
            # Read target .env
            with open(target_env, 'r', encoding='utf-8') as f:
                target_lines = f.readlines()
            
            # Parse target variables
            target_vars = set()
            for line in target_lines:
                if '=' in line and not line.strip().startswith('#'):
                    key = line.split('=')[0].strip()
                    target_vars.add(key)
            
            # Find new variables
            new_vars = set(source_vars.keys()) - target_vars
            
            if new_vars:
                print(f"\n✨ Adding {len(new_vars)} new variables to existing .env:")
                
                # Append new variables
                with open(target_env, 'a', encoding='utf-8') as f:
                    f.write("\n\n# ========================================\n")
                    f.write("# Added by Smart Integration\n")
                    f.write("# ========================================\n\n")
                    
                    for var in sorted(new_vars):
                        if source_vars[var]['section']:
                            f.write(f"{source_vars[var]['section']}\n")
                        f.write(f"{source_vars[var]['line']}\n")
                        print(f"  + {var}")
                
                self.log_change("MERGED", str(target_env), f"Added {len(new_vars)} new variables")
            else:
                print("\n✅ All environment variables already present")
                self.log_change("SKIPPED", str(target_env), "No new variables to add")
        else:
            # Copy entire .env
            shutil.copy2(source_env, target_env)
            print(f"\n✅ Copied complete .env file ({len(source_vars)} variables)")
            self.log_change("COPIED", str(target_env), "New .env file created")
    
    def find_files_with_pattern(self, pattern: str, extensions: List[str] = ['.py']) -> List[Path]:
        """Find files containing a specific pattern"""
        matching_files = []
        
        for ext in extensions:
            for file_path in self.target.rglob(f"*{ext}"):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if re.search(pattern, content):
                        matching_files.append(file_path)
                except Exception as e:
                    continue
        
        return matching_files
    
    def suggest_code_changes(self):
        """Suggest code changes for integration"""
        print("\n" + "=" * 60)
        print("CODE CHANGE SUGGESTIONS")
        print("=" * 60)
        
        patterns_to_check = {
            'Hardcoded MongoDB': r'MongoClient\(["\']mongodb://[^"\']+["\']\)',
            'Hardcoded ChromaDB': r'chromadb\.HttpClient\(host=',
            'Hardcoded OpenAI Key': r'openai\.api_key\s*=\s*["\'][^"\']{20,}["\']',
            'Hardcoded Azure Endpoint': r'openai\.api_base\s*=\s*["\']https://[^"\']+\.openai\.azure\.com',
        }
        
        suggestions = {}
        
        for description, pattern in patterns_to_check.items():
            files = self.find_files_with_pattern(pattern)
            if files:
                suggestions[description] = files
        
        if suggestions:
            print("\n⚠️  Found hardcoded values that should use environment variables:\n")
            
            for description, files in suggestions.items():
                print(f"  {description}:")
                for file in files:
                    rel_path = file.relative_to(self.target)
                    print(f"    - {rel_path}")
                    self.log_change("TODO", str(rel_path), f"Contains {description}")
        else:
            print("\n✅ No hardcoded values found - code looks clean!")
        
        return suggestions
    
    def generate_integration_report(self):
        """Generate final integration report"""
        print("\n" + "=" * 60)
        print("INTEGRATION REPORT")
        print("=" * 60)
        
        # Summary
        action_counts = {}
        for change in self.changes_log:
            action = change['action']
            action_counts[action] = action_counts.get(action, 0) + 1
        
        print("\n📊 Summary:")
        for action, count in sorted(action_counts.items()):
            print(f"  {action}: {count}")
        
        # Save detailed log
        log_file = self.target / 'integration_log.txt'
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("SMART INTEGRATION LOG\n")
            f.write("=" * 60 + "\n\n")
            
            for change in self.changes_log:
                f.write(f"[{change['action']}] {change['file']}\n")
                f.write(f"  {change['details']}\n\n")
        
        print(f"\n📄 Detailed log saved to: {log_file}")
        
        # Next steps
        print("\n📋 Next Steps:")
        print("  1. Review integration_log.txt for all changes")
        print("  2. Update import statements in files with TODO markers")
        print("  3. Test configuration loading with test_config.py")
        print("  4. Test manager functions with test_managers.py")
        print("  5. Run your application and check logs")
        
    def run(self):
        """Run the complete smart integration"""
        print("\n" + "=" * 80)
        print("SMART INTEGRATION PROCESS")
        print("=" * 80)
        print(f"\nSource: {self.source}")
        print(f"Target: {self.target}")
        
        # Execute integration steps
        self.copy_manager_files()
        self.merge_env_files()
        self.suggest_code_changes()
        self.generate_integration_report()
        
        print("\n✅ Smart integration completed!")

if __name__ == "__main__":
    source_project = r"C:\Users\saipr\Documents\GitHub\EEAIAdmin"
    target_project = "."  # Current directory
    
    integrator = SmartIntegrator(source_project, target_project)
    integrator.run()
```

---

## 🎯 Phase 3: Execution Strategy

### Option A: Automated Smart Integration (Recommended)

```powershell
# Step 1: Run analysis first
python analyze_config.py

# Step 2: Compare structures
python compare_structures.py

# Step 3: Run smart integration
python smart_integrate.py

# Step 4: Review the integration log
notepad integration_log.txt
```

### Option B: Manual Guided Integration

If your project structure is very different, follow this manual approach:

#### 1. Identify Where Configuration Should Live

```powershell
# Find existing config files
Get-ChildItem -Recurse -Include *config*.py, *settings*.py
```

**Decision Tree:**
- If `app/utils/` exists → Place managers there
- If `config/` exists → Place managers there
- If `core/` exists → Create `core/config/` and place there
- If `services/` exists → Create `services/config/` and place there

#### 2. Copy Files with Path Awareness

```powershell
# Example: If your project uses 'config/' instead of 'app/utils/'
$source = "C:\Users\saipr\Documents\GitHub\EEAIAdmin\app\utils"
$target = ".\config"

# Create target if needed
New-Item -ItemType Directory -Force -Path $target

# Copy manager files
Copy-Item "$source\api_config_manager.py" -Destination $target
Copy-Item "$source\mongodb_manager.py" -Destination $target
Copy-Item "$source\chromadb_repository_manager.py" -Destination $target
```

#### 3. Update Import Paths

If you placed managers in a different location, update imports:

**Original import:**
```python
from app.utils.api_config_manager import configure_azure_openai
```

**Updated import (if using 'config/' directory):**
```python
from config.api_config_manager import configure_azure_openai
```

#### 4. Merge .env Carefully

```powershell
# If you already have .env, merge manually
notepad .env
notepad C:\Users\saipr\Documents\GitHub\EEAIAdmin\.env

# Or use a diff tool
code --diff .env C:\Users\saipr\Documents\GitHub\EEAIAdmin\.env
```

---

## 🔍 Phase 4: Code Pattern Migration

### Pattern 1: Replace MongoDB Direct Connections

**Find:**
```python
# Search for direct MongoDB connections
Get-ChildItem -Recurse -Filter "*.py" | Select-String -Pattern "MongoClient\("
```

**Before:**
```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["database_name"]
collection = db["collection_name"]
```

**After:**
```python
from app.utils.mongodb_manager import get_mongo_database
# Or: from config.mongodb_manager import get_mongo_database (if using config/)

db = get_mongo_database()  # or get_mongo_database(customer_id)
if db:
    collection = db["collection_name"]
    # Use collection
else:
    logger.error("MongoDB not available")
```

### Pattern 2: Replace ChromaDB Direct Connections

**Find:**
```python
Get-ChildItem -Recurse -Filter "*.py" | Select-String -Pattern "chromadb\."
```

**Before:**
```python
import chromadb

client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_or_create_collection("my_collection")
```

**After:**
```python
from app.utils.chromadb_repository_manager import ChromaDBRepositoryManager

chroma_manager = ChromaDBRepositoryManager()
if chroma_manager.is_chromadb_enabled_for_customer(customer_id):
    client = chroma_manager.get_chroma_client_for_customer(customer_id)
    collection = client.get_or_create_collection("my_collection")
else:
    logger.warning("ChromaDB not available")
```

### Pattern 3: Replace Azure OpenAI Hardcoded Config

**Find:**
```python
Get-ChildItem -Recurse -Filter "*.py" | Select-String -Pattern "openai\.api"
```

**Before:**
```python
import openai

openai.api_type = "azure"
openai.api_base = "https://your-resource.openai.azure.com/"
openai.api_key = "your-api-key"
openai.api_version = "2024-02-01"

response = openai.ChatCompletion.create(
    engine="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
```

**After:**
```python
import openai
from app.utils.api_config_manager import configure_azure_openai, get_azure_deployment_name

# Configure once at startup (in app initialization)
configure_azure_openai(openai)

# Then use throughout the app
deployment_name = get_azure_deployment_name()

response = openai.ChatCompletion.create(
    engine=deployment_name,
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Pattern 4: Update Server Configuration

**Find your main entry point:**
```powershell
# Could be run.py, main.py, app.py, or server.py
Get-ChildItem -Filter "*.py" | Where-Object { $_.Name -match "^(run|main|app|server)\.py$" }
```

**Before (run.py, main.py, etc.):**
```python
from app import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
```

**After:**
```python
import os
from app import create_app

if __name__ == "__main__":
    app = create_app()
    
    # Get configuration from environment
    host = os.environ.get('SERVER_HOST', '0.0.0.0')
    port = int(os.environ.get('HTTP_PORT', '5000'))
    debug = os.environ.get('DEBUG_MODE', 'true').lower() in ('true', '1', 'yes')
    
    app.run(host=host, port=port, debug=debug)
```

---

## 🧪 Phase 5: Testing Strategy

### Test 1: Configuration Validation

Create `validate_integration.py`:
```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def validate_integration():
    """Validate that integration was successful"""
    
    print("=" * 60)
    print("INTEGRATION VALIDATION")
    print("=" * 60)
    
    issues = []
    warnings = []
    success = []
    
    # Check 1: .env file exists
    if Path('.env').exists():
        success.append("✅ .env file exists")
        load_dotenv()
    else:
        issues.append("❌ .env file not found")
    
    # Check 2: Manager files exist
    manager_locations = [
        'app/utils/api_config_manager.py',
        'config/api_config_manager.py',
        'core/config/api_config_manager.py',
    ]
    
    manager_found = False
    for location in manager_locations:
        if Path(location).exists():
            success.append(f"✅ Manager files found at: {location}")
            manager_found = True
            
            # Try to import
            try:
                # Add parent directory to path
                sys.path.insert(0, str(Path(location).parent.parent))
                
                if 'app/utils' in location:
                    from app.utils import api_config_manager
                elif 'config' in location:
                    import api_config_manager
                
                success.append("✅ Manager files can be imported")
            except ImportError as e:
                warnings.append(f"⚠️  Import issue: {e}")
            
            break
    
    if not manager_found:
        issues.append("❌ Manager files not found in any expected location")
    
    # Check 3: Environment variables
    required_vars = [
        'MONGO_URI',
        'AZURE_OPENAI_API_BASE',
        'AZURE_OPENAI_API_KEY',
    ]
    
    for var in required_vars:
        if os.getenv(var):
            success.append(f"✅ {var} is set")
        else:
            warnings.append(f"⚠️  {var} not set")
    
    # Print results
    print("\n✅ Success:")
    for item in success:
        print(f"  {item}")
    
    if warnings:
        print("\n⚠️  Warnings:")
        for item in warnings:
            print(f"  {item}")
    
    if issues:
        print("\n❌ Issues:")
        for item in issues:
            print(f"  {item}")
        print("\n❌ Integration validation FAILED")
        return False
    else:
        print("\n✅ Integration validation PASSED")
        return True

if __name__ == "__main__":
    validate_integration()
```

Run it:
```powershell
python validate_integration.py
```

### Test 2: Manager Functionality

Create `test_managers_adaptive.py`:
```python
import sys
from pathlib import Path

def find_and_import_managers():
    """Dynamically find and import manager modules"""
    
    # Try different import paths
    import_attempts = [
        ('app.utils', ['api_config_manager', 'mongodb_manager', 'chromadb_repository_manager']),
        ('config', ['api_config_manager', 'mongodb_manager', 'chromadb_repository_manager']),
        ('core.config', ['api_config_manager', 'mongodb_manager', 'chromadb_repository_manager']),
    ]
    
    for module_path, manager_names in import_attempts:
        try:
            managers = {}
            for name in manager_names:
                full_path = f"{module_path}.{name}"
                managers[name] = __import__(full_path, fromlist=[name])
            
            print(f"✅ Successfully imported from: {module_path}")
            return managers
        except ImportError:
            continue
    
    raise ImportError("Could not import manager modules from any expected location")

def test_managers():
    """Test manager functionality"""
    
    print("=" * 60)
    print("MANAGER FUNCTIONALITY TEST")
    print("=" * 60)
    
    try:
        managers = find_and_import_managers()
        
        # Test API Config Manager
        print("\n🔧 Testing API Config Manager:")
        try:
            api_config = managers['api_config_manager'].get_api_config()
            print(f"  ✅ get_api_config() works")
            print(f"  Azure OpenAI enabled: {api_config['azure_openai']['enabled']}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Test MongoDB Manager
        print("\n🍃 Testing MongoDB Manager:")
        try:
            mongo_config = managers['mongodb_manager'].get_mongo_config()
            print(f"  ✅ get_mongo_config() works")
            print(f"  Mode: {mongo_config['mode']}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Test ChromaDB Manager
        print("\n📦 Testing ChromaDB Manager:")
        try:
            ChromaDBManager = managers['chromadb_repository_manager'].ChromaDBRepositoryManager
            chroma_manager = ChromaDBManager()
            config = chroma_manager.get_chromadb_config()
            print(f"  ✅ ChromaDBRepositoryManager instantiation works")
            print(f"  Mode: {config['mode']}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print("\n✅ Manager tests completed")
        
    except Exception as e:
        print(f"\n❌ Failed to test managers: {e}")

if __name__ == "__main__":
    test_managers()
```

Run it:
```powershell
python test_managers_adaptive.py
```

### Test 3: Application Startup

```powershell
# Try to start your application
python run.py
# or python main.py
# or python app.py

# Check for these log messages:
# [INFO] Azure OpenAI configured successfully
# [INFO] MongoDB connected
# [INFO] ChromaDB mode: enabled
```

---

## 📋 Common Scenarios & Solutions

### Scenario 1: Different Directory Structure

**Problem:** Your project uses `src/` instead of `app/`

**Solution:**
```powershell
# Copy managers to appropriate location
Copy-Item "C:\Users\saipr\Documents\GitHub\EEAIAdmin\app\utils\*.py" -Destination "src\utils\" -Include "*_manager.py"

# Update imports in your code
# From: from app.utils.api_config_manager import ...
# To:   from src.utils.api_config_manager import ...
```

### Scenario 2: Already Have Configuration Module

**Problem:** You already have a `config.py` or `settings.py`

**Solution:** Integrate managers into existing structure

```python
# In your existing config.py
from pathlib import Path

# Import our managers
try:
    from .api_config_manager import (
        configure_azure_openai,
        get_api_config,
        get_azure_openai_key
    )
    from .mongodb_manager import get_mongo_database
    from .chromadb_repository_manager import ChromaDBRepositoryManager
    
    # Make them available through your config module
    __all__ = [
        'configure_azure_openai',
        'get_api_config',
        'get_azure_openai_key',
        'get_mongo_database',
        'ChromaDBRepositoryManager'
    ]
except ImportError as e:
    print(f"Warning: Could not import manager modules: {e}")
```

### Scenario 3: Using Different Python Package Manager

**Problem:** Your project uses Poetry/Pipenv instead of pip

**Solution:**

**For Poetry:**
```powershell
# Add dependencies
poetry add python-dotenv pymongo chromadb

# Install
poetry install
```

**For Pipenv:**
```powershell
# Add dependencies
pipenv install python-dotenv pymongo chromadb

# Install
pipenv install
```

### Scenario 4: Microservices Architecture

**Problem:** Your project has multiple services, each needs configuration

**Solution:** Create a shared configuration package

```
your_project/
├── services/
│   ├── service_a/
│   ├── service_b/
│   └── service_c/
├── shared/
│   └── config/
│       ├── __init__.py
│       ├── api_config_manager.py
│       ├── mongodb_manager.py
│       └── chromadb_repository_manager.py
└── .env  # Shared across all services
```

Each service imports from shared:
```python
from shared.config import get_mongo_database, configure_azure_openai
```

---

## ✅ Integration Checklist for Cleaned Projects

- [ ] **Analysis Phase**
  - [ ] Run `analyze_config.py` to understand current configuration
  - [ ] Run `compare_structures.py` to compare project structures
  - [ ] Document differences in `integration_notes.txt`

- [ ] **Preparation Phase**
  - [ ] Backup your updated project completely
  - [ ] Create `.env.backup` if .env already exists
  - [ ] Note all custom configuration currently in place

- [ ] **Manager Files Integration**
  - [ ] Identify correct target directory (app/utils, config, core, etc.)
  - [ ] Copy `api_config_manager.py` to target
  - [ ] Copy `mongodb_manager.py` to target
  - [ ] Copy `chromadb_repository_manager.py` to target
  - [ ] Update `__init__.py` in target directory if needed

- [ ] **Environment Variables**
  - [ ] Merge or copy `.env` file
  - [ ] Review all variables for correctness
  - [ ] Update `.gitignore` to exclude `.env`
  - [ ] Create `.env.example` without sensitive data

- [ ] **Code Updates**
  - [ ] Update import paths if directory structure differs
  - [ ] Replace MongoDB direct connections
  - [ ] Replace ChromaDB direct connections
  - [ ] Replace Azure OpenAI hardcoded config
  - [ ] Update server configuration in main file

- [ ] **Testing Phase**
  - [ ] Run `validate_integration.py`
  - [ ] Run `test_managers_adaptive.py`
  - [ ] Test application startup
  - [ ] Test each feature/endpoint
  - [ ] Check logs for any errors

- [ ] **Documentation**
  - [ ] Document any custom integration steps
  - [ ] Update project README with environment setup
  - [ ] Create deployment guide with environment variables
  - [ ] Note any deviations from standard integration

---

## 🚀 Quick Decision Matrix

| Your Project Has... | Recommended Action |
|---------------------|-------------------|
| `app/utils/` directory | ✅ Copy managers directly there |
| `config/` directory only | ✅ Copy managers to `config/` |
| `src/utils/` directory | ✅ Copy to `src/utils/`, update imports |
| `core/` directory | ✅ Create `core/config/`, copy there |
| Existing `config.py` | ⚠️  Integrate managers into it (Scenario 2) |
| Microservices structure | ⚠️  Create shared package (Scenario 4) |
| Very different structure | ⚠️  Use manual approach + adapt paths |

---

## 📞 Need Help?

If the automated integration doesn't work for your specific structure:

1. **Share your project structure:**
   ```powershell
   tree /F /A > project_structure.txt
   ```

2. **Run the analysis tools:**
   ```powershell
   python analyze_config.py > analysis.txt
   python compare_structures.py > comparison.txt
   ```

3. **Document your specific case** and we can create custom integration steps

---

**Document Version:** 1.0  
**Last Updated:** December 8, 2025  
**Status:** Ready for Complex/Cleaned Projects  

---

## 🎯 TL;DR - Quick Start for Cleaned Projects

```powershell
# 1. Analyze your project first
cd YourUpdatedProject
python analyze_config.py
python compare_structures.py

# 2. Run smart integration
python smart_integrate.py

# 3. Validate
python validate_integration.py
python test_managers_adaptive.py

# 4. Test your app
python run.py  # or main.py or whatever your entry point is
```

Good luck! 🚀
