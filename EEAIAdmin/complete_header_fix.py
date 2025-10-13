#!/usr/bin/env python3
"""
Complete fix for floating header structure
"""

import os
import re

def complete_header_fix(filepath):
    """Fix incomplete header actions section"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        
        # Pattern to find incomplete header actions section
        pattern = r'(<!-- Header Actions -->\s*\n\s*<div class="header-actions">\s*\n\s*<div class="status-indicator-modern">\s*\n\s*<div class="status-dot"></div>\s*)\n\s*</div>\s*\n\s*</div>\s*\n\s*</div>'
        
        replacement = r'\1\n                    <span>System Online</span>\n                </div>\n                <a href="/ai-chat-pro" class="action-button">\n                    <i class="mdi mdi-plus"></i>\n                    <span>New Session</span>\n                </a>\n            </div>\n        </div>\n    </div>'
        
        content = re.sub(pattern, replacement, content)
        
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
        if complete_header_fix(filepath):
            print(f"Fixed: {filename}")
            fixed_count += 1
    
    print(f"\nCompleted! Fixed {fixed_count} templates.")

if __name__ == "__main__":
    main()