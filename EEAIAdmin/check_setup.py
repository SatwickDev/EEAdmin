#!/usr/bin/env python3
"""
Check EEAI setup status
"""

import os
import sys
import subprocess

def check_command(command, name):
    """Check if a command exists"""
    try:
        subprocess.run([command, '--version'], capture_output=True, check=True)
        print(f"✓ {name} is installed")
        return True
    except:
        print(f"✗ {name} is NOT installed")
        return False

def check_server():
    """Check if Flask server is running"""
    try:
        import requests
        response = requests.get('http://localhost:5000', timeout=2)
        print("✓ Flask server is running")
        return True
    except:
        print("✗ Flask server is NOT running")
        print("  Start it with: python run.py")
        return False

def check_mongodb():
    """Check if MongoDB is accessible"""
    try:
        from pymongo import MongoClient
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000)
        client.server_info()
        print("✓ MongoDB is running")
        return True
    except:
        print("✗ MongoDB is NOT accessible")
        print("  Make sure MongoDB is installed and running")
        return False

def check_dependencies():
    """Check Python dependencies"""
    required = ['flask', 'pymongo', 'requests']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"✗ Missing Python packages: {', '.join(missing)}")
        print(f"  Install with: pip install {' '.join(missing)}")
        return False
    else:
        print("✓ All Python dependencies installed")
        return True

def main():
    print("=== EEAI Setup Status Check ===\n")
    
    checks = [
        lambda: check_command('python3', 'Python 3'),
        lambda: check_command('mongod', 'MongoDB'),
        check_dependencies,
        check_mongodb,
        check_server
    ]
    
    all_good = True
    for check in checks:
        if not check():
            all_good = False
    
    print("\n" + "="*30)
    if all_good:
        print("✓ All checks passed! You're ready to set up EEAI.")
        print("\nNext steps:")
        print("1. Run: python create_admin_auto.py")
        print("2. Run: python create_repositories_auto.py")
        print("3. Login at http://localhost:5000/")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print("\nTypical setup:")
        print("1. Install MongoDB and start it")
        print("2. Install Python dependencies: pip install -r requirements.txt")
        print("3. Start Flask server: python run.py")

if __name__ == "__main__":
    main()