#!/usr/bin/env python3
"""
Fix duplicate content in header actions section
"""

import os
import re

def fix_header_duplicates(filepath):
    """Fix duplicate header actions content"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        
        # Fix duplicate content in header actions section
        # Pattern to match the duplicate content after </div>
        content = re.sub(
            r'(</div>\s*\n\s*<span>System Online</span>\s*\n\s*</div>\s*\n\s*<a[^>]*class="action-button"[^>]*>.*?</a>\s*\n\s*</div>)',
            '</div>',
            content,
            flags=re.DOTALL
        )
        
        # Another pattern for slightly different formatting
        content = re.sub(
            r'(</div>\s*\n+\s*<span>System Online</span>.*?</a>\s*\n\s*</div>\s*\n\s*</div>)',
            '</div>\n        </div>\n    </div>',
            content,
            flags=re.DOTALL
        )
        
        # Write the fixed content
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
        if fix_header_duplicates(filepath):
            print(f"Fixed: {filename}")
            fixed_count += 1
    
    print(f"\nCompleted! Fixed {fixed_count} templates.")

if __name__ == "__main__":
    main()