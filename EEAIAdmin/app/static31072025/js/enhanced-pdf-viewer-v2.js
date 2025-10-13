(function() {
  // Enhanced PDF Viewer V2 with Modern UI/UX
  
  if (!window.Vue || !window.Vuetify) {
    console.error('Vue.js and Vuetify are required.');
    return;
  }

  // Helper function for base64 validation
  function isValidBase64(str) {
    if (!str || typeof str !== 'string') return false;
    try {
      return btoa(atob(str)) === str;
    } catch (err) {
      return false;
    }
  }

  // Enhanced Image Page Viewer Component
  window.ImagePageViewer = {
    name: 'ImagePageViewer',
    props: {
      base64Images: {
        type: Array,
        required: true,
        default: () => []
      },
      fields: {
        type: Object,
        default: () => ({})
      },
      highlightKey: {
        type: String,
        default: ''
      },
      highlightEditedKey: {
        type: String,
        default: ''
      },
      drawingFieldKey: {
        type: String,
        default: ''
      },
      initialPage: {
        type: Number,
        default: 1
      },
      category: {
        type: String,
        default: 'N/A'
      },
      documentType: {
        type: String,
        default: 'N/A'
      }
    },
    emits: ['update-bounding-box', 'page-changed'],
    setup(props, { emit }) {
      const { ref, computed, watch, onMounted, onUnmounted } = Vue;
      
      const pageNum = ref(props.initialPage || 1);
      const loading = ref(false);
      const imageError = ref(null);
      const imgRef = ref(null);
      const containerRef = ref(null);
      const scale = ref(1);
      const minScale = 0.5;
      const maxScale = 3;
      
      // Drawing state
      const isDrawing = ref(false);
      const drawingStart = ref({ x: 0, y: 0 });
      const drawingEnd = ref({ x: 0, y: 0 });
      
      // Pan state
      const isPanning = ref(false);
      const panStart = ref({ x: 0, y: 0 });
      const currentPan = ref({ x: 0, y: 0 });

      const pageCount = computed(() => props.base64Images?.length || 0);

      const imageSrc = computed(() => {
        if (!props.base64Images || props.base64Images.length === 0) return null;
        
        let data = props.base64Images[pageNum.value - 1];
        if (!data) return null;

        if (data.startsWith("data:image/")) return data;
        return "data:image/png;base64," + data;
      });

      const currentPageClassification = computed(() => {
        return {
          category: props.category,
          document_type: props.documentType
        };
      });

      const highlightBoxes = computed(() => {
        if (!props.fields || !imgRef.value) return [];

        const displayWidth = imgRef.value.clientWidth;
        const displayHeight = imgRef.value.clientHeight;
        const naturalWidth = imgRef.value.naturalWidth;
        const naturalHeight = imgRef.value.naturalHeight;

        const scaleX = displayWidth / naturalWidth;
        const scaleY = displayHeight / naturalHeight;

        return Object.entries(props.fields)
          .filter(([key, field]) => {
            return (key === props.highlightKey || key === props.highlightEditedKey) &&
                   field?.bounding_page === pageNum.value;
          })
          .map(([key, field]) => {
            let bbox = field.bounding_box;
            
            if (!bbox) return null;
            
            // Handle different bbox formats
            if (!Array.isArray(bbox)) {
              try {
                bbox = Array.from(bbox);
              } catch (e) {
                if (typeof bbox === 'object' && bbox !== null) {
                  const tempArray = [];
                  let i = 0;
                  while (bbox[i] !== undefined && i < 8) {
                    tempArray.push(bbox[i]);
                    i++;
                  }
                  bbox = tempArray;
                }
              }
            }

            if (!Array.isArray(bbox) || bbox.length === 0) return null;

            // Convert 4-coord to 8-coord format
            if (bbox.length === 4) {
              const [x1, y1, x2, y2] = bbox;
              bbox = [x1, y1, x2, y1, x2, y2, x1, y2];
            }

            if (bbox.length !== 8) return null;

            const dpi = 72;
            const pixelBox = bbox.map((coord, index) => {
              const px = coord * dpi;
              return index % 2 === 0 ? px * scaleX : px * scaleY;
            });

            return {
              key,
              box: pixelBox,
              isEdited: key === props.highlightEditedKey
            };
          })
          .filter(Boolean);
      });

      const drawingBox = computed(() => {
        if (!isDrawing.value) return null;
        
        const x = Math.min(drawingStart.value.x, drawingEnd.value.x);
        const y = Math.min(drawingStart.value.y, drawingEnd.value.y);
        const width = Math.abs(drawingEnd.value.x - drawingStart.value.x);
        const height = Math.abs(drawingEnd.value.y - drawingStart.value.y);
        
        return { x, y, width, height };
      });

      // Mouse/Touch handlers
      function handlePointerDown(event) {
        const rect = containerRef.value.getBoundingClientRect();
        const x = (event.clientX || event.touches[0].clientX) - rect.left;
        const y = (event.clientY || event.touches[0].clientY) - rect.top;

        if (props.drawingFieldKey) {
          event.preventDefault();
          isDrawing.value = true;
          drawingStart.value = { x, y };
          drawingEnd.value = { x, y };
        } else if (event.shiftKey || event.button === 1) {
          isPanning.value = true;
          panStart.value = { x: x - currentPan.value.x, y: y - currentPan.value.y };
        }
      }

      function handlePointerMove(event) {
        const rect = containerRef.value.getBoundingClientRect();
        const x = (event.clientX || event.touches[0].clientX) - rect.left;
        const y = (event.clientY || event.touches[0].clientY) - rect.top;

        if (isDrawing.value) {
          drawingEnd.value = { x, y };
        } else if (isPanning.value) {
          currentPan.value = {
            x: x - panStart.value.x,
            y: y - panStart.value.y
          };
        }
      }

      function handlePointerUp(event) {
        if (isDrawing.value && imgRef.value) {
          const displayWidth = imgRef.value.clientWidth;
          const displayHeight = imgRef.value.clientHeight;
          const naturalWidth = imgRef.value.naturalWidth;
          const naturalHeight = imgRef.value.naturalHeight;
          
          const scaleX = naturalWidth / displayWidth;
          const scaleY = naturalHeight / displayHeight;
          
          const dpi = 72;
          const x1 = Math.min(drawingStart.value.x, drawingEnd.value.x) * scaleX / dpi;
          const y1 = Math.min(drawingStart.value.y, drawingEnd.value.y) * scaleY / dpi;
          const x2 = Math.max(drawingStart.value.x, drawingEnd.value.x) * scaleX / dpi;
          const y2 = Math.max(drawingStart.value.y, drawingEnd.value.y) * scaleY / dpi;
          
          if (Math.abs(drawingEnd.value.x - drawingStart.value.x) > 5 && 
              Math.abs(drawingEnd.value.y - drawingStart.value.y) > 5) {
            emit('update-bounding-box', {
              fieldKey: props.drawingFieldKey,
              boundingBox: [x1, y1, x2, y2],
              boundingPage: pageNum.value
            });
          }
        }
        
        isDrawing.value = false;
        isPanning.value = false;
      }

      // Zoom functions
      function zoomIn() {
        scale.value = Math.min(scale.value * 1.2, maxScale);
      }

      function zoomOut() {
        scale.value = Math.max(scale.value / 1.2, minScale);
      }

      function resetZoom() {
        scale.value = 1;
        currentPan.value = { x: 0, y: 0 };
      }

      function fitToScreen() {
        if (!imgRef.value || !containerRef.value) return;
        
        const containerWidth = containerRef.value.clientWidth;
        const containerHeight = containerRef.value.clientHeight;
        const imgWidth = imgRef.value.naturalWidth;
        const imgHeight = imgRef.value.naturalHeight;
        
        const scaleX = containerWidth / imgWidth;
        const scaleY = containerHeight / imgHeight;
        
        scale.value = Math.min(scaleX, scaleY, 1);
        currentPan.value = { x: 0, y: 0 };
      }

      // Page navigation
      function nextPage() {
        if (pageNum.value < pageCount.value) {
          pageNum.value += 1;
          emit('page-changed', pageNum.value);
        }
      }

      function prevPage() {
        if (pageNum.value > 1) {
          pageNum.value -= 1;
          emit('page-changed', pageNum.value);
        }
      }

      function goToPage(page) {
        if (page >= 1 && page <= pageCount.value) {
          pageNum.value = page;
          emit('page-changed', pageNum.value);
        }
      }

      // Keyboard shortcuts
      function handleKeyboard(event) {
        switch(event.key) {
          case 'ArrowLeft':
            prevPage();
            break;
          case 'ArrowRight':
            nextPage();
            break;
          case '+':
          case '=':
            zoomIn();
            break;
          case '-':
            zoomOut();
            break;
          case '0':
            resetZoom();
            break;
          case 'f':
            fitToScreen();
            break;
        }
      }

      onMounted(() => {
        window.addEventListener('keydown', handleKeyboard);
      });

      onUnmounted(() => {
        window.removeEventListener('keydown', handleKeyboard);
      });

      return {
        pageNum,
        pageCount,
        loading,
        imageError,
        imageSrc,
        imgRef,
        containerRef,
        scale,
        currentPan,
        highlightBoxes,
        drawingBox,
        isDrawing,
        isPanning,
        currentPageClassification,
        handlePointerDown,
        handlePointerMove,
        handlePointerUp,
        nextPage,
        prevPage,
        goToPage,
        zoomIn,
        zoomOut,
        resetZoom,
        fitToScreen
      };
    },
    template: `
      <div class="image-viewer-container" ref="containerRef">
        <!-- Header Toolbar -->
        <div class="viewer-toolbar">
          <div class="toolbar-section">
            <v-btn icon size="small" @click="prevPage" :disabled="pageNum <= 1">
              <v-icon>mdi-chevron-left</v-icon>
            </v-btn>
            <div class="page-indicator">
              <input 
                type="number" 
                :value="pageNum" 
                @change="goToPage($event.target.value)"
                :min="1" 
                :max="pageCount"
                class="page-input"
              />
              <span class="page-total">/ {{ pageCount }}</span>
            </div>
            <v-btn icon size="small" @click="nextPage" :disabled="pageNum >= pageCount">
              <v-icon>mdi-chevron-right</v-icon>
            </v-btn>
          </div>
          
          <div class="toolbar-section">
            <v-btn icon size="small" @click="zoomOut" :disabled="scale <= 0.5">
              <v-icon>mdi-magnify-minus</v-icon>
            </v-btn>
            <span class="zoom-level">{{ Math.round(scale * 100) }}%</span>
            <v-btn icon size="small" @click="zoomIn" :disabled="scale >= 3">
              <v-icon>mdi-magnify-plus</v-icon>
            </v-btn>
            <v-divider vertical class="mx-2"></v-divider>
            <v-btn icon size="small" @click="fitToScreen" title="Fit to screen">
              <v-icon>mdi-fit-to-screen</v-icon>
            </v-btn>
            <v-btn icon size="small" @click="resetZoom" title="Reset view">
              <v-icon>mdi-restore</v-icon>
            </v-btn>
          </div>
          
          <div class="toolbar-section">
            <v-chip size="small" color="primary" variant="tonal">
              {{ currentPageClassification.category }}
            </v-chip>
            <v-chip size="small" color="secondary" variant="tonal">
              {{ currentPageClassification.document_type }}
            </v-chip>
          </div>
        </div>

        <!-- Image Viewer -->
        <div 
          class="viewer-content"
          @mousedown="handlePointerDown"
          @mousemove="handlePointerMove"
          @mouseup="handlePointerUp"
          @mouseleave="handlePointerUp"
          @touchstart="handlePointerDown"
          @touchmove="handlePointerMove"
          @touchend="handlePointerUp"
          :style="{
            cursor: drawingFieldKey ? 'crosshair' : (isPanning ? 'grabbing' : 'grab')
          }"
        >
          <div 
            class="image-container"
            :style="{
              transform: 'translate(' + currentPan.x + 'px, ' + currentPan.y + 'px) scale(' + scale + ')',
              transformOrigin: 'center center'
            }"
          >
            <div v-if="loading" class="loading-spinner">
              <v-progress-circular indeterminate color="primary"></v-progress-circular>
            </div>
            
            <div v-if="imageError" class="error-message">
              <v-icon size="48" color="error">mdi-image-broken</v-icon>
              <p>{{ imageError }}</p>
              <v-btn size="small" @click="imageError = null; loading = true">Retry</v-btn>
            </div>
            
            <img
              v-if="imageSrc && !imageError"
              :src="imageSrc"
              ref="imgRef"
              @load="loading = false"
              @error="imageError = 'Failed to load image'; loading = false"
              class="document-image"
              :style="{ display: loading ? 'none' : 'block' }"
            />
            
            <!-- Highlight Overlays -->
            <svg
              v-if="!loading && !imageError && imgRef"
              class="overlay-svg"
              :width="imgRef?.clientWidth || 0"
              :height="imgRef?.clientHeight || 0"
            >
              <!-- Existing field highlights -->
              <g v-for="highlight in highlightBoxes" :key="highlight.key">
                <polygon
                  :points="highlight.box.map((v, i) => (i % 2 === 0 ? v : v) + (i % 2 === 0 ? ',' : ' ')).join('')"
                  :fill="highlight.isEdited ? 'rgba(255, 152, 0, 0.3)' : 'rgba(33, 150, 243, 0.3)'"
                  :stroke="highlight.isEdited ? '#FF9800' : '#2196F3'"
                  stroke-width="2"
                  class="highlight-box"
                />
              </g>
              
              <!-- Drawing rectangle -->
              <rect
                v-if="drawingBox"
                :x="drawingBox.x"
                :y="drawingBox.y"
                :width="drawingBox.width"
                :height="drawingBox.height"
                fill="rgba(76, 175, 80, 0.3)"
                stroke="#4CAF50"
                stroke-width="2"
                stroke-dasharray="5,5"
                class="drawing-box"
              />
            </svg>
          </div>
        </div>
        
        <!-- Keyboard shortcuts hint -->
        <div class="shortcuts-hint">
          <v-icon size="small">mdi-keyboard</v-icon>
          <span>Arrow keys: Navigate | +/-: Zoom | F: Fit | 0: Reset</span>
        </div>
      </div>
    `
  };

  // Enhanced PDF Review Dialog Component
  window.PdfReviewDialog = {
    name: 'PdfReviewDialog',
    components: {
      ImagePageViewer: window.ImagePageViewer
    },
    props: {
      open: Boolean,
      analysis: Object,
      annotatedImage: Array,
      fileName: String,
      category: String,
      documentType: String
    },
    emits: ['update:open', 'approve', 'reject', 'save-draft'],
    setup(props, { emit }) {
      const { ref, computed, watch, reactive } = Vue;
      
      const activeTab = ref('fields');
      const searchQuery = ref('');
      const selectedField = ref(null);
      const drawingFieldKey = ref('');
      const editHistory = reactive({});
      const fieldAnnotations = reactive({});
      const exportFormat = ref('json');
      const showConfidenceThreshold = ref(true);
      const confidenceThreshold = ref(80);
      
      // Copy fields data to make it reactive
      const fields = ref({});
      
      watch(() => props.analysis?.combined_fields, (newFields) => {
        if (newFields) {
          fields.value = JSON.parse(JSON.stringify(newFields));
          Object.entries(fields.value).forEach(([key, field]) => {
            field._edited = false;
            field._originalValue = field.value;
            field._confidence = field.confidence || 95;
          });
        }
      }, { immediate: true });

      const base64Images = computed(() => {
        const images = [];
        if (props.analysis?.pdf_pages && Array.isArray(props.analysis.pdf_pages)) {
          props.analysis.pdf_pages.forEach((img) => {
            if (typeof img === 'string') {
              if (img.startsWith('data:image/')) {
                images.push(img);
              } else {
                images.push("data:image/png;base64," + img);
              }
            }
          });
        }
        return images;
      });

      const annotatedImages = computed(() => {
        if (!Array.isArray(props.annotatedImage)) return base64Images.value;
        return props.annotatedImage.filter(img => 
          img && typeof img === 'string' && 
          (img.startsWith('data:image/') || isValidBase64(img))
        ).map(img => 
          img.startsWith('data:image/') ? img : "data:image/png;base64," + img
        );
      });

      const filteredFields = computed(() => {
        let filtered = fields.value;
        
        // Apply search filter
        if (searchQuery.value) {
          const query = searchQuery.value.toLowerCase();
          filtered = Object.fromEntries(
            Object.entries(filtered).filter(([key, field]) => {
              return key.toLowerCase().includes(query) ||
                     (field.value && field.value.toString().toLowerCase().includes(query));
            })
          );
        }
        
        // Apply confidence threshold filter
        if (showConfidenceThreshold.value) {
          filtered = Object.fromEntries(
            Object.entries(filtered).filter(([key, field]) => {
              return (field._confidence || field.confidence || 0) >= confidenceThreshold.value;
            })
          );
        }
        
        return filtered;
      });

      const fieldStats = computed(() => {
        const total = Object.keys(fields.value).length;
        const edited = Object.values(fields.value).filter(f => f._edited).length;
        const highConfidence = Object.values(fields.value).filter(f => 
          (f._confidence || f.confidence || 0) >= 90
        ).length;
        
        return { total, edited, highConfidence };
      });

      const swiftCompliance = computed(() => {
        return props.analysis?.swift_compliance || {};
      });

      const ucpCompliance = computed(() => {
        return props.analysis?.ucp_compliance || {};
      });

      const complianceStats = computed(() => {
        const swiftTotal = Object.keys(swiftCompliance.value).length;
        const swiftCompliant = Object.values(swiftCompliance.value).filter(r => r.compliant).length;
        
        const ucpTotal = Object.keys(ucpCompliance.value).length;
        const ucpCompliant = Object.values(ucpCompliance.value).filter(r => r.compliant).length;
        
        return {
          swift: { total: swiftTotal, compliant: swiftCompliant },
          ucp: { total: ucpTotal, compliant: ucpCompliant }
        };
      });

      // Field operations
      function selectField(fieldKey) {
        selectedField.value = fieldKey;
      }

      function editField(fieldKey, newValue) {
        if (fields.value[fieldKey]) {
          if (!editHistory[fieldKey]) {
            editHistory[fieldKey] = [];
          }
          editHistory[fieldKey].push(fields.value[fieldKey].value);
          
          fields.value[fieldKey].value = newValue;
          fields.value[fieldKey]._edited = true;
        }
      }

      function revertField(fieldKey) {
        if (fields.value[fieldKey] && editHistory[fieldKey] && editHistory[fieldKey].length > 0) {
          fields.value[fieldKey].value = editHistory[fieldKey].pop();
          if (editHistory[fieldKey].length === 0) {
            fields.value[fieldKey]._edited = false;
          }
        }
      }

      function updateConfidence(fieldKey, confidence) {
        if (fields.value[fieldKey]) {
          fields.value[fieldKey]._confidence = confidence;
        }
      }

      function addAnnotation(fieldKey, annotation) {
        fieldAnnotations[fieldKey] = annotation;
      }

      function startDrawing(fieldKey) {
        drawingFieldKey.value = fieldKey;
        selectedField.value = fieldKey;
      }

      function handleBoundingBoxUpdate(data) {
        const { fieldKey, boundingBox, boundingPage } = data;
        if (fields.value[fieldKey]) {
          fields.value[fieldKey].bounding_box = boundingBox;
          fields.value[fieldKey].bounding_page = boundingPage;
          fields.value[fieldKey]._edited = true;
          fields.value[fieldKey]._redrawn = true;
          
          drawingFieldKey.value = '';
          
          // TODO: Trigger OCR on the new bounding box
          console.log('Updated bounding box for', fieldKey, boundingBox);
        }
      }

      // Export functions
      function exportData() {
        const exportData = {
          fileName: props.fileName,
          documentType: props.documentType,
          category: props.category,
          fields: fields.value,
          annotations: fieldAnnotations,
          compliance: {
            swift: swiftCompliance.value,
            ucp: ucpCompliance.value
          },
          metadata: {
            exportDate: new Date().toISOString(),
            totalFields: fieldStats.value.total,
            editedFields: fieldStats.value.edited
          }
        };

        let blob, filename;
        if (exportFormat.value === 'json') {
          blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
          filename = `${props.fileName || 'document'}_export.json`;
        } else if (exportFormat.value === 'csv') {
          const csv = convertToCSV(exportData);
          blob = new Blob([csv], { type: 'text/csv' });
          filename = `${props.fileName || 'document'}_export.csv`;
        }

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      }

      function convertToCSV(data) {
        const headers = ['Field Name', 'Value', 'Confidence', 'Edited', 'Annotation', 'Page'];
        const rows = [headers];
        
        Object.entries(data.fields).forEach(([key, field]) => {
          rows.push([
            key,
            field.value || '',
            field._confidence || field.confidence || '',
            field._edited ? 'Yes' : 'No',
            fieldAnnotations[key] || '',
            field.bounding_page || ''
          ]);
        });
        
        return rows.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
      }

      // Dialog actions
      function closeDialog() {
        selectedField.value = null;
        drawingFieldKey.value = '';
        emit('update:open', false);
      }

      function approve() {
        emit('approve', {
          fields: fields.value,
          annotations: fieldAnnotations,
          compliance: {
            swift: swiftCompliance.value,
            ucp: ucpCompliance.value
          }
        });
        closeDialog();
      }

      function reject() {
        emit('reject', {
          fields: fields.value,
          annotations: fieldAnnotations,
          compliance: {
            swift: swiftCompliance.value,
            ucp: ucpCompliance.value
          }
        });
        closeDialog();
      }

      function saveDraft() {
        emit('save-draft', {
          fields: fields.value,
          annotations: fieldAnnotations
        });
      }

      return {
        activeTab,
        searchQuery,
        selectedField,
        drawingFieldKey,
        fields,
        filteredFields,
        fieldStats,
        annotatedImages,
        swiftCompliance,
        ucpCompliance,
        complianceStats,
        exportFormat,
        showConfidenceThreshold,
        confidenceThreshold,
        fieldAnnotations,
        selectField,
        editField,
        revertField,
        updateConfidence,
        addAnnotation,
        startDrawing,
        handleBoundingBoxUpdate,
        exportData,
        closeDialog,
        approve,
        reject,
        saveDraft
      };
    },
    template: `
      <v-dialog 
        :model-value="open" 
        @update:model-value="$emit('update:open', $event)"
        fullscreen
        transition="dialog-bottom-transition"
        class="pdf-review-dialog"
      >
        <v-card class="d-flex flex-column">
          <!-- Header -->
          <v-toolbar color="primary" dark dense>
            <v-toolbar-title class="d-flex align-center">
              <v-icon class="mr-2">mdi-file-document-check</v-icon>
              <span>{{ fileName || 'Document Review' }}</span>
            </v-toolbar-title>
            
            <v-spacer></v-spacer>
            
            <div class="mr-4">
              <v-chip color="white" variant="outlined" class="mr-2">
                <v-icon start size="small">mdi-shape</v-icon>
                {{ category }}
              </v-chip>
              <v-chip color="white" variant="outlined">
                <v-icon start size="small">mdi-file</v-icon>
                {{ documentType }}
              </v-chip>
            </div>
            
            <v-btn icon @click="saveDraft" title="Save Draft">
              <v-icon>mdi-content-save</v-icon>
            </v-btn>
            
            <v-btn icon @click="closeDialog">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-toolbar>
          
          <!-- Main Content -->
          <v-card-text class="flex-grow-1 pa-0">
            <div class="pdf-review-content">
              <!-- Left Panel - Image Viewer -->
              <div class="viewer-panel">
                <image-page-viewer
                  :base64-images="annotatedImages"
                  :fields="fields"
                  :highlight-key="selectedField"
                  :highlight-edited-key="null"
                  :drawing-field-key="drawingFieldKey"
                  :category="category"
                  :document-type="documentType"
                  @update-bounding-box="handleBoundingBoxUpdate"
                />
              </div>
              
              <!-- Right Panel - Data & Compliance -->
              <div class="data-panel">
                <v-tabs v-model="activeTab" color="primary" grow>
                  <v-tab value="fields">
                    <v-icon start>mdi-form-textbox</v-icon>
                    Fields
                    <v-chip size="x-small" class="ml-2">{{ fieldStats.total }}</v-chip>
                  </v-tab>
                  <v-tab value="swift">
                    <v-icon start>mdi-bank</v-icon>
                    SWIFT
                    <v-chip 
                      size="x-small" 
                      class="ml-2"
                      :color="complianceStats.swift.compliant === complianceStats.swift.total ? 'success' : 'warning'"
                    >
                      {{ complianceStats.swift.compliant }}/{{ complianceStats.swift.total }}
                    </v-chip>
                  </v-tab>
                  <v-tab value="ucp">
                    <v-icon start>mdi-gavel</v-icon>
                    UCP600
                    <v-chip 
                      size="x-small" 
                      class="ml-2"
                      :color="complianceStats.ucp.compliant === complianceStats.ucp.total ? 'success' : 'warning'"
                    >
                      {{ complianceStats.ucp.compliant }}/{{ complianceStats.ucp.total }}
                    </v-chip>
                  </v-tab>
                </v-tabs>
                
                <v-window v-model="activeTab" class="data-window">
                  <!-- Fields Tab -->
                  <v-window-item value="fields">
                    <div class="fields-container">
                      <!-- Search and Filters -->
                      <div class="fields-toolbar">
                        <v-text-field
                          v-model="searchQuery"
                          density="compact"
                          variant="outlined"
                          prepend-inner-icon="mdi-magnify"
                          placeholder="Search fields..."
                          clearable
                          hide-details
                          class="flex-grow-1 mr-2"
                        />
                        
                        <v-checkbox
                          v-model="showConfidenceThreshold"
                          label="Min confidence"
                          hide-details
                          density="compact"
                          class="mr-2"
                        />
                        
                        <v-slider
                          v-if="showConfidenceThreshold"
                          v-model="confidenceThreshold"
                          :min="0"
                          :max="100"
                          :step="5"
                          hide-details
                          density="compact"
                          class="confidence-slider"
                          style="width: 150px"
                        >
                          <template v-slot:append>
                            <span class="text-caption">{{ confidenceThreshold }}%</span>
                          </template>
                        </v-slider>
                      </div>
                      
                      <!-- Field Stats -->
                      <div class="field-stats">
                        <v-chip size="small" variant="tonal" class="mr-2">
                          Total: {{ fieldStats.total }}
                        </v-chip>
                        <v-chip size="small" variant="tonal" color="warning" class="mr-2" v-if="fieldStats.edited > 0">
                          Edited: {{ fieldStats.edited }}
                        </v-chip>
                        <v-chip size="small" variant="tonal" color="success">
                          High Confidence: {{ fieldStats.highConfidence }}
                        </v-chip>
                      </div>
                      
                      <!-- Fields List -->
                      <div class="fields-list">
                        <div
                          v-for="(field, fieldKey) in filteredFields"
                          :key="fieldKey"
                          class="field-item"
                          :class="{
                            'field-selected': selectedField === fieldKey,
                            'field-edited': field._edited,
                            'field-redrawn': field._redrawn
                          }"
                          @click="selectField(fieldKey)"
                        >
                          <div class="field-header">
                            <span class="field-name">{{ fieldKey }}</span>
                            <div class="field-actions">
                              <v-chip
                                size="small"
                                :color="field._confidence >= 90 ? 'success' : field._confidence >= 70 ? 'warning' : 'error'"
                                variant="tonal"
                                @click.stop="selectField(fieldKey)"
                              >
                                {{ field._confidence || field.confidence || 0 }}%
                              </v-chip>
                              
                              <v-btn
                                icon
                                size="x-small"
                                variant="text"
                                @click.stop="startDrawing(fieldKey)"
                                :color="drawingFieldKey === fieldKey ? 'success' : 'default'"
                                title="Redraw bounding box"
                              >
                                <v-icon size="small">mdi-vector-square</v-icon>
                              </v-btn>
                              
                              <v-btn
                                v-if="field._edited"
                                icon
                                size="x-small"
                                variant="text"
                                color="warning"
                                @click.stop="revertField(fieldKey)"
                                title="Revert changes"
                              >
                                <v-icon size="small">mdi-undo</v-icon>
                              </v-btn>
                            </div>
                          </div>
                          
                          <v-text-field
                            :model-value="field.value"
                            @update:model-value="editField(fieldKey, $event)"
                            density="compact"
                            variant="outlined"
                            hide-details
                            class="field-value mt-2"
                          />
                          
                          <v-expand-transition>
                            <div v-if="selectedField === fieldKey" class="field-details mt-2">
                              <v-textarea
                                :model-value="fieldAnnotations[fieldKey]"
                                @update:model-value="addAnnotation(fieldKey, $event)"
                                label="Notes"
                                density="compact"
                                variant="outlined"
                                rows="2"
                                hide-details
                              />
                              
                              <div class="confidence-adjuster mt-2">
                                <span class="text-caption">Adjust Confidence:</span>
                                <v-slider
                                  :model-value="field._confidence || field.confidence"
                                  @update:model-value="updateConfidence(fieldKey, $event)"
                                  :min="0"
                                  :max="100"
                                  :step="5"
                                  density="compact"
                                  hide-details
                                >
                                  <template v-slot:append>
                                    <v-text-field
                                      :model-value="field._confidence || field.confidence"
                                      @update:model-value="updateConfidence(fieldKey, $event)"
                                      type="number"
                                      density="compact"
                                      style="width: 60px"
                                      hide-details
                                      suffix="%"
                                    />
                                  </template>
                                </v-slider>
                              </div>
                            </div>
                          </v-expand-transition>
                        </div>
                      </div>
                    </div>
                  </v-window-item>
                  
                  <!-- SWIFT Compliance Tab -->
                  <v-window-item value="swift">
                    <div class="compliance-container">
                      <div class="compliance-summary">
                        <v-progress-circular
                          :model-value="(complianceStats.swift.compliant / complianceStats.swift.total) * 100"
                          :size="80"
                          :width="8"
                          :color="complianceStats.swift.compliant === complianceStats.swift.total ? 'success' : 'warning'"
                        >
                          {{ Math.round((complianceStats.swift.compliant / complianceStats.swift.total) * 100) || 0 }}%
                        </v-progress-circular>
                        <div class="ml-4">
                          <h3>SWIFT Compliance</h3>
                          <p class="text-body-2 text-grey">
                            {{ complianceStats.swift.compliant }} of {{ complianceStats.swift.total }} rules passed
                          </p>
                        </div>
                      </div>
                      
                      <v-list density="compact" class="compliance-list">
                        <v-list-item
                          v-for="(rule, fieldKey) in swiftCompliance"
                          :key="fieldKey"
                          :class="{
                            'compliance-pass': rule.compliant,
                            'compliance-fail': !rule.compliant
                          }"
                        >
                          <template v-slot:prepend>
                            <v-icon :color="rule.compliant ? 'success' : 'error'">
                              {{ rule.compliant ? 'mdi-check-circle' : 'mdi-close-circle' }}
                            </v-icon>
                          </template>
                          
                          <v-list-item-title>{{ fieldKey }}</v-list-item-title>
                          <v-list-item-subtitle>{{ rule.reason || 'Compliant' }}</v-list-item-subtitle>
                        </v-list-item>
                      </v-list>
                    </div>
                  </v-window-item>
                  
                  <!-- UCP600 Compliance Tab -->
                  <v-window-item value="ucp">
                    <div class="compliance-container">
                      <div class="compliance-summary">
                        <v-progress-circular
                          :model-value="(complianceStats.ucp.compliant / complianceStats.ucp.total) * 100"
                          :size="80"
                          :width="8"
                          :color="complianceStats.ucp.compliant === complianceStats.ucp.total ? 'success' : 'warning'"
                        >
                          {{ Math.round((complianceStats.ucp.compliant / complianceStats.ucp.total) * 100) || 0 }}%
                        </v-progress-circular>
                        <div class="ml-4">
                          <h3>UCP600 Compliance</h3>
                          <p class="text-body-2 text-grey">
                            {{ complianceStats.ucp.compliant }} of {{ complianceStats.ucp.total }} rules passed
                          </p>
                        </div>
                      </div>
                      
                      <v-list density="compact" class="compliance-list">
                        <v-list-item
                          v-for="(rule, fieldKey) in ucpCompliance"
                          :key="fieldKey"
                          :class="{
                            'compliance-pass': rule.compliant,
                            'compliance-fail': !rule.compliant,
                            'compliance-warning': rule.compliant === 'warning'
                          }"
                        >
                          <template v-slot:prepend>
                            <v-icon 
                              :color="rule.compliant === true ? 'success' : rule.compliant === 'warning' ? 'warning' : 'error'"
                            >
                              {{ rule.compliant === true ? 'mdi-check-circle' : rule.compliant === 'warning' ? 'mdi-alert-circle' : 'mdi-close-circle' }}
                            </v-icon>
                          </template>
                          
                          <v-list-item-title>{{ fieldKey }}</v-list-item-title>
                          <v-list-item-subtitle>{{ rule.reason || 'Compliant' }}</v-list-item-subtitle>
                        </v-list-item>
                      </v-list>
                    </div>
                  </v-window-item>
                </v-window>
              </div>
            </div>
          </v-card-text>
          
          <!-- Footer Actions -->
          <v-card-actions class="dialog-footer">
            <div class="d-flex align-center">
              <v-select
                v-model="exportFormat"
                :items="['json', 'csv']"
                label="Export format"
                density="compact"
                variant="outlined"
                hide-details
                style="width: 120px"
                class="mr-2"
              />
              <v-btn variant="tonal" @click="exportData">
                <v-icon start>mdi-download</v-icon>
                Export
              </v-btn>
            </div>
            
            <v-spacer></v-spacer>
            
            <v-btn variant="text" @click="closeDialog">Cancel</v-btn>
            <v-btn color="error" variant="tonal" @click="reject">
              <v-icon start>mdi-close-circle</v-icon>
              Reject
            </v-btn>
            <v-btn color="success" variant="flat" @click="approve">
              <v-icon start>mdi-check-circle</v-icon>
              Approve
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    `
  };

  // Add required styles
  const style = document.createElement('style');
  style.textContent = `
    /* PDF Review Dialog Styles */
    .pdf-review-dialog .v-card {
      height: 100vh;
    }
    
    .pdf-review-content {
      display: flex;
      height: 100%;
      gap: 0;
    }
    
    .viewer-panel {
      flex: 1;
      background: #f5f5f5;
      display: flex;
      flex-direction: column;
      min-width: 50%;
    }
    
    .data-panel {
      width: 500px;
      display: flex;
      flex-direction: column;
      background: white;
      border-left: 1px solid #e0e0e0;
    }
    
    /* Image Viewer Styles */
    .image-viewer-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      position: relative;
    }
    
    .viewer-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 16px;
      background: white;
      border-bottom: 1px solid #e0e0e0;
      gap: 16px;
    }
    
    .toolbar-section {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .page-indicator {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 14px;
    }
    
    .page-input {
      width: 50px;
      padding: 4px 8px;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
      text-align: center;
    }
    
    .page-total {
      color: #666;
    }
    
    .zoom-level {
      min-width: 50px;
      text-align: center;
      font-size: 14px;
      color: #666;
    }
    
    .viewer-content {
      flex: 1;
      overflow: hidden;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f5f5f5;
    }
    
    .image-container {
      position: relative;
      transition: transform 0.2s ease;
      transform-origin: center center;
    }
    
    .document-image {
      max-width: 100%;
      max-height: 100%;
      display: block;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .overlay-svg {
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: none;
    }
    
    .highlight-box {
      cursor: pointer;
      transition: opacity 0.2s;
    }
    
    .highlight-box:hover {
      opacity: 0.8;
    }
    
    .drawing-box {
      animation: dash 0.5s linear infinite;
    }
    
    @keyframes dash {
      to {
        stroke-dashoffset: -10;
      }
    }
    
    .shortcuts-hint {
      position: absolute;
      bottom: 8px;
      right: 8px;
      background: rgba(0,0,0,0.7);
      color: white;
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .loading-spinner,
    .error-message {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      padding: 32px;
    }
    
    /* Data Panel Styles */
    .data-window {
      flex: 1;
      overflow: hidden;
    }
    
    .fields-container,
    .compliance-container {
      height: 100%;
      display: flex;
      flex-direction: column;
      padding: 16px;
    }
    
    .fields-toolbar {
      display: flex;
      align-items: center;
      margin-bottom: 16px;
      gap: 8px;
    }
    
    .field-stats {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
    }
    
    .fields-list {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    
    .field-item {
      background: #f5f5f5;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 12px;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .field-item:hover {
      background: #eeeeee;
      border-color: #bdbdbd;
    }
    
    .field-item.field-selected {
      background: #e3f2fd;
      border-color: #2196f3;
    }
    
    .field-item.field-edited {
      border-left: 4px solid #ff9800;
    }
    
    .field-item.field-redrawn {
      border-left: 4px solid #4caf50;
    }
    
    .field-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .field-name {
      font-weight: 500;
      color: #424242;
    }
    
    .field-actions {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    
    .field-value {
      margin-top: 8px;
    }
    
    .field-details {
      padding-top: 12px;
      border-top: 1px solid #e0e0e0;
    }
    
    .confidence-adjuster {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    
    /* Compliance Styles */
    .compliance-summary {
      display: flex;
      align-items: center;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 8px;
      margin-bottom: 16px;
    }
    
    .compliance-list {
      flex: 1;
      overflow-y: auto;
    }
    
    .compliance-pass {
      background: #e8f5e9;
    }
    
    .compliance-fail {
      background: #ffebee;
    }
    
    .compliance-warning {
      background: #fff8e1;
    }
    
    /* Footer Styles */
    .dialog-footer {
      padding: 16px 24px;
      border-top: 1px solid #e0e0e0;
      background: #fafafa;
    }
    
    /* Responsive */
    @media (max-width: 1280px) {
      .data-panel {
        width: 400px;
      }
    }
    
    @media (max-width: 960px) {
      .pdf-review-content {
        flex-direction: column;
      }
      
      .viewer-panel {
        min-width: auto;
        height: 50%;
      }
      
      .data-panel {
        width: 100%;
        height: 50%;
        border-left: none;
        border-top: 1px solid #e0e0e0;
      }
    }
  `;
  document.head.appendChild(style);

  // Export for global use
  window.isValidBase64 = isValidBase64;
})();