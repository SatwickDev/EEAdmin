const { createApp, ref, reactive, onMounted, watch, nextTick, onUnmounted } = window.Vue;
const { createVuetify } = window.Vuetify;

const vuetify = createVuetify({
  theme: {
    defaultTheme: "light",
    themes: {
      light: {
        dark: false,
        colors: {
          primary: "#667eea",
          secondary: "#764ba2",
          accent: "#82B1FF",
          error: "#FF5252",
          info: "#2196F3",
          success: "#4CAF50",
          warning: "#FB8C00",
          background: "#FFFFFF",
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: "#667eea",
          secondary: "#764ba2",
          accent: "#FF4081",
          error: "#FF5252",
          info: "#2196F3",
          success: "#4CAF50",
          warning: "#FB8C00",
          background: "#121212",
        },
      },
    },
  },
});

const USER_AVATAR = "https://randomuser.me/api/portraits/women/68.jpg";
const BOT_AVATAR = "https://img.icons8.com/color/48/000000/artificial-intelligence.png";

function getTime(ts = new Date()) {
  if (!ts) return "";
  if (!(ts instanceof Date)) ts = new Date(ts);
  if (isNaN(ts.getTime())) return "";
  return ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = (e) => reject(e);
    reader.readAsDataURL(file);
  });
}

async function handleFilePreview(file) {
  if (!file) return null;
  try {
    if (file.type.startsWith("image/")) {
      return await fileToDataUrl(file);
    } else if (file.type === "application/pdf") {
      return URL.createObjectURL(file);
    } else {
      console.warn("Unsupported file type:", file.type);
      return null;
    }
  } catch (error) {
    console.error("Error creating file preview:", error);
    return null;
  }
}

