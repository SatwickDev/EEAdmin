#!/usr/bin/env python3
"""
Add Inter font import to all templates that are missing it
"""

import os
import re

def add_inter_font(filepath):
    """Add Inter font import after floating-header-unified.css"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        
        # Check if Inter font is already imported
        if 'fonts.googleapis.com/css2?family=Inter' in content:
            return False
        
        # Find the floating-header-unified.css link and add Inter font after it
        # Try different patterns for the floating-header CSS link
        patterns = [
            r'(<link href="{{ url_for\(\'static\', filename=\'css/floating-header-unified\.css\'\) }}" rel="stylesheet">)',
            r'(<link\s+href="{{ url_for\(\'static\',\s*filename=\'css/floating-header-unified\.css\'\) }}"\s+rel="stylesheet">)',
            r'(<link\s+rel="stylesheet"\s+href="{{ url_for\(\'static\',\s*filename=\'css/floating-header-unified\.css\'\) }}">)'
        ]
        
        inter_font_link = '\n  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">'
        
        # Try each pattern
        updated = False
        for pattern in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, r'\1' + inter_font_link, content)
                updated = True
                break
        
        # If none of the patterns matched, try to add it after vuetify CSS
        if not updated and 'vuetify' in content:
            pattern = r'(<link[^>]*vuetify[^>]*>)'
            content = re.sub(pattern, r'\1' + inter_font_link, content)
            updated = True
        
        if not updated:
            return False
        
        # Write the updated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"Error fixing {filename}: {str(e)}")
        return False

def main():
    """Main function"""
    templates_dir = '/mnt/c/Users/AIAdmin/Desktop/EEAI/app/templates'
    
    # Get all HTML files
    html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
    
    fixed_count = 0
    for filename in sorted(html_files):
        filepath = os.path.join(templates_dir, filename)
        if add_inter_font(filepath):
            print(f"Added Inter font to: {filename}")
            fixed_count += 1
    
    print(f"\nCompleted! Added Inter font to {fixed_count} templates.")

if __name__ == "__main__":
    main()