const { createApp, ref, onMounted, watch, nextTick, onUnmounted } = window.Vue;
const { createVuetify } = window.Vuetify;
const vuetify = createVuetify();


const USER_AVATAR = "https://randomuser.me/api/portraits/women/68.jpg";
const BOT_AVATAR = "https://img.icons8.com/color/48/000000/artificial-intelligence.png";


function getTime(ts = new Date()) {
  if (!ts) return "";
  if (!(ts instanceof Date)) ts = new Date(ts);
  if (isNaN(ts.getTime())) return "";
  return ts.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => resolve(e.target.result);
    reader.onerror = e => reject(e);
    reader.readAsDataURL(file);
  });
}

// Better file handling
async function handleFilePreview(file) {
  if (!file) return null;

  try {
    if (file.type.startsWith('image/')) {
      return await fileToDataUrl(file);
    } else if (file.type === 'application/pdf') {
      return URL.createObjectURL(file);
    } else {
      console.warn('Unsupported file type:', file.type);
      return null;
    }
  } catch (error) {
    console.error('Error creating file preview:', error);
    return null;
  }
}

// Main App Component
const App = {
  components: {
    PdfReviewDialog: window.PdfReviewDialog,
    ImagePageViewer: window.ImagePageViewer
  },
  setup() {
    const chatMessages = ref([]);
    const input = ref('');
    const isDark = ref(false);
    const isMaximized = ref(false);
    const loading = ref(false);
    const chatRef = ref(null);
    const file = ref(null);
    const filePreview = ref(null);
    const pdfDialogOpen = ref(false);
    const pdfUrl = ref("");
    const pdfAnalysis = ref(null);
    const pdfFileName = ref("");
    const annotatedImage = ref([]); // changed from string to arra
    const isRecording = ref(false);
    const currentPage = ref(1);
    const fileInputKey = ref(0); // Force re-render file input
    let recognition;
    let synth = window.speechSynthesis;
    const toast = ref({ show: false, text: "", color: "success" });

    onMounted(async () => {
      try {
        const res = await fetch('/history?user_id=1517524');
        const data = await res.json();
        if (Array.isArray(data.conversation_history) && data.conversation_history.length) {
          chatMessages.value = data.conversation_history.map(msg => ({
            sender: msg.role === 'user' ? 'user' : 'bot',
            text: msg.message,
            timestamp: new Date(msg.created_at),
            html: /<[a-z][\s\S]*>/i.test(msg.message),
            fileData: msg.file_data || null
          }));
        } else {
          chatMessages.value = [{
            sender: "bot",
            text: "<h2>👋 Welcome to Fin AI!</h2><p>How can I help you today?</p>",
            timestamp: new Date(),
            html: true
          }];
        }
      } catch (e) {
        console.error('Failed to load chat history:', e);
        chatMessages.value = [{
          sender: "bot",
          text: "<h2>👋 Welcome to Fin AI!</h2><p>How can I help you today?</p>",
          timestamp: new Date(),
          html: true
        }];
      }
    });

    onUnmounted(() => {
      // Clean up object URLs to prevent memory leaks
      if (filePreview.value && filePreview.value.startsWith('blob:')) {
        URL.revokeObjectURL(filePreview.value);
      }
    });

    watch(chatMessages, () => nextTick(() => scrollToBottom()));

    function scrollToBottom() {
      if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight;
    }

    async function sendMessage() {
      if (!input.value.trim() && !file.value) return;

      if (input.value.trim()) {
        chatMessages.value.push({
          sender: "user",
          text: input.value,
          timestamp: new Date()
        });
      }

      if (file.value) {
        chatMessages.value.push({
          sender: "user",
          file: {
            name: file.value.name,
            type: file.value.type,
            url: filePreview.value
          },
          text: file.value.name,
          timestamp: new Date()
        });
      }

      loading.value = true;
      let response;

      try {
        if (file.value) {
          console.log("Uploading file:", file.value.name, file.value.type, file.value.size);

          const formData = new FormData();
          formData.append('query', input.value || '');
          formData.append('user_id', '1517524');
          formData.append('productname', 'EE');
          formData.append('functionname', 'register_import_lc');
          formData.append('SCF', 'false');
          formData.append('file', file.value);

          console.log("Making POST request to /query with file upload");

          const res = await fetch('/query', {
            method: 'POST',
            body: formData
          });

          console.log("Response status:", res.status, res.statusText);

          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          }

          const responseText = await res.text();
         // 🔍 Log full parsed JSON info instead of truncated string
try {
  const parsed = JSON.parse(responseText);
  console.log("✅ Full parsed response:", parsed);

  // ✅ Correct path: parsed.response[0].page_classifications[0]
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

          if (file.value.type.endsWith('pdf') && response.analysis_result) {
            pdfUrl.value = filePreview.value;
            pdfAnalysis.value = response.analysis_result;
            pdfFileName.value = file.value.name;
             // Extract category and document type properly
    const firstPage = response.analysis_result.per_page?.[0];
    const category = firstPage?.page_classifications?.[0]?.category;
    const document_type = firstPage?.page_classifications?.[0]?.document_type;

    console.log("Category Type:", category);
    console.log("Document Type:", document_type);

            // Handle annotated image
            if (response.annotated_image && Array.isArray(response.annotated_image)) {
              // ✅ FIXED: Convert all base64 to data URLs
              annotatedImage.value = response.annotated_image.map(img =>
                img.startsWith('data:image/') ? img : "data:image/jpeg;base64," + img
              );
            } else {
              annotatedImage.value = [];
            }

            pdfDialogOpen.value = true;
            chatMessages.value.push({
              sender: "bot",
              text: `PDF "${file.value.name}" processed successfully. Click to review.`,
              timestamp: new Date(),
              fileData: {
                pdfUrl: filePreview.value,
                pdfAnalysis: response.analysis_result,
                annotatedImage: annotatedImage.value,
                fileName: file.value.name
              }
            });
            removeFile();
            loading.value = false;
            input.value = '';
            return;
          }

          removeFile();
        } else {
          console.log("Sending text query:", input.value);

          const res = await fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              query: input.value,
              user_id: '1517524',
              productname: 'EE',
              functionname: 'register_import_lc',
              SCF: false
            })
          });

          console.log("Text query response status:", res.status, res.statusText);

          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          }

          response = await res.json();
        }
        handleBackendResponse(response);
      } catch (err) {
        console.error('Detailed error sending message:', {
          error: err,
          message: err.message,
          stack: err.stack,
          type: err.name
        });

        let errorMessage = "Sorry, there was a problem contacting the backend.";

        if (err.message.includes('fetch')) {
          errorMessage += " Network connection failed.";
        } else if (err.message.includes('JSON')) {
          errorMessage += " Invalid response format.";
        } else if (err.message.includes('HTTP')) {
          errorMessage += ` Server error: ${err.message}`;
        }

        chatMessages.value.push({
          sender: "bot",
          text: errorMessage,
          timestamp: new Date()
        });
        showToast(`Error: ${err.message}`, "error");
      } finally {
        loading.value = false;
        input.value = '';
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
          pdfAnalysis.value = {
  ...responseData.analysis_result,
  page_classifications: responseData.page_classifications
};
          pdfFileName.value = responseData.file_name || "Document";
          console.log("pdfAnalysis value:", JSON.stringify(pdfAnalysis.value, null, 2));
          console.log("Category Type:", pdfAnalysis.value.page_classifications?.[0]?.category);


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
              annotatedImage.value = "";
            }
          } else {
            console.log("No annotated image in response");
            annotatedImage.value = "";
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
              fileName: responseData.file_name || "Document"
            }
          });
          return;
        }
      }

      // Fallback: Handle direct analysis result (in case of different response structure)
      if (data && (data.analysis_result || data.annotated_image)) {
        pdfAnalysis.value = data.analysis_result;

        if (data.annotated_image && Array.isArray(data.annotated_image) && data.annotated_image.length > 0) {
          const imageData = data.annotated_image[0];
          if (imageData && typeof imageData === 'string' && imageData.length > 0) {
            annotatedImage.value = imageData.startsWith('data:image/') ? imageData : "data:image/jpeg;base64," + imageData;
          } else {
            annotatedImage.value = "";
          }
        } else {
          annotatedImage.value = "";
        }

        pdfFileName.value = data.file_name || "Document";
        pdfDialogOpen.value = true;
        chatMessages.value.push({
          sender: "bot",
          text: `PDF "${data.file_name || 'document'}" processed. Click to review.`,
          timestamp: new Date(),
          fileData: {
            pdfUrl: pdfUrl.value,
            pdfAnalysis: data.analysis_result,
            annotatedImage: annotatedImage.value,
            fileName: data.file_name || "Document"
          }
        });
        return;
      }

      // Handle table responses
      if (data.intent && data.intent.toLowerCase().includes('table') && data.response && data.response.table) {
        chatMessages.value.push({
          sender: "bot",
          table: data.response.table,
          timestamp: new Date()
        });
        return;
      }

      // Handle chart/visualization responses
      if (data.intent && data.intent.toLowerCase().includes('visualization') && data.chart) {
        chatMessages.value.push({
          sender: "bot",
          chart: data.chart,
          timestamp: new Date()
        });
        return;
      }

      // Handle HTML responses
      if (data.result && /<[a-z][\s\S]*>/i.test(data.result)) {
        chatMessages.value.push({
          sender: "bot",
          text: data.result,
          timestamp: new Date(),
          html: true
        });
        return;
      }

      // Handle string responses
      if (data.response && typeof data.response === "string") {
        chatMessages.value.push({
          sender: "bot",
          text: data.response,
          timestamp: new Date(),
          html: /<[a-z][\s\S]*>/i.test(data.response)
        });
        return;
      }

      // Default: show JSON response for debugging
      console.warn("Unhandled response structure:", data);
      chatMessages.value.push({
        sender: "bot",
        text: `<pre>${JSON.stringify(data, null, 2)}</pre>`,
        timestamp: new Date(),
        html: true
      });
    }

    function openPdfDialog(msg) {
      if (msg.fileData) {
        pdfUrl.value = msg.fileData.pdfUrl;
        pdfAnalysis.value = msg.fileData.pdfAnalysis;
        annotatedImage.value = msg.fileData.annotatedImage;
        pdfFileName.value = msg.fileData.fileName;
        pdfDialogOpen.value = true;
      }
    }

    async function handleDrop(e) {
      e.preventDefault();
      const files = e.dataTransfer.files;
      if (!files.length) return;

      const selectedFile = files[0];
      file.value = selectedFile;

      try {
        filePreview.value = await handleFilePreview(selectedFile);
      } catch (error) {
        console.error('Error handling dropped file:', error);
        showToast("Failed to process file", "error");
      }
    }

    async function handleFile(e) {
      const f = e.target.files[0];
      if (f) {
        file.value = f;
      try {
    filePreview.value = await handleFilePreview(f);
  } catch (error) {
    console.error('Error handling selected file:', error);
    showToast("Failed to process file", "error");
    removeFile(); // Clean up on error
  } finally {
    // Reset input value to allow same file selection
    e.target.value = '';
  }
}
    }

    function removeFile() {
      if (filePreview.value && filePreview.value.startsWith('blob:')) {
        URL.revokeObjectURL(filePreview.value);
      }
      file.value = null;
      filePreview.value = null;
      fileInputKey.value++; // Reset file input
    }

    function startRecording() {
      if (!('webkitSpeechRecognition' in window)) {
        showToast('Voice recognition not supported in your browser.', 'error');
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
      recognition.onresult = e => {
        input.value = e.results[0][0].transcript;
        isRecording.value = false;
      };
      recognition.onerror = () => {
        isRecording.value = false;
        showToast('Voice recognition error', 'error');
      };
      recognition.onend = () => isRecording.value = false;
      recognition.start();
    }

    function speakText(text) {
      if (!window.speechSynthesis) return;
      const utter = new SpeechSynthesisUtterance(stripHtml(text));
      utter.rate = 1.05;
      synth.cancel();
      synth.speak(utter);
    }

    function stripHtml(html) {
      const div = document.createElement('div');
      div.innerHTML = html;
      return div.textContent || div.innerText || '';
    }

    function copyText(text) {
      navigator.clipboard.writeText(stripHtml(text));
      showToast("Copied to clipboard!", "success");
    }

    function downloadText(text, sender = 'message') {
      const blob = new Blob([stripHtml(text)], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      a.href = url;
      a.download = `${sender}-${timestamp}.txt`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
      showToast("Downloaded!", "primary");
    }

    function showToast(text, color = "success") {
      toast.value.text = text;
      toast.value.color = color;
      toast.value.show = true;
      setTimeout(() => toast.value.show = false, 1300);
    }

    function toggleTheme() {
      isDark.value = !isDark.value;
      document.body.classList.toggle('dark', isDark.value);
      document.body.classList.toggle('bg-gray-900', isDark.value);
    }

    function toggleMaximize() {
      isMaximized.value = !isMaximized.value;
    }

    watch(chatMessages, async () => {
      await nextTick();
      chatMessages.value.forEach((msg, idx) => {
        if (msg.chart && !msg._rendered) {
          try {
            Highcharts.chart('chart-' + idx, {
              chart: { backgroundColor: 'transparent' },
              title: { text: msg.chart.title || "Chart" },
              series: [{ data: msg.chart.data }]
            });
            msg._rendered = true;
          } catch (error) {
            console.error('Error rendering chart:', error);
          }
        }
      });
    });

    function renderTable(table) {
      if (!Array.isArray(table) || !table.length) return 'No data';
      const keys = Object.keys(table[0]);
      return `
        <table class="min-w-full text-sm text-gray-800 dark:text-gray-200">
          <thead><tr>${keys.map(k => `<th class="px-2 py-1 border-b font-bold">${k}</th>`).join('')}</tr></thead>
          <tbody>
            ${table.map(row => `
              <tr>${keys.map(k => `<td class="px-2 py-1 border-b">${row[k]}</td>`).join('')}</tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    function clearChat() {
      if (confirm("Clear chat history?")) {
        chatMessages.value = [{
          sender: "bot",
          text: "<h2>👋 Welcome to Fin AI!</h2><p>How can I help you today?</p>",
          timestamp: new Date(),
          html: true
        }];
      }
    }

    function handleApprove(data) {
      showToast("Document approved!", "success");
      pdfDialogOpen.value = false;
      const editedCount = Object.values(data.fields).filter(f => f._edited).length;
      chatMessages.value.push({
        sender: "bot",
        text: `Document "${pdfFileName.value}" approved with ${editedCount} edited fields.`,
        timestamp: new Date()
      });
    }

    function handleReject(data) {
      showToast("Document rejected!", "error");
      pdfDialogOpen.value = false;
      chatMessages.value.push({
        sender: "bot",
        text: `Document "${pdfFileName.value}" rejected.`,
        timestamp: new Date()
      });
    }

    return {
      chatMessages, input, sendMessage, chatRef, isDark, toggleTheme, loading,
      file, filePreview, handleDrop, handleFile, removeFile,
      isRecording, startRecording,
      clearChat, renderTable,
      USER_AVATAR, BOT_AVATAR, getTime,
      copyText, downloadText, speakText, toast,
      isMaximized, toggleMaximize,
      pdfDialogOpen, pdfAnalysis, pdfUrl,fileInputKey, pdfFileName, annotatedImage,
      handleApprove, handleReject, openPdfDialog
    };
  },
  template: `
    <v-app>
      <v-snackbar v-model="toast.show" :color="toast.color" timeout="1200" top right>{{ toast.text }}</v-snackbar>
      <div :class="[
            isMaximized ? 'fixed inset-0 z-50 max-w-full max-h-full rounded-none my-0' : 'max-w-2xl',
            'mx-auto my-8 shadow-2xl rounded-3xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 smooth-transition flex flex-col'
          ]" style="height: calc(100vh - 4rem);">
        <div class="flex items-center justify-between p-6 border-b border-gray-100 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800 z-10 rounded-t-3xl">
          <div class="flex items-center gap-3">
            <img :src="BOT_AVATAR" class="w-9 h-9" alt="Bot avatar"/>
            <span class="text-2xl font-bold text-gray-800 dark:text-gray-200 tracking-tight">Fin AI ChatBot</span>
          </div>
          <div class="flex gap-2">
            <v-btn icon @click="toggleTheme" :color="isDark?'yellow':'primary'" variant="text" aria-label="Toggle theme">
              <v-icon>{{ isDark ? 'mdi-weather-night' : 'mdi-white-balance-sunny' }}</v-icon>
            </v-btn>
            <v-btn icon @click="toggleMaximize" color="primary" variant="text" title="Maximize/Minimize" aria-label="Toggle maximize">
              <v-icon v-if="!isMaximized">mdi-arrow-expand</v-icon>
              <v-icon v-else>mdi-arrow-collapse</v-icon>
            </v-btn>
            <v-btn icon @click="clearChat" color="error" variant="text" title="Clear chat" aria-label="Clear chat">
              <v-icon>mdi-trash-can</v-icon>
            </v-btn>
          </div>
        </div>
        <div ref="chatRef"
             class="overflow-y-auto flex-1 px-4 py-6 bg-gray-50 dark:bg-gray-700 smooth-transition chat-container"
             style="min-height:16rem;">
          <div v-for="(msg,idx) in chatMessages" :key="idx"
  class="mb-6 flex"
  @click="openPdfDialog(msg)"
  :class="[
    msg.sender === 'user' ? 'justify-end' : 'justify-start',
    msg.fileData ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg smooth-transition' : ''
  ]">

            <template v-if="msg.sender==='user'">
              <div class="flex items-end gap-2">
                <div class="relative group">
                  <div class="flex gap-1 absolute -top-6 right-0 opacity-0 group-hover:opacity-100 smooth-transition z-10">
                    <v-tooltip text="Copy"><template #activator="{ props }">
                      <v-btn v-bind="props" icon variant="text" size="x-small" @click.stop="copyText(msg.text)" aria-label="Copy message"><v-icon size="18">mdi-content-copy</v-icon></v-btn>
                    </template></v-tooltip>
                    <v-tooltip text="Download"><template #activator="{ props }">
                      <v-btn v-bind="props" icon variant="text" size="x-small" @click.stop="downloadText(msg.text, 'user')" aria-label="Download message"><v-icon size="18">mdi-download</v-icon></v-btn>
                    </template></v-tooltip>
                    <v-tooltip text="Speak"><template #activator="{ props }">
                      <v-btn v-bind="props" icon variant="text" size="x-small" @click.stop="speakText(msg.text)" aria-label="Speak message"><v-icon size="18">mdi-volume-high</v-icon></v-btn>
                    </template></v-tooltip>
                  </div>
                  <div class="max-w-xs bg-blue-600 text-white p-3 rounded-2xl rounded-br-md shadow-md text-base" style="white-space:pre-line;">
                    <template v-if="!msg.file">{{ msg.text }}</template>
                    <template v-else>
                      <div class="font-semibold mb-1"><v-icon class="mr-1" size="20">mdi-paperclip</v-icon>{{ msg.file.name }}</div>
                      <img v-if="msg.file.type.startsWith('image/')" :src="msg.file.url" class="max-h-32 rounded-lg mt-2 image-fade-in" alt="Uploaded image" />
                      <a v-if="msg.file.type.endsWith('pdf')" :href="msg.file.url" target="_blank" class="underline text-xs text-white" aria-label="Open PDF">Open PDF</a>
                    </template>
                  </div>
                  <div class="text-xs text-right text-gray-400 mt-1">{{ getTime(msg.timestamp) }}</div>
                </div>
                <img :src="USER_AVATAR" class="w-8 h-8 rounded-full border-2 border-blue-400" alt="User avatar"/>
              </div>
            </template>
            <template v-else>
              <div class="flex items-end gap-2">
                <img :src="BOT_AVATAR" class="w-8 h-8 rounded-full border-2 border-blue-400" alt="Bot avatar"/>
                <div class="relative group">
                  <div class="flex gap-1 absolute -top-6 right-0 opacity-0 group-hover:opacity-100 smooth-transition z-10">
                    <v-tooltip text="Copy"><template #activator="{ props }">
                      <v-btn v-bind="props" icon variant="text" size="x-small" @click.stop="copyText(msg.text)" aria-label="Copy message"><v-icon size="18">mdi-content-copy</v-icon></v-btn>
                    </template></v-tooltip>
                    <v-tooltip text="Download"><template #activator="{ props }">
                      <v-btn v-bind="props" icon variant="text" size="x-small" @click.stop="downloadText(msg.text, 'bot')" aria-label="Download message"><v-icon size="18">mdi-download</v-icon></v-btn>
                    </template></v-tooltip>
                    <v-tooltip text="Speak"><template #activator="{ props }">
                      <v-btn v-bind="props" icon variant="text" size="x-small" @click.stop="speakText(msg.text)" aria-label="Speak message"><v-icon size="18">mdi-volume-high</v-icon></v-btn>
                    </template></v-tooltip>
                  </div>
                  <div v-if="msg.chart" class="max-w-xs p-2 bg-gray-200 dark:bg-gray-600 rounded-2xl shadow-md">
                    <div :id="'chart-'+idx" style="min-width:200px; height:150px;"></div>
                  </div>
                  <div v-else-if="msg.table" class="max-w-xs p-2 bg-gray-200 dark:bg-gray-600 rounded-2xl shadow-md" v-html="renderTable(msg.table)"></div>
                  <div v-else-if="msg.html" class="max-w-xs bg-gray-200 dark:bg-gray-600 text-gray-900 dark:text-white p-3 rounded-2xl rounded-bl-md shadow-md" v-html="msg.text"></div>
                  <div v-else class="max-w-xs bg-gray-200 dark:bg-gray-600 text-gray-900 dark:text-white p-3 rounded-2xl rounded-bl-md shadow-md">
                    {{ msg.text }}
                  </div>
                  <div class="text-xs text-left text-gray-400 mt-1">{{ getTime(msg.timestamp) }}</div>
                </div>
              </div>
            </template>
          </div>
          <div v-if="loading" class="w-full flex justify-center my-4">
            <v-progress-circular indeterminate color="primary" aria-label="Loading"/>
            <span class="ml-2 text-gray-600 dark:text-gray-300 loading-dots">Processing</span>
          </div>
        </div>
        <form @submit.prevent="sendMessage" class="flex gap-2 p-6 pt-3 border-t border-gray-100 dark:border-gray-700 sticky bottom-0 bg-white dark:bg-gray-800 z-10 rounded-b-3xl">
          <v-btn icon :loading="isRecording" @click.prevent="startRecording" :disabled="isRecording" variant="tonal" color="primary" aria-label="Toggle recording">
            <v-icon>{{ isRecording ? 'mdi-microphone-off' : 'mdi-microphone' }}</v-icon>
          </v-btn>
          <v-text-field
            v-model="input"
            class="flex-1"
            density="compact"
            rounded
            variant="outlined"
            placeholder="Type your message..."
            :disabled="loading"
            hide-details
            aria-label="Message input"
          />
          <v-btn type="submit" color="primary" variant="flat" class="ml-1" :disabled="loading || (!input && !file)" aria-label="Send message">
            <v-icon>mdi-send</v-icon>
          </v-btn>
        </form>
        <div class="px-6 pb-6">
          <label
            @dragover.prevent
            @drop="handleDrop"
            class="file-upload-zone block w-full p-4 border-2 border-dashed border-blue-400 rounded-xl text-center text-blue-600 cursor-pointer bg-blue-50 dark:bg-gray-700 dark:border-blue-200 hover:bg-blue-100"
          >
            <input type="file" class="hidden" @change="handleFile":key="fileInputKey" aria-label="Upload file"/>
            <span v-if="!file">Drag & drop a file or <span class="underline">click to upload</span></span>
            <div v-if="file" class="flex flex-col items-center gap-2">
              <span class="font-medium text-gray-700 dark:text-gray-200">{{ file.name }}</span>
              <img v-if="filePreview && file.type.startsWith('image/')" :src="filePreview" class="max-h-24 rounded image-fade-in loaded" alt="File preview" />
              <iframe v-if="filePreview && file.type.endsWith('pdf')" :src="filePreview" class="w-full h-24 rounded" title="PDF preview"></iframe>
              <v-btn @click.prevent="removeFile" color="error" size="small" variant="outlined" aria-label="Remove file">Remove</v-btn>
            </div>
          </label>
        </div>
        <PdfReviewDialog
          :open="pdfDialogOpen"
          :pdf-url="pdfUrl"
          :analysis="pdfAnalysis"
          :annotated-image="annotatedImage"
          :file-name="pdfFileName"


          @update:open="pdfDialogOpen = $event"
          @approve="handleApprove"
          @reject="handleReject"
        />
      </div>
    </v-app>
  `
};

console.log('ImagePageViewer is', window.ImagePageViewer);
console.log('PdfReviewDialog is', window.PdfReviewDialog);
createApp(App).use(vuetify).mount('#app');