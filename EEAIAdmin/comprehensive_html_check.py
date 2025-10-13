#!/usr/bin/env python3
"""
Comprehensive check for all HTML templates
"""

import os
import re
from collections import defaultdict

def check_template(filepath):
    """Check a single template for issues"""
    issues = []
    filename = os.path.basename(filepath)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Check for multiple floating headers
        header_count = content.count('<div class="floating-header">')
        if header_count > 1:
            issues.append(f"Multiple floating headers found: {header_count}")
        elif header_count == 0:
            issues.append("No floating header found")
        
        # 2. Check for duplicate navigation sections
        nav_count = content.count('<nav class="nav-pills">')
        if nav_count > 1:
            issues.append(f"Multiple navigation sections found: {nav_count}")
        
        # 3. Check for duplicate brand-info sections
        brand_count = content.count('<div class="brand-info">')
        if brand_count > 1:
            issues.append(f"Multiple brand-info sections found: {brand_count}")
        
        # 4. Check CSS order
        css_files = re.findall(r'<link[^>]*href="([^"]+\.css[^"]*)"[^>]*>', content)
        css_order = []
        for css in css_files:
            if 'tailwind' in css:
                css_order.append('tailwind')
            elif 'mdi' in css or 'materialdesignicons' in css:
                css_order.append('mdi')
            elif 'floating-header-unified' in css:
                css_order.append('floating-header')
            elif 'vuetify' in css:
                css_order.append('vuetify')
            elif 'Inter' in css:
                css_order.append('inter-font')
            elif 'unified-design' in css:
                css_order.append('unified-design')
            elif 'app.css' in css:
                css_order.append('app-css')
        
        expected_order = ['mdi', 'floating-header', 'vuetify', 'inter-font', 'unified-design', 'app-css']
        
        # Check if all required CSS are present
        missing_css = []
        for expected in expected_order:
            if expected not in css_order:
                missing_css.append(expected)
        
        if missing_css:
            issues.append(f"Missing CSS: {', '.join(missing_css)}")
        
        # 5. Check for inline CSS that might conflict
        style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
        for style in style_blocks:
            if '.floating-header' in style:
                issues.append("Inline CSS defining .floating-header (conflicts with unified CSS)")
            if '.nav-pills' in style:
                issues.append("Inline CSS defining .nav-pills (conflicts with unified CSS)")
            if '.brand-' in style:
                issues.append("Inline CSS defining brand styles (conflicts with unified CSS)")
        
        # 6. Check body tag
        body_match = re.search(r'<body([^>]*)>', content)
        if body_match:
            body_tag = body_match.group(0)
            if 'with-floating-header' not in body_tag:
                issues.append("Body missing 'with-floating-header' class")
            
            # Check for duplicate class attributes
            if body_tag.count('class=') > 1:
                issues.append("Body has multiple class attributes")
        
        # 7. Check for proper padding
        if 'padding-top' not in content and 'pt-' not in content:
            issues.append("No padding-top found for floating header spacing")
        
        # 8. Check for broken HTML structure
        if content.count('<div') != content.count('</div>'):
            issues.append("Mismatched div tags")
        
        # 9. Check for "No newline at end of file" markers
        if 'No newline at end of file' in content:
            issues.append("Contains 'No newline at end of file' text")
        
        return filename, issues
        
    except Exception as e:
        return filename, [f"Error reading file: {str(e)}"]

def main():
    """Main function"""
    templates_dir = '/mnt/c/Users/AIAdmin/Desktop/EEAI/app/templates'
    
    # Get all HTML files
    html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
    
    print("=== COMPREHENSIVE HTML TEMPLATE CHECK ===\n")
    
    issues_found = False
    for filename in sorted(html_files):
        filepath = os.path.join(templates_dir, filename)
        name, issues = check_template(filepath)
        
        if issues:
            issues_found = True
            print(f"\n❌ {name}:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"✅ {name}: OK")
    
    if not issues_found:
        print("\n✅ All templates are properly configured!")
    else:
        print("\n❌ Issues found in templates above")

if __name__ == "__main__":
    main()