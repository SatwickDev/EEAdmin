#!/usr/bin/env python3
"""
Final comprehensive fix for all floating headers
"""

import os
import re

# Complete floating header template
COMPLETE_FLOATING_HEADER = '''    <!-- Unified Floating Header -->
    <div class="floating-header">
        <div class="floating-header-content">
            <!-- Brand Section -->
            <div class="brand-section">
                <div class="logo-container">
                    <div class="modern-logo">
                        <svg width="28" height="28" viewBox="0 0 48 48">
                            <defs>
                                <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" style="stop-color:#6366f1"/>
                                    <stop offset="50%" style="stop-color:#8b5cf6"/>
                                    <stop offset="100%" style="stop-color:#06b6d4"/>
                                </linearGradient>
                            </defs>
                            <g fill="url(#logoGradient)">
                                <rect x="8" y="8" width="8" height="32" rx="3"/>
                                <rect x="8" y="8" width="24" height="8" rx="3"/>
                                <rect x="8" y="20" width="20" height="8" rx="3"/>
                            </g>
                            <g fill="url(#logoGradient)" opacity="0.6">
                                <rect x="20" y="32" width="20" height="2" rx="1"/>
                                <rect x="20" y="36" width="20" height="2" rx="1"/>
                            </g>
                        </svg>
                        <div class="status-pulse"></div>
                    </div>
                </div>
                <div class="brand-info">
                    <h1 class="brand-title">Finstack</h1>
                    <p class="brand-subtitle">Innovation Partners for the Future of Finance</p>
                </div>
            </div>

            <!-- Navigation Pills -->
            <nav class="nav-pills">
                <a href="/" class="nav-pill {active_dashboard}">
                    <i class="mdi mdi-view-dashboard"></i>
                    <span>Dashboard</span>
                </a>
                <a href="/analytics" class="nav-pill {active_analytics}">
                    <i class="mdi mdi-chart-line"></i>
                    <span>Analytics</span>
                </a>
                <a href="/ai-chat-pro" class="nav-pill {active_ai_chat}">
                    <i class="mdi mdi-robot"></i>
                    <span>AI Chat</span>
                </a>
                <a href="/compliance-results" class="nav-pill {active_compliance}">
                    <i class="mdi mdi-shield-check"></i>
                    <span>Vetting</span>
                </a>
                <a href="/document-classification" class="nav-pill {active_documents}">
                    <i class="mdi mdi-file-document-multiple"></i>
                    <span>Documents</span>
                </a>
            </nav>

            <!-- Header Actions -->
            <div class="header-actions">
                <div class="status-indicator-modern">
                    <div class="status-dot"></div>
                    <span>System Online</span>
                </div>
                <a href="/ai-chat-pro" class="action-button">
                    <i class="mdi mdi-plus"></i>
                    <span>New Session</span>
                </a>
            </div>
        </div>
    </div>'''

def get_active_nav(filename):
    """Determine which nav item should be active based on filename"""
    active_map = {
        'analytics': ['analytics_improved.html', 'analytics_new.html'],
        'ai_chat': ['ai_chat.html', 'ai_chat_pro.html', 'ai_chat_modern.html', 'ai_chat - Copy.html',
                   'chat.html', 'clean_chat.html', 'enhanced_chat.html', 'enhanced_chat_complete.html', 
                   'smart_chat.html'],
        'compliance': ['compliance_checker.html', 'compliance_results.html', 'doccheck.html'],
        'documents': ['document_classification.html', 'document_classification_ai.html', 
                     'document_classification_modern.html', 'document_upload.html',
                     'document_classification - Copy.html', 'document_classification_backup.html'],
        'dashboard': ['index.html', 'richold.html', 'chromadb_status.html', 'rich.html', 'websiteIndex.html']
    }
    
    for nav, files in active_map.items():
        if filename in files:
            return nav
    return 'dashboard'

def fix_template_final(filepath):
    """Final fix for template"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        
        # 1. Remove ALL existing floating header content
        # Pattern to match the entire floating header section
        content = re.sub(r'<!-- Unified Floating Header -->.*?</div>\s*</div>\s*(?:</div>\s*)?', '', content, flags=re.DOTALL)
        
        # Also remove any partial headers
        content = re.sub(r'<div class="floating-header">.*?(?=<(?:div|script|main|section|body))', '', content, flags=re.DOTALL)
        
        # 2. Get the correct active nav
        active_nav = get_active_nav(filename)
        header_html = COMPLETE_FLOATING_HEADER
        header_html = header_html.replace('{active_dashboard}', 'active' if active_nav == 'dashboard' else '')
        header_html = header_html.replace('{active_analytics}', 'active' if active_nav == 'analytics' else '')
        header_html = header_html.replace('{active_ai_chat}', 'active' if active_nav == 'ai_chat' else '')
        header_html = header_html.replace('{active_compliance}', 'active' if active_nav == 'compliance' else '')
        header_html = header_html.replace('{active_documents}', 'active' if active_nav == 'documents' else '')
        
        # 3. Insert the complete header after body tag
        body_match = re.search(r'(<body[^>]*>)', content)
        if body_match:
            insert_pos = body_match.end()
            content = content[:insert_pos] + '\n' + header_html + '\n' + content[insert_pos:]
        
        # 4. Remove "No newline at end of file" text
        content = re.sub(r'No newline at end of file', '', content)
        
        # 5. Ensure file ends properly
        content = content.rstrip() + '\n</html>' if not content.rstrip().endswith('</html>') else content
        
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
        if fix_template_final(filepath):
            print(f"Fixed: {filename}")
            fixed_count += 1
    
    print(f"\nCompleted! Fixed {fixed_count} templates.")

if __name__ == "__main__":
    main()