const App = {
  components: {
    PdfReviewDialog: window.PdfReviewDialog,
    ImagePageViewer: window.ImagePageViewer,
  },
  setup() {
    const chatMessages = ref([]);
    const input = ref("");
    const isDark = ref(false);
    const isMaximized = ref(false);
    const loading = ref(false);
    const chatRef = ref(null);
    const file = ref(null);
    const filePreview = ref(null);
    const fileInputKey = ref(0);
    const pdfDialogOpen = ref(false);
    const pdfUrl = ref("");
    const pdfAnalysis = reactive({});
    const pdfFileName = ref("");
    const annotatedImage = ref([]);
    const selectedCategory = ref("");
    const selectedDocumentType = ref("");
    const isRecording = ref(false);
    const uploadProgress = ref(0);
    const toast = ref({ show: false, text: "", color: "success" });
    const isTyping = ref(false);
    const showQuickActions = ref(false);
    const dragover = ref(false);
    let recognition;
    let synth = window.speechSynthesis;

    // Enhanced quick action suggestions with better icons
    const quickActions = ref([
      { text: "Analyze document", icon: "mdi-file-document-check", color: "primary", gradient: "from-blue-500 to-purple-600" },
      { text: "Generate report", icon: "mdi-chart-timeline-variant", color: "success", gradient: "from-green-500 to-teal-600" },
      { text: "Check compliance", icon: "mdi-shield-check-outline", color: "warning", gradient: "from-orange-500 to-red-600" },
      { text: "Export data", icon: "mdi-database-export", color: "info", gradient: "from-cyan-500 to-blue-600" }
    ]);

    // Download format options with icons
    const downloadFormats = ref([
      { value: 'excel', label: 'Excel', icon: 'mdi-file-excel', color: '#10B981' },
      { value: 'json', label: 'JSON', icon: 'mdi-code-json', color: '#6366F1' },
      { value: 'pdf', label: 'PDF', icon: 'mdi-file-pdf-box', color: '#EF4444' },
      { value: 'csv', label: 'CSV', icon: 'mdi-file-table', color: '#F59E0B' }
    ]);

    onMounted(async () => {
      try {
        const res = await fetch("/history?user_id=" + getUserId());
        if (res.status === 401) {
          window.location.reload();
          return;
        }
        const data = await res.json();
        if (Array.isArray(data.conversation_history) && data.conversation_history.length) {
          chatMessages.value = data.conversation_history.map((msg) => ({
            sender: msg.role === "user" ? "user" : "bot",
            text: msg.message,
            timestamp: new Date(msg.created_at),
            html: /<[a-z][\s\S]*>/i.test(msg.message),
            fileData: msg.file_data || null,
          }));
        } else {
          chatMessages.value = [{
            sender: "bot",
            text: "👋 Welcome to ilyas! I'm your intelligent assistant ready to help with document analysis, compliance checking, and more. How can I assist you today?",
            timestamp: new Date(),
            html: false,
          }];
        }
      } catch (e) {
        console.error("Failed to load chat history:", e);
        chatMessages.value = [{
          sender: "bot",
          text: "👋 Welcome to Fin AI! I'm your intelligent assistant ready to help with document analysis, compliance checking, and more. How can I assist you today?",
          timestamp: new Date(),
          html: false,
        }];
      }
    });

    onUnmounted(() => {
      if (filePreview.value && filePreview.value.startsWith("blob:")) {
        URL.revokeObjectURL(filePreview.value);
      }
    });

    watch(chatMessages, () => {
      nextTick(() => scrollToBottom());
    });

    watch(isDark, (newVal) => {
      vuetify.theme.global.name.value = newVal ? "dark" : "light";
      document.body.classList.toggle("dark", newVal);
      document.body.classList.toggle("bg-gray-900", newVal);
    });

    function scrollToBottom() {
      if (chatRef.value) {
        chatRef.value.scrollTop = chatRef.value.scrollHeight;
      }
    }

    function startRecording() {
      if (!("webkitSpeechRecognition" in window)) {
        showToast("Voice recognition not supported in your browser.", "error");
        return;
      }
      if (isRecording.value && recognition) {
        recognition.stop();
        return;
      }
      recognition = new webkitSpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-US";
      isRecording.value = true;
      recognition.onresult = (e) => {
        input.value = e.results[0][0].transcript;
        isRecording.value = false;
      };
      recognition.onerror = () => {
        isRecording.value = false;
        showToast("Voice recognition error", "error");
      };
      recognition.onend = () => (isRecording.value = false);
      recognition.start();
    }

    async function logout() {
      try {
        const response = await fetch("/auth/logout", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });
        if (!response.ok) throw new Error("Logout failed");
        localStorage.removeItem("user_id");
        showToast("Logged out successfully", "success");
        window.location.href = '/';
      } catch (error) {
        showToast("Logout failed", "error");
      }
    }

    function simulateTyping() {
      isTyping.value = true;
      setTimeout(() => {
        isTyping.value = false;
      }, 1500);
    }

    function getUserId() {
      const user = localStorage.getItem("user_data");
      if (!user) return null;
      try {
        const parsed = JSON.parse(user);
        return parsed.id || null;
      } catch {
        return null;
      }
    }

    async function sendMessage() {
      if (!input.value.trim() && !file.value) return;

      // Initialize progress loader variable for scope
      let progressLoader = null;

      showQuickActions.value = false;

      if (input.value.trim()) {
        chatMessages.value.push({
          sender: "user",
          text: input.value,
          timestamp: new Date(),
        });
      }

      if (file.value) {
        chatMessages.value.push({
          sender: "user",
          file: {
            name: file.value.name,
            type: file.value.type,
            url: filePreview.value,
          },
          text: file.value.name,
          timestamp: new Date(),
        });
      }

      loading.value = true;
      simulateTyping();
      let response;

      try {
        if (file.value) {
          console.log("Uploading file:", file.value.name, file.value.type, file.value.size);
          const formData = new FormData();
          formData.append("query", input.value || "");
          formData.append("user_id", getUserId());
          formData.append("productname", "EE");
          formData.append("functionname", "register_import_lc");
          formData.append("SCF", "false");
          formData.append("file", file.value);
          
          // Add client_id for progress tracking if WebSocket is available
          if (window.aiWebSocket && window.aiWebSocket.clientId) {
            formData.append("client_id", window.aiWebSocket.clientId);
            console.log("📊 Added client_id for progress tracking:", window.aiWebSocket.clientId);
          }

          // Show progress loader if WebSocket is available
          if (window.aiWebSocket && window.ProgressLoader) {
            progressLoader = new window.ProgressLoader({
              wsClient: window.aiWebSocket,
              onComplete: () => {
                console.log("✅ Progress completed!");
              },
              onError: (error) => {
                console.error("❌ Progress error:", error);
              }
            });
            progressLoader.show();
          }

          const res = await fetch("/query", {
            method: "POST",
            body: formData,
          });

          if (res.status === 401) {
            window.location.reload();
            return;
          }

          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          }

          const responseText = await res.text();
          // Log full parsed JSON info instead of truncated string
          try {
            const parsed = JSON.parse(responseText);
            console.log("✅ Full parsed response:", parsed);

            // Correct path: parsed.response[0].page_classifications[0]
            const category =
              parsed.response?.[0]?.page_classifications?.[0]?.category || 'N/A';
            const documentType =
              parsed.response?.[0]?.page_classifications?.[0]?.document_type || 'N/A';

            console.log("📁 Category:", category);
            console.log("📄 Document Type:", documentType);

            response = parsed;

          } catch (parseError) {
            console.error("❌ Failed to parse JSON response:", parseError, responseText);
            throw new Error("Invalid JSON response from server");
          }

          console.log("Parsed response:", response);

          if (file.value.type.endsWith("pdf") && response.analysis_result) {
            pdfUrl.value = filePreview.value;
            Object.assign(pdfAnalysis, response.analysis_result);
            pdfFileName.value = file.value.name;
            
            // Add page_classifications to pdfAnalysis if it exists in the response
            if (response.response?.[0]?.page_classifications) {
              pdfAnalysis.page_classifications = response.response[0].page_classifications;
            }
            
            // Extract category and document type from the correct location
            const category = response.response?.[0]?.page_classifications?.[0]?.category || 'N/A';
            const document_type = response.response?.[0]?.page_classifications?.[0]?.document_type || 'N/A';

            console.log("Category Type:", category);
            console.log("Document Type:", document_type);
            
            selectedCategory.value = category;
            selectedDocumentType.value = document_type;
            
            // Handle annotated image
            if (response.annotated_image && Array.isArray(response.annotated_image)) {
              // FIXED: Convert all base64 to data URLs
              annotatedImage.value = response.annotated_image.map(img =>
                img.startsWith('data:image/') ? img : "data:image/jpeg;base64," + img
              );
            } else {
              annotatedImage.value = [];
            }
            
            pdfDialogOpen.value = true;
            
            // Ensure pdfAnalysis includes page_classifications
            const analysisWithClassifications = {
              ...response.analysis_result,
              page_classifications: pdfAnalysis.page_classifications || []
            };
            
            console.log("Creating chat message with analysis:", analysisWithClassifications);
            console.log("Page classifications:", analysisWithClassifications.page_classifications);
            
            chatMessages.value.push({
              sender: "bot",
              text: `PDF "${file.value.name}" processed successfully. Click to review.`,
              timestamp: new Date(),
              fileData: {
                pdfUrl: filePreview.value,
                pdfAnalysis: analysisWithClassifications,
                annotatedImage: annotatedImage.value,
                fileName: file.value.name,
                category: selectedCategory.value,
                document_type: selectedDocumentType.value,
              },
            });
            removeFile();
            loading.value = false;
            input.value = "";
            return;
          }

          removeFile();
        } else {
          const res = await fetch("/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              query: input.value,
              user_id: getUserId(),
              productname: "EE",
              functionname: "register_import_lc",
              SCF: false,
            }),
          });

          if (res.status === 401) {
            window.location.reload();
            return;
          }

          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          }

          // Check if response is an image (for visualization requests)
          const contentType = res.headers.get('content-type');
          if (contentType && contentType.includes('image')) {
            const blob = await res.blob();
            const imageUrl = URL.createObjectURL(blob);
            chatMessages.value.push({
              sender: "bot",
              text: "📊 Here's your visualization:",
              image: imageUrl,
              timestamp: new Date(),
            });
            loading.value = false;
            isTyping.value = false;
            input.value = "";
            return;
          }

          response = await res.json();
        }
        handleBackendResponse(response);
      } catch (err) {
        console.error("Detailed error sending message:", {
          error: err,
          message: err.message,
          stack: err.stack,
          type: err.name,
        });

        let errorMessage = "⚠️ I'm having trouble connecting right now. Please try again in a moment.";
        if (err.message.includes("fetch")) {
          errorMessage += " Check your internet connection.";
        } else if (err.message.includes("JSON")) {
          errorMessage += " There was a data formatting issue.";
        }

        chatMessages.value.push({
          sender: "bot",
          text: errorMessage,
          timestamp: new Date(),
          html: false,
        });
        showToast(`Error: ${err.message}`, "error");
      } finally {
        // Hide progress loader if it was shown
        if (progressLoader) {
          progressLoader.hide();
        }
        loading.value = false;
        isTyping.value = false;
        input.value = "";
      }
    }

    function handleBackendResponse(data) {
      console.log("BACKEND RESPONSE:", data);

      // Handle array responses
      if (Array.isArray(data)) data = data[0];

      // Handle the specific structure from your backend
      if (data.intent && data.intent.toLowerCase().includes("file upload") &&
          data.response && Array.isArray(data.response) && data.response.length > 0) {

        const responseData = data.response[0];
        console.log("Processing file upload response:", responseData);

        if (responseData.analysis_result) {
          Object.assign(pdfAnalysis, {
            ...responseData.analysis_result,
            page_classifications: responseData.page_classifications
          });
          pdfFileName.value = responseData.file_name || "Document";
          console.log("pdfAnalysis value:", JSON.stringify(pdfAnalysis, null, 2));
          console.log("Category Type:", pdfAnalysis.page_classifications?.[0]?.category);

          // Extract category and document type
          selectedCategory.value = responseData.page_classifications?.[0]?.category || "N/A";
          selectedDocumentType.value = responseData.page_classifications?.[0]?.document_type || "N/A";

          // Handle annotated image - your backend sends it in the response array
          if (responseData.annotated_image && Array.isArray(responseData.annotated_image) && responseData.annotated_image.length > 0) {
            const imageData = responseData.annotated_image[0];
            console.log("Annotated image data received:", imageData.substring(0, 50) + "...");

            // Check if it's valid base64 (remove data URL validation as your backend sends raw base64)
            if (imageData && typeof imageData === 'string' && imageData.length > 0) {
              // Add data URL prefix if not present
              annotatedImage.value = responseData.annotated_image.map(img =>
                img.startsWith('data:image/') ? img : "data:image/jpeg;base64," + img
              );
              console.log("Annotated image processed successfully");
            } else {
              console.warn('Invalid annotated image data received');
              annotatedImage.value = [];
            }
          } else {
            console.log("No annotated image in response");
            annotatedImage.value = [];
          }

          // Also check if we need to add PDF pages for the original image
          if (responseData.analysis_result.pdf_pages) {
            console.log("PDF pages found in analysis result");
          }

          pdfDialogOpen.value = true;
          chatMessages.value.push({
            sender: "bot",
            text: `PDF "${responseData.file_name || 'document'}" processed successfully. Click to review the analysis.`,
            timestamp: new Date(),
            fileData: {
              pdfUrl: filePreview.value || pdfUrl.value,
              pdfAnalysis: responseData.analysis_result,
              annotatedImage: annotatedImage.value,
              fileName: responseData.file_name || "Document",
              category: selectedCategory.value,
              document_type: selectedDocumentType.value,
            },
          });
          return;
        }
      }

      // Fallback: Handle direct analysis result (in case of different response structure)
      if (data && (data.analysis_result || data.annotated_image)) {
        Object.assign(pdfAnalysis, data.analysis_result);

        if (data.annotated_image && Array.isArray(data.annotated_image) && data.annotated_image.length > 0) {
          const imageData = data.annotated_image[0];
          if (imageData && typeof imageData === 'string' && imageData.length > 0) {
            annotatedImage.value = data.annotated_image.map(img => 
              img.startsWith('data:image/') ? img : "data:image/jpeg;base64," + img
            );
          } else {
            annotatedImage.value = [];
          }
        } else {
          annotatedImage.value = [];
        }

        pdfFileName.value = data.file_name || "Document";
        selectedCategory.value = data.page_classifications?.[0]?.category || "N/A";
        selectedDocumentType.value = data.page_classifications?.[0]?.document_type || "N/A";
        pdfDialogOpen.value = true;
        chatMessages.value.push({
          sender: "bot",
          text: `PDF "${data.file_name || 'document'}" processed. Click to review.`,
          timestamp: new Date(),
          fileData: {
            pdfUrl: pdfUrl.value,
            pdfAnalysis: data.analysis_result,
            annotatedImage: annotatedImage.value,
            fileName: data.file_name || "Document",
            category: selectedCategory.value,
            document_type: selectedDocumentType.value,
          },
        });
        return;
      }

      if (data.intent?.toLowerCase().includes("table") && data.response?.table) {
        chatMessages.value.push({
          sender: "bot",
          table: data.response.table,
          timestamp: new Date(),
        });
        return;
      }

      if (data.intent?.toLowerCase().includes("visualization") && data.chart) {
        chatMessages.value.push({
          sender: "bot",
          chart: data.chart,
          timestamp: new Date(),
        });
        return;
      }

      if (data.result && /<[a-z][\s\S]*>/i.test(data.result)) {
        chatMessages.value.push({
          sender: "bot",
          text: data.result,
          timestamp: new Date(),
          html: true,
        });
        return;
      }

      if (data.response && typeof data.response === "string") {
        chatMessages.value.push({
          sender: "bot",
          text: data.response,
          timestamp: new Date(),
          html: /<[a-z][\s\S]*>/i.test(data.response),
        });
        return;
      }

      console.warn("Unhandled response structure:", data);
      chatMessages.value.push({
        sender: "bot",
        text: `🔍 Here's the detailed response:\n\n${JSON.stringify(data, null, 2)}`,
        timestamp: new Date(),
        html: false,
      });
    }

    function openPdfDialog(msg) {
      if (msg.fileData) {
        console.log("Opening PDF Dialog with fileData:", msg.fileData);
        console.log("pdfAnalysis page_classifications:", msg.fileData.pdfAnalysis?.page_classifications);
        
        pdfUrl.value = msg.fileData.pdfUrl;
        Object.assign(pdfAnalysis, JSON.parse(JSON.stringify(msg.fileData.pdfAnalysis)));
        // Ensure annotatedImage is an array
        annotatedImage.value = Array.isArray(msg.fileData.annotatedImage) ? msg.fileData.annotatedImage : [];
        pdfFileName.value = msg.fileData.fileName;
        selectedCategory.value = msg.fileData.category || "N/A";
        selectedDocumentType.value = msg.fileData.document_type || "N/A";
        pdfDialogOpen.value = true;
      }
    }

    function handleDragOver(e) {
      e.preventDefault();
      dragover.value = true;
    }

    function handleDragEnter(e) {
      e.preventDefault();
      dragover.value = true;
    }

    function handleDragLeave(e) {
      e.preventDefault();
      // Only set dragover to false if we're leaving the drop zone itself
      if (!e.currentTarget.contains(e.relatedTarget)) {
        dragover.value = false;
      }
    }

    async function handleDrop(e) {
      e.preventDefault();
      dragover.value = false;
      
      const files = e.dataTransfer.files;
      if (!files.length) return;
      
      const selectedFile = files[0];
      file.value = selectedFile;
      
      try {
        uploadProgress.value = 0;
        const interval = setInterval(() => {
          uploadProgress.value = Math.min(uploadProgress.value + 10, 90);
        }, 200);
        
        filePreview.value = await handleFilePreview(selectedFile);
        
        clearInterval(interval);
        uploadProgress.value = 100;
        
        setTimeout(() => {
          uploadProgress.value = 0;
        }, 1000);
        
        showToast("File uploaded successfully!", "success");
      } catch (error) {
        console.error("Error processing dropped file:", error);
        showToast("Failed to process file", "error");
        removeFile();
      }
    }

    async function handleFile(e) {
      const f = e.target.files[0];
      if (!f) return;
      file.value = f;
      try {
        uploadProgress.value = 0;
        const interval = setInterval(() => {
          uploadProgress.value = Math.min(uploadProgress.value + 10, 90);
        }, 200);
        filePreview.value = await handleFilePreview(f);
        clearInterval(interval);
        uploadProgress.value = 100;
        showToast("File ready for processing!", "success");
      } catch (error) {
        showToast("Failed to process file", "error");
        removeFile();
      } finally {
        fileInputKey.value++;
        e.target.value = "";
      }
    }

    function removeFile() {
      if (filePreview.value && filePreview.value.startsWith("blob:")) {
        URL.revokeObjectURL(filePreview.value);
      }
      file.value = null;
      filePreview.value = null;
      uploadProgress.value = 0;
      fileInputKey.value++;
    }

    function useQuickAction(action) {
      input.value = action.text;
      showQuickActions.value = false;
      sendMessage();
    }

    function speakText(text) {
      if (!window.speechSynthesis) return;
      const utter = new SpeechSynthesisUtterance(stripHtml(text));
      utter.rate = 1.05;
      synth.cancel();
      synth.speak(utter);
    }

    function stripHtml(html) {
      const div = document.createElement("div");
      div.innerHTML = html;
      return div.textContent || div.innerText || "";
    }

    function copyText(text) {
      navigator.clipboard.writeText(stripHtml(text));
      showToast("Copied to clipboard!", "success");
    }

    // Enhanced download function with direct format handling
    function downloadMessage(msg, format) {
      if (!format) {
        showToast("Please select a download format", "error");
        return;
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const sender = msg.sender;
      let blob, filename;

      if (format === "excel") {
        // Create Excel content (simplified - in real app use SheetJS)
        const csvContent = [
          ["Sender", "Text", "Timestamp", "File Name", "Category", "Document Type"],
          [
            msg.sender,
            `"${stripHtml(msg.text).replace(/"/g, '""')}"`,
            getTime(msg.timestamp),
            msg.fileData ? msg.fileData.fileName : "",
            msg.fileData ? msg.fileData.category : "",
            msg.fileData ? msg.fileData.document_type : "",
          ],
        ].map(row => row.join(",")).join("\n");
        blob = new Blob([csvContent], { type: "application/vnd.ms-excel" });
        filename = `${sender}-${timestamp}.xlsx`;
      } else if (format === "json") {
        const jsonContent = JSON.stringify({
          sender: msg.sender,
          text: stripHtml(msg.text),
          timestamp: msg.timestamp,
          fileData: msg.fileData ? {
            fileName: msg.fileData.fileName,
            category: msg.fileData.category,
            document_type: msg.fileData.document_type,
          } : null,
        }, null, 2);
        blob = new Blob([jsonContent], { type: "application/json" });
        filename = `${sender}-${timestamp}.json`;
      } else if (format === "csv") {
        const csvContent = [
          ["Sender", "Text", "Timestamp", "File Name", "Category", "Document Type"],
          [
            msg.sender,
            `"${stripHtml(msg.text).replace(/"/g, '""')}"`,
            getTime(msg.timestamp),
            msg.fileData ? msg.fileData.fileName : "",
            msg.fileData ? msg.fileData.category : "",
            msg.fileData ? msg.fileData.document_type : "",
          ],
        ].map(row => row.join(",")).join("\n");
        blob = new Blob([csvContent], { type: "text/csv" });
        filename = `${sender}-${timestamp}.csv`;
      } else if (format === "pdf") {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        doc.setFontSize(12);
        doc.text(`Fin AI Chat - Message Download`, 10, 10);
        doc.text(`Sender: ${msg.sender}`, 10, 20);
        doc.text(`Timestamp: ${getTime(msg.timestamp)}`, 10, 30);
        if (msg.fileData) {
          doc.text(`File: ${msg.fileData.fileName}`, 10, 40);
          doc.text(`Category: ${msg.fileData.category}`, 10, 50);
          doc.text(`Document Type: ${msg.fileData.document_type}`, 10, 60);
          doc.text(`Text: ${stripHtml(msg.text)}`, 10, 70, { maxWidth: 180 });
        } else {
          doc.text(`Text: ${stripHtml(msg.text)}`, 10, 40, { maxWidth: 180 });
        }
        blob = doc.output("blob");
        filename = `${sender}-${timestamp}.pdf`;
      } else {
        showToast("Unsupported format selected", "error");
        return;
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        URL.revokeObjectURL(url);
        a.remove();
      }, 100);
      showToast(`Downloaded as ${format.toUpperCase()}!`, "primary");
    }

    function showToast(text, color = "success") {
      toast.value.text = text;
      toast.value.color = color;
      toast.value.show = true;
      setTimeout(() => (toast.value.show = false), 1300);
    }

    function toggleTheme() {
      isDark.value = !isDark.value;
    }

    function toggleMaximize() {
      isMaximized.value = !isMaximized.value;
    }

    function renderTable(table) {
      if (!Array.isArray(table) || !table.length) return "No data";
      const keys = Object.keys(table[0]);
      return `
        <table class="enhanced-data-table w-full text-sm">
          <thead>
            <tr>${keys
              .map((k) => `<th class="px-4 py-3 font-semibold">${k}</th>`)
              .join("")}
            </tr>
          </thead>
          <tbody>
            ${table
              .map(
                (row, index) =>
                  `<tr class="hover:bg-purple-50 dark:hover:bg-gray-600 transition-colors">
                    ${keys
                      .map((k) => `<td class="px-4 py-3">${row[k]}</td>`)
                      .join("")}
                  </tr>`
              )
              .join("")}
          </tbody>
        </table>
      `;
    }

    async function clearChat() {
      if (confirm("Clear chat history? This action cannot be undone.")) {
        try {
          const user_id = getUserId() || "1517524";
          const session_id = getUserId() || null;

          console.log("Sending clear_history request:", { user_id, session_id });

          const response = await fetch("/clear_history", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ user_id, session_id }),
          });

          const text = await response.text();
          console.log("Raw response:", text);

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${text}`);
          }

          const data = JSON.parse(text);
          console.log("Parsed response:", data);

          chatMessages.value = [{
            sender: "bot",
            text: "👋 Chat history cleared! I'm ready to help you with a fresh start. What would you like to work on today?",
            timestamp: new Date(),
            html: false,
          }];
          showToast("Chat history cleared successfully!", "success");
        } catch (error) {
          console.error("Error clearing chat history:", error);
          showToast("Failed to clear chat history: " + error.message, "error");
        }
      }
    }

    function handleApprove(data) {
      showToast("Document approved successfully!", "success");
      pdfDialogOpen.value = false;
      const editedCount = Object.values(data.fields || {}).filter((f) => f._edited).length;
      chatMessages.value.push({
        sender: "bot",
        text: `✅ Document "${pdfFileName.value}" has been approved with ${editedCount} edited fields. All changes have been saved to your records.`,
        timestamp: new Date(),
      });
    }

    function handleReject(data) {
      showToast("Document rejected!", "error");
      pdfDialogOpen.value = false;
      chatMessages.value.push({
        sender: "bot",
        text: `❌ Document "${pdfFileName.value}" has been rejected. You can upload a corrected version or contact support for assistance.`,
        timestamp: new Date(),
      });
    }

    return {
      chatMessages,
      input,
      sendMessage,
      chatRef,
      isDark,
      toggleTheme,
      loading,
      file,
      filePreview,
      dragover,
      handleDrop,
      handleDragOver,
      handleDragEnter,
      handleDragLeave,
      handleFile,
      removeFile,
      fileInputKey,
      isRecording,
      startRecording,
      clearChat,
      renderTable,
      USER_AVATAR,
      BOT_AVATAR,
      getTime,
      copyText,
      downloadMessage,
      downloadFormats,
      speakText,
      toast,
      isMaximized,
      toggleMaximize,
      pdfDialogOpen,
      pdfUrl,
      pdfAnalysis,
      annotatedImage,
      pdfFileName,
      selectedCategory,
      selectedDocumentType,
      uploadProgress,
      handleApprove,
      handleReject,
      openPdfDialog,
      logout,
      isTyping,
      showQuickActions,
      quickActions,
      useQuickAction,
    };
  },
  template: `
    <v-app>
      <v-snackbar v-model="toast.show" :color="toast.color" timeout="1200" top right>{{ toast.text }}</v-snackbar>

      <!-- Modern Chat Interface with Enhanced Glassmorphism -->
      <div :class="[
            isMaximized ? 'fixed inset-0 z-50 max-w-full max-h-full rounded-none my-0' : 'max-w-6xl',
            'mx-auto my-6 shadow-2xl rounded-3xl bg-gradient-to-br from-purple-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 border border-purple-200 dark:border-gray-700 smooth-transition flex flex-col backdrop-filter backdrop-blur-xl'
          ]" style="height: calc(100vh - 3rem);">

        <!-- Enhanced Header with Glassmorphism Effect -->
        <div class="flex items-center justify-between p-6 border-b border-white/20 sticky top-0 bg-white/10 dark:bg-black/10 z-10 rounded-t-3xl backdrop-filter backdrop-blur-xl">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500 via-blue-600 to-indigo-700 flex items-center justify-center shadow-lg animate-pulse">
              <v-icon color="white" size="28">mdi-robot-excited-outline</v-icon>
            </div>
            <div>
              <span class="text-2xl font-bold bg-gradient-to-r from-purple-600 via-blue-600 to-indigo-600 bg-clip-text text-transparent tracking-tight">Fin AI Assistant</span>
              <div class="flex items-center gap-2 mt-1">
                <div class="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse shadow-lg shadow-green-500/50"></div>
                <span class="text-sm text-gray-600 dark:text-gray-300 font-medium">Online & Ready</span>
              </div>
            </div>
          </div>
          <div class="flex gap-2">
            <v-btn icon @click="toggleTheme" :color="isDark?'yellow':'purple'" variant="text" aria-label="Toggle theme" class="glass-button-enhanced">
              <v-icon>{{ isDark ? 'mdi-weather-night' : 'mdi-white-balance-sunny' }}</v-icon>
            </v-btn>
            <v-btn icon @click="toggleMaximize" color="blue" variant="text" title="Maximize/Minimize" aria-label="Toggle maximize" class="glass-button-enhanced">
              <v-icon v-if="!isMaximized">mdi-arrow-expand</v-icon>
              <v-icon v-else>mdi-arrow-collapse</v-icon>
            </v-btn>
            <v-btn icon @click="clearChat" color="error" variant="text" title="Clear chat" aria-label="Clear chat" class="glass-button-enhanced">
              <v-icon>mdi-broom</v-icon>
            </v-btn>
            <v-btn icon @click="logout" color="red" variant="text" title="Logout" aria-label="Logout" class="glass-button-enhanced">
              <v-icon>mdi-logout</v-icon>
            </v-btn>
          </div>
        </div>

        <!-- Chat Messages Area -->
        <div ref="chatRef"
             class="overflow-y-auto flex-1 px-6 py-6 bg-gradient-to-b from-transparent to-white/5 dark:to-black/5 smooth-transition chat-container-enhanced"
             style="min-height:16rem;">

          <!-- Enhanced Quick Actions Floating Panel -->
          <div v-if="showQuickActions && chatMessages.length === 1"
               class="mb-6 p-6 bg-white/30 dark:bg-black/30 backdrop-filter backdrop-blur-xl rounded-2xl border border-white/30 animate-fade-in shadow-xl">
            <h4 class="text-lg font-semibold mb-4 text-gray-800 dark:text-white flex items-center">
              <v-icon class="mr-2" color="primary">mdi-lightning-bolt</v-icon>
              Quick Actions
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <v-btn
                v-for="action in quickActions"
                :key="action.text"
                :color="action.color"
                variant="elevated"
                class="justify-start h-14 glass-button-enhanced"
                :class="'bg-gradient-to-r ' + action.gradient"
                @click="useQuickAction(action)"
              >
                <v-icon :icon="action.icon" class="mr-3" size="20"></v-icon>
                <span class="font-medium">{{ action.text }}</span>
              </v-btn>
            </div>
          </div>

          <!-- Enhanced Messages -->
          <div v-for="(msg, idx) in chatMessages" :key="idx"
               class="mb-6 flex animate-slide-in message-group"
               :class="msg.sender === 'user' ? 'justify-end' : 'justify-start'"
               :style="{ animationDelay: idx * 0.1 + 's' }">

            <!-- Enhanced User Message -->
            <template v-if="msg.sender === 'user'">
              <div class="flex items-end gap-3 max-w-2xl">
                <div class="relative group">
                  <div class="user-message-enhanced text-white p-4 rounded-2xl rounded-br-md shadow-xl backdrop-filter backdrop-blur-sm border border-white/20" style="white-space: pre-line;">
                    <template v-if="!msg.file">{{ msg.text }}</template>
                    <template v-else>
                      <div class="font-semibold mb-2 flex items-center">
                        <v-icon class="mr-2" size="20">mdi-attachment</v-icon>
                        {{ msg.file.name }}
                      </div>
                      <img v-if="msg.file.type.startsWith('image/')" :src="msg.file.url" class="max-h-32 rounded-lg mt-2 shadow-md" alt="Uploaded image" />
                      <a v-if="msg.file.type.endsWith('pdf')" :href="msg.file.url" target="_blank" class="underline text-white/90 hover:text-white transition-colors" aria-label="Open PDF">📄 Open PDF</a>
                    </template>
                  </div>

                  <!-- Enhanced Message Actions -->
                  <div class="message-actions-enhanced flex gap-2 mt-3 items-center justify-end">
                    <v-btn icon size="small" @click.stop="copyText(msg.text)" variant="text" color="purple" aria-label="Copy message" class="glass-button-small-enhanced">
                      <v-icon size="16">mdi-content-copy</v-icon>
                    </v-btn>

                    <!-- Direct Download Buttons -->
                    <div class="flex gap-1">
                      <v-btn
                        v-for="format in downloadFormats"
                        :key="format.value"
                        icon
                        size="small"
                        variant="text"
                        :color="format.color"
                        @click="downloadMessage(msg, format.value)"
                        :title="'Download as ' + format.label"
                        class="glass-button-small-enhanced"
                      >
                        <v-icon size="16" :color="format.color">{{ format.icon }}</v-icon>
                      </v-btn>
                    </div>

                    <v-btn icon size="small" @click.stop="speakText(msg.text)" variant="text" color="purple" aria-label="Speak message" class="glass-button-small-enhanced">
                      <v-icon size="16">mdi-volume-high</v-icon>
                    </v-btn>
                  </div>
                  <div class="text-xs text-right text-gray-500 mt-1 font-medium">{{ getTime(msg.timestamp) }}</div>
                </div>
                <div class="w-12 h-12 rounded-full border-3 border-purple-400 shadow-xl overflow-hidden bg-gradient-to-br from-purple-400 to-blue-500">
                  <img :src="USER_AVATAR" class="w-full h-full object-cover" alt="User avatar"/>
                </div>
              </div>
            </template>

            <!-- Enhanced Bot Message -->
            <template v-else>
              <div class="flex items-end gap-3 max-w-2xl">
                <div class="w-12 h-12 rounded-full border-3 border-blue-400 shadow-xl overflow-hidden bg-gradient-to-br from-blue-400 to-purple-500">
                  <img :src="BOT_AVATAR" class="w-full h-full object-cover" alt="Bot avatar"/>
                </div>
                <div class="relative group">
                  <!-- Chart Message -->
                  <div v-if="msg.chart" class="enhanced-chart-container">
                    <div :id="'chart-'+idx" class="min-w-[300px] h-[200px] rounded-lg"></div>
                  </div>

                  <!-- Image Message (for visualizations) -->
                  <div v-else-if="msg.image" class="bot-message-enhanced p-4 rounded-2xl shadow-xl">
                    <div class="mb-3 text-gray-900 dark:text-white">{{ msg.text }}</div>
                    <img :src="msg.image" class="max-w-full h-auto rounded-lg shadow-md" alt="Visualization" />
                  </div>

                  <!-- Table Message -->
                  <div v-else-if="msg.table" class="bot-message-enhanced p-4 rounded-2xl shadow-xl" v-html="renderTable(msg.table)"></div>

                  <!-- HTML Message -->
                  <div v-else-if="msg.html" class="bot-message-enhanced text-gray-900 dark:text-white p-4 rounded-2xl rounded-bl-md shadow-xl" v-html="msg.text"></div>

                  <!-- File Data Message -->
                  <div v-else-if="msg.fileData" class="bot-message-enhanced text-gray-900 dark:text-white p-4 rounded-2xl rounded-bl-md shadow-xl">
                    <div class="flex items-center justify-between">
                      <span>{{ msg.text }}</span>
                      <v-btn
                        variant="elevated"
                        color="primary"
                        @click="openPdfDialog(msg)"
                        size="small"
                        class="ml-3 glass-button-enhanced"
                        aria-label="Review PDF"
                      >
                        <v-icon class="mr-1" size="16">mdi-file-eye</v-icon>
                        Review Analysis
                      </v-btn>
                    </div>
                  </div>

                  <!-- Regular Text Message -->
                  <div v-else class="bot-message-enhanced text-gray-900 dark:text-white p-4 rounded-2xl rounded-bl-md shadow-xl">
                    {{ msg.text }}
                  </div>

                  <!-- Enhanced Message Actions -->
                  <div class="message-actions-enhanced flex gap-2 mt-3 items-center">
                    <v-btn icon size="small" @click.stop="copyText(msg.text)" variant="text" color="blue" aria-label="Copy message" class="glass-button-small-enhanced">
                      <v-icon size="16">mdi-content-copy</v-icon>
                    </v-btn>

                    <!-- Direct Download Buttons -->
                    <div class="flex gap-1">
                      <v-btn
                        v-for="format in downloadFormats"
                        :key="format.value"
                        icon
                        size="small"
                        variant="text"
                        :color="format.color"
                        @click="downloadMessage(msg, format.value)"
                        :title="'Download as ' + format.label"
                        class="glass-button-small-enhanced"
                      >
                        <v-icon size="16" :color="format.color">{{ format.icon }}</v-icon>
                      </v-btn>
                    </div>

                    <v-btn icon size="small" @click.stop="speakText(msg.text)" variant="text" color="blue" aria-label="Speak message" class="glass-button-small-enhanced">
                      <v-icon size="16">mdi-volume-high</v-icon>
                    </v-btn>
                  </div>
                  <div class="text-xs text-left text-gray-500 mt-1 font-medium">{{ getTime(msg.timestamp) }}</div>
                </div>
              </div>
            </template>
          </div>

          <!-- Enhanced Typing Indicator -->
          <div v-if="isTyping" class="flex justify-start mb-6">
            <div class="flex items-end gap-3">
              <div class="w-12 h-12 rounded-full border-3 border-blue-400 shadow-xl overflow-hidden bg-gradient-to-br from-blue-400 to-purple-500">
                <img :src="BOT_AVATAR" class="w-full h-full object-cover" alt="Bot avatar"/>
              </div>
              <div class="typing-indicator-enhanced">
                <div class="flex items-center gap-2 p-4 bg-white/80 dark:bg-black/60 backdrop-filter backdrop-blur-xl rounded-2xl border border-white/30 shadow-xl">
                  <div class="typing-dots-enhanced">
                    <div class="typing-dot-enhanced"></div>
                    <div class="typing-dot-enhanced"></div>
                    <div class="typing-dot-enhanced"></div>
                  </div>
                  <span class="ml-2 text-gray-700 dark:text-gray-200 text-sm font-medium">AI is thinking...</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Enhanced Loading Indicator -->
          <div v-if="loading && !isTyping" class="w-full flex justify-center my-6">
            <div class="flex items-center gap-4 p-6 bg-white/70 dark:bg-black/50 backdrop-filter backdrop-blur-xl rounded-2xl border border-white/30 shadow-xl">
              <v-progress-circular indeterminate color="primary" size="28" width="3" aria-label="Loading"/>
              <span class="text-gray-700 dark:text-gray-200 font-medium">Processing your request...</span>
            </div>
          </div>

          <!-- Full Screen Loading Overlay -->
          <div v-if="loading" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[9999]">
            <div class="bg-white dark:bg-gray-800 rounded-3xl p-8 shadow-2xl border border-gray-200 dark:border-gray-700 max-w-sm w-full mx-4">
              <div class="text-center">
                <div class="mb-4">
                  <v-progress-circular 
                    indeterminate 
                    color="primary" 
                    size="64" 
                    width="4"
                    class="mb-4"
                  ></v-progress-circular>
                </div>
                <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-2">Processing...</h3>
                <p class="text-gray-600 dark:text-gray-300 text-sm">Please wait while we process your request</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Enhanced Input Area with Glassmorphism -->
        <div class="border-t border-white/20 sticky bottom-0 bg-white/10 dark:bg-black/10 z-10 rounded-b-3xl backdrop-filter backdrop-blur-xl">
          <!-- Message Input -->
          <form @submit.prevent="sendMessage" class="flex gap-4 p-6">
            <v-btn
              icon
              :loading="isRecording"
              @click.prevent="startRecording"
              :disabled="isRecording"
              variant="tonal"
              color="primary"
              aria-label="Toggle recording"
              class="glass-button-enhanced"
              size="large"
            >
              <v-icon>{{ isRecording ? 'mdi-microphone-off' : 'mdi-microphone' }}</v-icon>
            </v-btn>

            <v-text-field
              v-model="input"
              class="flex-1 enhanced-input"
              density="comfortable"
              rounded
              variant="outlined"
              placeholder="Ask me anything about documents, compliance, or get help..."
              :disabled="loading"
              hide-details
              aria-label="Message input"
              @focus="showQuickActions = !input && chatMessages.length === 1"
            />

            <v-btn
              type="submit"
              color="primary"
              variant="elevated"
              class="px-8 glass-button-enhanced"
              :disabled="loading || (!input && !file)"
              aria-label="Send message"
              size="large"
            >
              <v-icon class="mr-2">mdi-send</v-icon>
              Send
            </v-btn>
          </form>

          <!-- Enhanced File Upload Area -->
          <div class="px-6 pb-6">
            <label
              @dragover.prevent="handleDragOver"
              @dragenter.prevent="handleDragEnter"
              @dragleave.prevent="handleDragLeave"
              @drop.prevent="handleDrop"
              class="enhanced-file-upload-zone block w-full p-8 border-2 border-dashed rounded-2xl text-center cursor-pointer transition-all duration-300 bg-white/90 dark:bg-gray-800/90 backdrop-filter backdrop-blur-md"
              :class="{
                'border-blue-400 bg-blue-50/80 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100/80 dark:hover:bg-blue-900/50 transform scale-[1.02]': !dragover && !file,
                'border-green-400 bg-green-50/80 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-100/80 dark:hover:bg-green-900/50 transform scale-[1.05] ring-2 ring-green-400/50': dragover,
                'border-purple-400 bg-purple-50/80 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400': file
              }"
            >
              <input ref="uploadInput" type="file" class="hidden" @change="handleFile" :key="fileInputKey" aria-label="Upload file"/>

              <!-- Enhanced Upload Progress -->
              <v-progress-linear
                v-if="uploadProgress > 0 && uploadProgress < 100"
                :value="uploadProgress"
                height="10"
                rounded
                color="primary"
                class="mb-6"
                style="box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);"
              ></v-progress-linear>

              <!-- Upload States -->
              <div v-if="!file && !dragover" class="flex flex-col items-center gap-4">
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-400 via-purple-500 to-indigo-600 flex items-center justify-center shadow-xl">
                  <v-icon color="white" size="32">mdi-cloud-upload</v-icon>
                </div>
                <div class="text-center">
                  <div class="text-xl font-bold text-gray-800 dark:text-white mb-2">Drag & drop your file here</div>
                  <div class="text-sm text-gray-600 dark:text-gray-300">or <span class="underline font-medium cursor-pointer hover:text-blue-600 dark:hover:text-blue-400">click to browse</span></div>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 bg-white/70 dark:bg-gray-700/70 px-4 py-2 rounded-full border border-gray-200 dark:border-gray-600">
                  Supports PDF, images, Excel, Word, and more
                </div>
              </div>

              <!-- Drag Over State -->
              <div v-if="dragover" class="flex flex-col items-center gap-4">
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center animate-bounce shadow-xl">
                  <v-icon color="white" size="32">mdi-file-plus</v-icon>
                </div>
                <div class="text-xl font-bold text-green-600 dark:text-green-400">Drop your file here!</div>
              </div>

              <!-- Enhanced File Preview -->
              <div v-if="file" class="flex flex-col items-center gap-4">
                <div class="flex items-center gap-4 p-4 bg-white/80 dark:bg-gray-800/80 rounded-xl shadow-lg border border-gray-200 dark:border-gray-600">
                  <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center shadow-lg">
                    <v-icon color="white" size="24">{{ file.type.includes('pdf') ? 'mdi-file-pdf-box' : file.type.includes('image') ? 'mdi-file-image' : 'mdi-file-document' }}</v-icon>
                  </div>
                  <div class="text-left flex-1">
                    <div class="font-semibold text-gray-800 dark:text-white truncate max-w-xs">{{ file.name }}</div>
                    <div class="text-xs text-gray-600 dark:text-gray-400">{{ (file.size / 1024 / 1024).toFixed(2) }} MB • {{ file.type }}</div>
                  </div>
                </div>

                <!-- File Preview Images -->
                <div v-if="filePreview && file.type.startsWith('image/')" class="w-full max-w-md">
                  <img :src="filePreview" class="w-full max-h-40 object-contain rounded-xl shadow-xl border border-gray-200 dark:border-gray-600" alt="File preview"/>
                </div>
                
                <div v-if="filePreview && file.type.endsWith('pdf')" class="w-full max-w-md">
                  <iframe :src="filePreview" class="w-full h-40 rounded-xl shadow-xl border border-gray-200 dark:border-gray-600" title="PDF preview"></iframe>
                </div>

                <div class="flex gap-2">
                  <v-btn @click.prevent="removeFile" color="error" size="small" variant="elevated" aria-label="Remove file" class="glass-button-enhanced">
                    <v-icon class="mr-2" size="16">mdi-close</v-icon>
                    Remove File
                  </v-btn>
                  <v-btn v-if="file" color="primary" size="small" variant="outlined" aria-label="File info" class="glass-button-enhanced">
                    <v-icon class="mr-2" size="16">mdi-information</v-icon>
                    {{ file.type.split('/')[0].toUpperCase() }}
                  </v-btn>
                </div>
              </div>
            </label>
          </div>
        </div>

        <!-- PDF Review Dialog -->
        <PdfReviewDialog
          :open="pdfDialogOpen"
          :pdf-url="pdfUrl"
          :analysis="pdfAnalysis"
          :annotated-image="annotatedImage"
          :file-name="pdfFileName"
          :category="selectedCategory"
          :document_type="selectedDocumentType"
          @update:open="pdfDialogOpen = $event"
          @approve="handleApprove"
          @reject="handleReject"
        />
      </div>
    </v-app>
  `,
};

console.log('main.js: Defining createChatApp');
window.createChatApp = () => {
  console.log('main.js: createChatApp called');
  return createApp(App).use(vuetify);
};