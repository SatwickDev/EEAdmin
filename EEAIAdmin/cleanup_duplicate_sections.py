#!/usr/bin/env python3
"""
Clean up duplicate navigation and header actions sections after floating header
"""

import os
import re

def cleanup_duplicates(filepath):
    """Remove duplicate nav and header sections after the main floating header"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        
        # Pattern to find duplicate navigation pills section after the main floating header
        content = re.sub(
            r'(</div>\s*</div>\s*\n\s*<!-- Navigation Pills -->\s*\n\s*\n\s*<!-- Header Actions -->\s*.*?</div>)',
            '', 
            content, 
            flags=re.DOTALL
        )
        
        # Also clean up any standalone duplicate sections
        content = re.sub(
            r'(\n\s*<!-- Navigation Pills -->\s*\n\s*\n\s*<!-- Header Actions -->\s*<div class="header-actions">.*?</div>\s*(?=\n|<|$))',
            '',
            content,
            flags=re.DOTALL
        )
        
        # Write the cleaned content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"Error cleaning {filename}: {str(e)}")
        return False

def main():
    """Main function"""
    templates_dir = '/mnt/c/Users/AIAdmin/Desktop/EEAI/app/templates'
    
    # Get all HTML files
    html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
    
    cleaned_count = 0
    for filename in sorted(html_files):
        filepath = os.path.join(templates_dir, filename)
        if cleanup_duplicates(filepath):
            print(f"Cleaned: {filename}")
            cleaned_count += 1
    
    print(f"\nCompleted! Cleaned {cleaned_count} templates.")

if __name__ == "__main__":
    main()