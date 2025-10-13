#!/usr/bin/env python3
"""
Fix all template issues comprehensively
"""

import os
import re

def fix_template(filepath):
    """Fix all issues in a template"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        filename = os.path.basename(filepath)
        
        # 1. Remove all duplicate navigation and brand sections
        # Find the main floating header
        main_header_match = re.search(r'<!-- Unified Floating Header -->.*?</div>\s*</div>\s*</div>', content, re.DOTALL)
        if main_header_match:
            main_header = main_header_match.group(0)
            # Remove all other nav-pills and brand-info that are outside the main header
            content_after_header = content[main_header_match.end():]
            
            # Remove duplicate nav-pills
            content_after_header = re.sub(r'<nav class="nav-pills">.*?</nav>', '', content_after_header, flags=re.DOTALL)
            # Remove duplicate brand-info
            content_after_header = re.sub(r'<div class="brand-info">.*?</div>\s*</div>', '', content_after_header, flags=re.DOTALL)
            
            content = content[:main_header_match.end()] + content_after_header
        
        # 2. Fix CSS order - ensure Inter font is included
        if 'fonts.googleapis.com' not in content or 'Inter' not in content:
            # Add Inter font after vuetify
            vuetify_pos = content.find('vuetify.min.css')
            if vuetify_pos > 0:
                end_of_line = content.find('\n', vuetify_pos)
                if end_of_line > 0:
                    content = content[:end_of_line] + '\n  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">' + content[end_of_line:]
        
        # 3. Remove inline CSS that conflicts with floating-header-unified.css
        # Remove style blocks that define floating-header styles
        content = re.sub(r'<style[^>]*>.*?\.floating-header\s*\{[^}]*\}.*?</style>', '', content, flags=re.DOTALL)
        
        # 4. Fix body tag issues
        # Remove duplicate class attributes
        body_match = re.search(r'<body[^>]*>', content)
        if body_match:
            body_tag = body_match.group(0)
            # Count class attributes
            class_count = body_tag.count('class=')
            if class_count > 1:
                # Extract all classes
                classes = []
                for match in re.finditer(r'class="([^"]*)"', body_tag):
                    classes.extend(match.group(1).split())
                # Remove duplicates and ensure with-floating-header is included
                unique_classes = list(set(classes))
                if 'with-floating-header' not in unique_classes:
                    unique_classes.append('with-floating-header')
                # Build new body tag
                other_attrs = re.sub(r'class="[^"]*"', '', body_tag).strip('<> ')
                new_body_tag = f'<body class="{" ".join(unique_classes)}"'
                if other_attrs:
                    new_body_tag += ' ' + other_attrs
                new_body_tag += '>'
                content = content.replace(body_tag, new_body_tag)
        
        # 5. Add padding-top style if missing
        if 'padding-top' not in content and 'pt-' not in content:
            # Add style before </head>
            style_block = '''  <style>
    body {
      padding-top: 100px;
    }
    @media (max-width: 768px) {
      body {
        padding-top: 80px;
      }
    }
  </style>
'''
            content = content.replace('</head>', style_block + '</head>')
        
        # 6. Remove "No newline at end of file" text
        content = content.replace('No newline at end of file', '')
        
        # 7. Ensure proper closing tags
        # This is a simple fix - just ensure content ends with proper HTML closing
        if not content.strip().endswith('</html>'):
            content = content.strip() + '\n</html>'
        
        # Write only if changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing {os.path.basename(filepath)}: {str(e)}")
        return False

def main():
    """Main function"""
    templates_dir = '/mnt/c/Users/AIAdmin/Desktop/EEAI/app/templates'
    
    # Get all HTML files
    html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
    
    fixed_count = 0
    for filename in sorted(html_files):
        filepath = os.path.join(templates_dir, filename)
        if fix_template(filepath):
            print(f"Fixed: {filename}")
            fixed_count += 1
        else:
            print(f"No changes: {filename}")
    
    print(f"\nCompleted! Fixed {fixed_count} templates.")

if __name__ == "__main__":
    main()