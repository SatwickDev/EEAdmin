#!/usr/bin/env python3
"""
Final verification of all templates
"""

import os
import re

def verify_template(filepath):
    """Verify template has correct structure"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        issues = []
        
        # Check 1: Verify floating header exists with complete structure
        if not re.search(r'<div class="floating-header">', content):
            issues.append("Missing floating header")
        
        # Check 2: Verify brand-info section exists
        if not re.search(r'<div class="brand-info">', content):
            issues.append("Missing brand-info section")
        
        # Check 3: Verify nav-pills section exists
        if not re.search(r'<nav class="nav-pills">', content):
            issues.append("Missing nav-pills section")
        
        # Check 4: Verify header-actions section exists
        if not re.search(r'<div class="header-actions">', content):
            issues.append("Missing header-actions section")
        
        # Check 5: Verify CSS imports in correct order
        css_order_correct = True
        css_imports = [
            'floating-header-unified.css',
            'Inter:wght',
            'unified-design.css',
            'app.css'
        ]
        
        last_pos = 0
        for css in css_imports:
            pos = content.find(css)
            if pos == -1:
                issues.append(f"Missing CSS: {css}")
                css_order_correct = False
            elif pos < last_pos:
                issues.append(f"CSS out of order: {css}")
                css_order_correct = False
            else:
                last_pos = pos
        
        # Check 6: Verify body has class="with-floating-header"
        if not re.search(r'<body[^>]*class="[^"]*with-floating-header[^"]*"', content):
            issues.append("Body missing 'with-floating-header' class")
        
        return filename, issues
        
    except Exception as e:
        return filename, [f"Error reading file: {str(e)}"]

def main():
    """Main function"""
    templates_dir = '/mnt/c/Users/AIAdmin/Desktop/EEAI/app/templates'
    
    # Get all HTML files
    html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
    
    print("=== FINAL TEMPLATE VERIFICATION ===\n")
    
    all_good = True
    for filename in sorted(html_files):
        filepath = os.path.join(templates_dir, filename)
        filename, issues = verify_template(filepath)
        
        if issues:
            all_good = False
            print(f"❌ {filename}:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"✅ {filename}: All checks passed")
    
    print("\n" + "="*50)
    if all_good:
        print("✅ ALL TEMPLATES HAVE CORRECT FLOATING HEADER STRUCTURE!")
    else:
        print("❌ Some templates still have issues")

if __name__ == "__main__":
    main()