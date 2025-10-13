#!/usr/bin/env python
"""Script to add smart capture and chatbot features to cash_management_form.html"""

# The changes to be made:
# 1. Add smart capture CSS styles
# 2. Add smart capture section HTML after form header
# 3. Add chatbot icon and overlay HTML before closing body
# 4. Add JavaScript functions for smart capture and chatbot

print("""
MANUAL CHANGES NEEDED FOR cash_management_form.html:

1. ADD AFTER LINE 8 (after <title> tag), add MDI icons:
   <link href="https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/css/materialdesignicons.min.css" rel="stylesheet">

2. ADD SMART CAPTURE SECTION after the form header (around line 406):
   After:
            <div class="form-header">
                <h1><i class="fas fa-wallet"></i> Cash Management</h1>
                <p>Liquidity Management, Cash Flow, and Payment Processing</p>
            </div>
   
   Add:
            <!-- Smart Capture Section -->
            <div class="smart-capture-section">
                <div class="smart-capture-info">
                    <div class="smart-capture-icon">
                        <i class="mdi mdi-scan-helper"></i>
                    </div>
                    <div class="smart-capture-text">
                        <h3>Smart Document Capture</h3>
                        <p>Upload and extract cash management information from documents automatically</p>
                    </div>
                </div>
                <button type="button" class="btn btn-smart-capture" onclick="openSmartCapture()">
                    <i class="mdi mdi-scan-helper"></i> 
                    <span>Start Smart Capture</span>
                </button>
            </div>

3. ADD HTML BEFORE </body> tag (around line 1186):
   
    <!-- Smart Capture Modal -->
    <div id="smartCaptureModal" class="smart-capture-modal">
        <div class="smart-capture-iframe-container">
            <div class="smart-capture-header">
                <div class="smart-capture-header-title">
                    <i class="mdi mdi-scan-helper"></i>
                    <div>
                        <h3>Smart Document Capture</h3>
                        <div class="smart-capture-header-subtitle">Upload and extract data from your cash management documents</div>
                    </div>
                </div>
                <button class="smart-capture-close" onclick="closeSmartCapture()" title="Close">
                    <i class="mdi mdi-close"></i>
                </button>
            </div>
            <div class="smart-capture-loading">
                <div class="smart-capture-spinner"></div>
                <div class="smart-capture-loading-text">Loading Smart Capture...</div>
            </div>
            <iframe id="smartCaptureIframe" class="smart-capture-iframe" src="" onload="hideSmartCaptureLoading()"></iframe>
        </div>
    </div>
    
    <!-- Chatbot Icon -->
    <div class="chatbot-icon" onclick="openChatbot()">
        <i class="fas fa-comments"></i>
    </div>
    
    <!-- Chatbot Overlay -->
    <div id="chatbotOverlay" class="chatbot-overlay" onclick="closeChatbotOnOverlay(event)">
        <div id="chatbotWindow" class="chatbot-window" onclick="event.stopPropagation()">
            <div class="chatbot-header" id="chatbotHeader">
                <div class="chatbot-header-left">
                    <i class="fas fa-robot"></i>
                    <div>
                        <h3>AI Assistant - Cash Management</h3>
                        <div class="chatbot-status">
                            <span class="status-dot"></span>
                            <span>Online</span>
                        </div>
                    </div>
                </div>
                <div class="chatbot-controls">
                    <button class="chatbot-control-btn" onclick="minimizeChatbot()" title="Minimize">
                        <i class="fas fa-minus"></i>
                    </button>
                    <button class="chatbot-control-btn" onclick="maximizeChatbot()" title="Maximize">
                        <i class="fas fa-expand"></i>
                    </button>
                    <button class="chatbot-control-btn" onclick="closeChatbot()" title="Close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="chatbot-body">
                <iframe id="chatbotFrame" class="chatbot-iframe" src=""></iframe>
            </div>
        </div>
    </div>
""")