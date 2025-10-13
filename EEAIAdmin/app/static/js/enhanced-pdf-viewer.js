(function() {
  // Check for Vue and Vuetify dependencies
  if (!window.Vue) {
    console.error('Vue.js is not loaded. Please include Vue.js.');
    return;
  }
  if (!window.Vuetify) {
    console.error('Vuetify is not loaded. Please include Vuetify.');
    return;
  }

  // Enhanced base64 validation
  function isValidBase64(str) {
    if (!str || typeof str !== 'string') return false;
    try {
      return btoa(atob(str)) === str;
    } catch (err) {
      return false;
    }
  }

  // ---- Enhanced Image Page Viewer Component ----
  if (window.ImagePageViewer) return;

  window.ImagePageViewer = {
    props: {
      base64Images: {
        type: Array,
        required: true,
        default: () => [],
        validator: arr => Array.isArray(arr)
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
  document_type: {
    type: String,
    default: 'N/A'
  }
    },
    emits: ['update-bounding-box'],
    setup(props, { emit }) {
      const { ref, computed, watch,toRefs  } = Vue;
      const { highlightKey, highlightEditedKey } = toRefs(props);
      const pageNum = ref(props.initialPage || 1);
      const loading = ref(false);
      const imageError = ref(null);
      const imgRef = ref(null);
      const imgDimensions = ref({ width: 600, height: 800 });
      const scale = ref(1); // 🔍 Zoom scale (default 1x)
      
      // Drawing state
      const isDrawing = ref(false);
      const drawingStart = ref({ x: 0, y: 0 });
      const drawingEnd = ref({ x: 0, y: 0 });
      const currentDrawing = ref(null);
      const localDrawingFieldKey = ref('');
      
      // Watch for external drawing field key changes
      watch(() => props.drawingFieldKey, (newVal) => {
        localDrawingFieldKey.value = newVal;
      });

      const pageCount = computed(() => {
        const count = (props.base64Images && props.base64Images.length) ? props.base64Images.length : 0;
        console.log('ImagePageViewer: pageCount computed', count);
        return count;
      });

      const imageSrc = computed(() => {
        if (!props.base64Images || props.base64Images.length === 0) {
          console.warn('ImagePageViewer: No base64 images provided');
          return null;
        }

        let data = props.base64Images[pageNum.value - 1];
        if (!data) {
          console.warn('ImagePageViewer: No image data for page', pageNum.value);
          return null;
        }

        console.log('ImagePageViewer: Processing image data for page', pageNum.value, {
          dataLength: data.length,
          startsWithData: data.startsWith("data:"),
          first50Chars: data.substring(0, 50)
        });

        // If already a complete data URL
        if (data.startsWith("data:image/")) {
          return data;
        }

        // If it looks like base64, try to create data URL
        if (isValidBase64(data)) {
          // Try PNG first as it's more universal
          return "data:image/png;base64," + data;
        }

        // If validation fails, still try to display (might be URL encoded or have extra chars)
        console.warn('ImagePageViewer: Data failed validation, trying anyway');
        return "data:image/png;base64," + data;
      });

      watch(() => props.base64Images, (val) => {
        const length = (val && val.length) ? val.length : 0;
        console.log('ImagePageViewer: base64Images updated', length, 'images');
      }, { immediate: true });

      watch(imageSrc, (newSrc) => {
        if (newSrc) {
          imageError.value = null;
          loading.value = true;
          console.log('ImagePageViewer: imageSrc changed for page', pageNum.value);
        }
      });
      watch(() => props.initialPage, (newVal) => {
  if (newVal !== pageNum.value) {
    pageNum.value = newVal;
  }
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
      const shouldHighlight =
        (key === highlightKey.value || key === highlightEditedKey.value) &&
        field?.bounding_page === pageNum.value;

      return shouldHighlight;
    })
    .map(([key, field]) => {
      let bbox = field.bounding_box;
      
      // Handle different bounding box formats
      if (!bbox) {
        console.warn(`No bounding box for field ${key}`);
        return null;
      }
      
      // If it's a Proxy or object, try to convert to array
      if (!Array.isArray(bbox)) {
        try {
          // Try to extract array from Proxy or object
          bbox = Array.from(bbox);
        } catch (e) {
          // If that fails, check if it has numeric properties
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

      // Check if we have a valid bounding box
      if (!Array.isArray(bbox) || bbox.length === 0) {
        console.warn(`Invalid bounding box for field ${key}:`, bbox);
        return null;
      }

      // Convert 4-coordinate format to 8-coordinate format if needed
      if (bbox.length === 4) {
        // We have [x1, y1, x2, y2] - convert to full polygon coordinates
        const [x1, y1, x2, y2] = bbox;
        bbox = [
          x1, y1,  // top-left
          x2, y1,  // top-right
          x2, y2,  // bottom-right
          x1, y2   // bottom-left
        ];
      }

      if (bbox.length !== 8 || !bbox.every(n => typeof n === 'number' && !isNaN(n))) {
        console.warn(`Invalid bounding box for field ${key}:`, bbox, 'Expected array of 4 or 8 numbers');
        return null;
      }

      const dpi = 72;
      const pixelBox = bbox.map((coord, index) => {
        const px = coord * dpi;
        return index % 2 === 0 ? px * scaleX : px * scaleY;
      });

      console.log(`Highlight box for ${key}:`, {
        originalBbox: field.bounding_box,
        convertedBbox: bbox,
        pixelBox: pixelBox,
        page: field.bounding_page,
        currentPage: pageNum.value,
        scales: { scaleX, scaleY }
      });

      return {
        key,
        box: pixelBox
      };
    })
    .filter(Boolean);
});
        watch(highlightBoxes, (boxes) => {
  if (boxes.length > 0) {
    console.log('Highlight boxes:', boxes);
    console.log('Image dimensions:', imgDimensions.value);
  }
}, { immediate: true });
      function handleImageLoadSuccess() {
  console.log('ImagePageViewer: Image loaded successfully for page', pageNum.value);
  imageError.value = null;
  loading.value = false;

  const img = imgRef.value;
  if (img && img.complete && img.naturalWidth > 0 && img.naturalHeight > 0) {
    imgDimensions.value = {
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      displayWidth: img.clientWidth,
      displayHeight: img.clientHeight
    };
    console.log('Image dimensions captured:', imgDimensions.value);
  } else {
    console.warn('ImagePageViewer: imgRef is null or not fully loaded');
  }
}

      function handleImageLoadError(event) {
        const error = `Failed to load image for page ${pageNum.value}`;
        console.error('ImagePageViewer:', error, event);
        imageError.value = error;
        loading.value = false;
      }

      function nextPage() {
        if (pageNum.value < pageCount.value) pageNum.value += 1;
      }

      function prevPage() {
        if (pageNum.value > 1) pageNum.value -= 1;
      }

      function setPage(num) {
        if (num >= 1 && num <= pageCount.value) pageNum.value = num;
      }
       function zoomIn() {
        scale.value = Math.min(scale.value + 0.1, 3); // Max 3x
      }

      function zoomOut() {
        scale.value = Math.max(scale.value - 0.1, 0.5); // Min 0.5x
      }
      
      // Drawing functions
      function handleMouseDown(event) {
        console.log('handleMouseDown called, drawingFieldKey:', localDrawingFieldKey.value);
        if (!imgRef.value || !localDrawingFieldKey.value) {
          console.log('No imgRef or drawingFieldKey, returning');
          return;
        }
        
        event.preventDefault();
        isDrawing.value = true;
        
        const rect = event.currentTarget.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        drawingStart.value = { x, y };
        drawingEnd.value = { x, y };
        console.log('Started drawing at:', { x, y });
      }
      
      function handleMouseMove(event) {
        if (!isDrawing.value || !imgRef.value) return;
        
        const rect = event.currentTarget.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        drawingEnd.value = { x, y };
      }
      
      function handleMouseUp(event) {
        if (!isDrawing.value || !imgRef.value) return;
        
        const displayWidth = imgRef.value.clientWidth;
        const displayHeight = imgRef.value.clientHeight;
        const naturalWidth = imgRef.value.naturalWidth;
        const naturalHeight = imgRef.value.naturalHeight;
        
        const scaleX = naturalWidth / displayWidth;
        const scaleY = naturalHeight / displayHeight;
        
        // Convert pixel coordinates to PDF coordinates (inches)
        const dpi = 72;
        const x1 = Math.min(drawingStart.value.x, drawingEnd.value.x) * scaleX / dpi;
        const y1 = Math.min(drawingStart.value.y, drawingEnd.value.y) * scaleY / dpi;
        const x2 = Math.max(drawingStart.value.x, drawingEnd.value.x) * scaleX / dpi;
        const y2 = Math.max(drawingStart.value.y, drawingEnd.value.y) * scaleY / dpi;
        
        // Only emit if we have a valid box (not just a click)
        if (Math.abs(drawingEnd.value.x - drawingStart.value.x) > 5 && 
            Math.abs(drawingEnd.value.y - drawingStart.value.y) > 5) {
          emit('update-bounding-box', {
            fieldKey: localDrawingFieldKey.value,
            boundingBox: [x1, y1, x2, y2],
            boundingPage: pageNum.value
          });
        }
        
        isDrawing.value = false;
      }
      
      const drawingBox = computed(() => {
        if (!isDrawing.value) return null;
        
        const x = Math.min(drawingStart.value.x, drawingEnd.value.x);
        const y = Math.min(drawingStart.value.y, drawingEnd.value.y);
        const width = Math.abs(drawingEnd.value.x - drawingStart.value.x);
        const height = Math.abs(drawingEnd.value.y - drawingStart.value.y);
        
        return { x, y, width, height };
      });

      return {
        pageNum,
        pageCount,
        loading,
        imageError,
        imageSrc,
        highlightBoxes,
        nextPage,
        prevPage,
        setPage,
        imgRef,
        imgDimensions,
        handleImageLoadSuccess,
        handleImageLoadError,
        scale,
        zoomIn,
        zoomOut,
        isDrawing,
        drawingBox,
        handleMouseDown,
        handleMouseMove,
        handleMouseUp,
        drawingFieldKey: localDrawingFieldKey
      };
    },
    template: `
      <!--div class="flex flex-col items-center gap-4 w-full max-w-4xl mx-auto p-4 bg-white dark:bg-gray-900 rounded-lg shadow-lg">
        <div class="flex flex-col sm:flex-row items-center justify-between w-full bg-gray-100 dark:bg-gray-800 rounded-md p-2">
          <div class="flex flex-col sm:flex-row items-center gap-2 mb-2 sm:mb-0">
            <v-btn size="small" @click="prevPage" :disabled="pageNum <= 1" variant="text" color="primary" aria-label="Previous page">
              <v-icon>mdi-chevron-left</v-icon>
            </v-btn>
            <v-text-field
              v-model.number="pageNum"
              type="number"
              density="compact"
              variant="outlined"
              hide-details
              class="w-20"
              :min="1"
              :max="pageCount"
              @input="setPage(pageNum)"
              aria-label="Current page number"
            />
            <span class="text-sm text-gray-600 dark:text-gray-300">of {{ pageCount }}</span>
            <v-btn size="small" @click="nextPage" :disabled="pageNum >= pageCount" variant="text" color="primary" aria-label="Next page">
              <v-icon>mdi-chevron-right</v-icon>
            </v-btn>
          </div>
        </div-->

        <div class="relative w-full max-w-2xl border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden shadow-md" style="min-height: 400px;">
          <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800">
            <v-progress-circular indeterminate color="primary" size="48"></v-progress-circular>
          </div>

          <div v-if="imageError" class="absolute inset-0 flex flex-col items-center justify-center bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 p-4">
            <v-icon size="48" class="mb-2">mdi-image-broken</v-icon>
            <span class="text-sm font-bold text-center">{{ imageError }}</span>
            <v-btn size="small" color="primary" @click="() => { imageError = null; loading = true; }" class="mt-2">
              Retry
            </v-btn>
          </div>
           <div class="flex justify-center w-full h-full">
      <div class="relative" :style="{ transform: 'scale(' + scale + ')', transformOrigin: 'top center' }">
      <div v-if="!imageSrc && !loading && !imageError" class="text-gray-500 text-sm text-center p-4">
  No original PDF image available to display.
</div>

           <div 
          v-if="imageSrc && !imageError" 
          class="relative inline-block"
          :class="{ 'drawing-cursor': drawingFieldKey }"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseUp"
        >
           <img
          :src="imageSrc"
          ref="imgRef"
          alt="Document page image"
          class="image-fade-in"
          :class="{ 'loaded': !loading }"
          @error="handleImageLoadError"
          @load="handleImageLoadSuccess"
          style="display: block; max-width: 100%; max-height: 800px; pointer-events: none;"
        />

      <svg
          v-if="(highlightBoxes.length || drawingBox) && imageSrc && !imageError && !loading && imgRef"
          class="absolute top-0 left-0 pointer-events-none"
         :width="imgRef ? imgRef.clientWidth : imgDimensions.displayWidth"
         :height="imgRef ? imgRef.clientHeight : imgDimensions.displayHeight"
        >
         <polygon
  v-for="hb in highlightBoxes"
  :key="hb.key"
  :points="[
    hb.box[0] + ',' + hb.box[1],
    hb.box[2] + ',' + hb.box[3],
    hb.box[4] + ',' + hb.box[5],
    hb.box[6] + ',' + hb.box[7]
  ].join(' ')"
  :stroke="hb.key === highlightEditedKey ? '#F59E0B' : '#2563EB'"
  stroke-width="3"
  fill="rgba(255, 0, 0, 0.2)"
  style="pointer-events: auto; cursor: pointer;"
/>
        <!-- Drawing rectangle -->
        <rect
          v-if="drawingBox"
          :x="drawingBox.x"
          :y="drawingBox.y"
          :width="drawingBox.width"
          :height="drawingBox.height"
          stroke="#10B981"
          stroke-width="2"
          fill="rgba(16, 185, 129, 0.2)"
          stroke-dasharray="5,5"
        />
        </svg>
        </div>

        </div>
      </div>
      <style>
        .cursor-crosshair {
          cursor: crosshair !important;
        }
      </style>
    `
  };

  // -------- Enhanced PDF Review Dialog Component -----------
 window.PdfReviewDialog = {
  name: "PdfReviewDialog",
  components: {
    ImagePageViewer: window.ImagePageViewer
  },
  props: {
    open: Boolean,
    pdfUrl: String,
    analysis: Object,
    annotatedImage: {
    type: Array,
    default: () => []
  },
    fileName: String,
   category: String,
  document_type: String,
  },
  emits: ["update:open", "approve", "reject"],
    setup(props, { emit }) {
      const { ref, computed, watch } = Vue;
      const tab = ref("entities");
      const showAnnotated = ref(false);
      const highlightKey = ref("");
      const highlightEditedKey = ref("");
      const searchQuery = ref("");
      const annotations = ref({});
      const editHistory = ref({});
      const exportFormat = ref("json");
      const pageViewer = ref(null);
      const fields = ref({});


        const currentPageClassification = computed(() => {
      if (!props.analysis || !props.analysis.page_classifications || !pageViewer.value) {
        return { category: 'N/A', document_type: 'N/A' };
      }

      // Get the current page number (1-indexed)
      const currentPage = pageViewer.value.pageNum;

      // Find the classification for this page
      const classification = props.analysis.page_classifications.find(
        c => c.page_number === currentPage
      );

      return classification || { category: 'N/A', document_type: 'N/A' };
    });


      watch(() => props.analysis && props.analysis.combined_fields, newVal => {
        if (newVal) {
          fields.value = JSON.parse(JSON.stringify(newVal));
          Object.values(fields.value).forEach(f => {
            f._edited = false;
            f._originalValue = f.value;
          });
          console.log('PdfReviewDialog: Fields updated', Object.keys(fields.value).length, 'fields');
        }
      }, { immediate: true });

    const base64Images = computed(() => {
  const images = [];

  if (props.analysis?.pdf_pages && Array.isArray(props.analysis.pdf_pages)) {
    props.analysis.pdf_pages.forEach((img, idx) => {
      if (typeof img === 'string') {
        if (img.startsWith('data:image/')) {
          images.push(img);
        } else if (isValidBase64(img)) {
          images.push("data:image/png;base64," + img);
        } else {
          console.warn("❌ Invalid base64 string at index", idx, "value:", img.substring(0, 50));
        }
      } else {
        console.warn("❌ Non-string item in pdf_pages at index", idx, "->", img);
      }
    });
  } else {
    console.warn("❌ Missing or invalid props.analysis.pdf_pages:", props.analysis?.pdf_pages);
  }

  console.log("✅ Computed base64Images with", images.length, "valid images");
  return images;
});



      const annotatedImages = computed(() => {
  if (!Array.isArray(props.annotatedImage)) return [];

  return props.annotatedImage.filter(img =>
    img && (typeof img === 'string') &&
    (img.startsWith('data:image/') || isValidBase64(img))
  );
});

      const imagesToShow = computed(() => {
        const images = showAnnotated.value ? annotatedImages.value : base64Images.value;
        console.log('PdfReviewDialog: imagesToShow computed', images.length, 'images', showAnnotated.value ? '(annotated)' : '(original)');
        console.log("Full analysis.pdf_pages:", props.analysis?.pdf_pages);
        return images;
      });

      const filteredFields = computed(() => {
        if (!searchQuery.value) return fields.value;
        const query = searchQuery.value.toLowerCase();
        return Object.fromEntries(
          Object.entries(fields.value).filter(([fieldKey, field]) => {
            const fieldKeyMatch = fieldKey.toLowerCase().includes(query);
            const valueMatch = field.value && field.value.toLowerCase().includes(query);
            return fieldKeyMatch || valueMatch;
          })
        );
      });

      const swiftResult = computed(() => {
        if (props.analysis && props.analysis.per_page && props.analysis.per_page.length > 0) {
          return props.analysis.per_page[0].swift_result || {};
        }
        return {};
      });

      const ucpResult = computed(() => {
        if (props.analysis && props.analysis.per_page && props.analysis.per_page.length > 0) {
          return props.analysis.per_page[0].ucp600_result || {};
        }
        return {};
      });

      const swiftSummary = computed(() => {
        const total = Object.keys(swiftResult.value).length;
        const compliant = Object.values(swiftResult.value).filter(r => r.compliance).length;
        return total ? `${compliant}/${total} fields compliant` : "No SWIFT data";
      });

      const ucpSummary = computed(() => {
        const total = Object.keys(ucpResult.value).length;
        const errors = Object.values(ucpResult.value).filter(r => r.error && r.error !== "None").length;
        return total ? `${total - errors}/${total} fields valid` : "No UCP600 data";
      });

      function onFieldEdit(fieldKey, value) {
        if (fields.value[fieldKey]) {
          if (!editHistory.value[fieldKey]) editHistory.value[fieldKey] = [];
          editHistory.value[fieldKey].push(fields.value[fieldKey].value);
          fields.value[fieldKey].value = value;
          fields.value[fieldKey]._edited = true;
          highlightEditedKey.value = fieldKey;
        }
      }

      function revertField(fieldKey) {
        if (fields.value[fieldKey] && fields.value[fieldKey]._edited) {
          fields.value[fieldKey].value = fields.value[fieldKey]._originalValue;
          fields.value[fieldKey]._edited = false;
          editHistory.value[fieldKey] = [];
          if (highlightEditedKey.value === fieldKey) highlightEditedKey.value = "";
        }
      }


      function onConfidenceClick(fieldKey) {
  const field = fields.value[fieldKey];
  if (!field) return;

  // Set the highlight key
  highlightKey.value = fieldKey === highlightKey.value ? "" : fieldKey;

  // Automatically go to the correct page
  if (field.bounding_page && pageViewer.value?.setPage) {
    pageViewer.value.setPage(field.bounding_page);
    console.log(`Navigating to page ${field.bounding_page} for field ${fieldKey}`);
  }
}

      function closeDialog() {
        highlightKey.value = "";
        highlightEditedKey.value = "";
        showAnnotated.value = false;
        searchQuery.value = "";
        annotations.value = {};
        editHistory.value = {};
        emit("update:open", false);
      }

      function approve() {
        emit("approve", { fields: fields.value, annotations: annotations.value });
      }

      function reject() {
        emit("reject", { fields: fields.value, annotations: annotations.value });
      }

      function exportData() {
        const data = {
          fields: fields.value,
          annotations: annotations.value
        };
        let blob, filename;
        if (exportFormat.value === "json") {
          blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
          filename = `${props.fileName || "document"}-export.json`;
        } else {
          const csv = [
            ["Key", "Value", "Confidence", "Description", "Edited", "Annotation", "BoundingBox", "Page"].join(","),
            ...Object.entries(fields.value).map(([fieldKey, f]) => [
              `"${fieldKey}"`,
              `"${f.value || ""}"`,
              f.confidence || "",
              `"${f.desc || ""}"`,
              f._edited ? "Yes" : "No",
              `"${annotations.value[fieldKey] || ""}"`,
              `"${f.bounding_box || ""}"`,
              f.bounding_page || ""
            ].join(","))
          ].join("\n");
          blob = new Blob([csv], { type: "text/csv" });
          filename = `${props.fileName || "document"}-export.csv`;
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      }
      
      function handleBoundingBoxUpdate(data) {
        const { fieldKey, boundingBox, boundingPage } = data;
        if (fields.value[fieldKey]) {
          fields.value[fieldKey].bounding_box = boundingBox;
          fields.value[fieldKey].bounding_page = boundingPage;
          fields.value[fieldKey]._edited = true;
          fields.value[fieldKey]._boundingBoxUpdated = true;
          
          // TODO: Here you would typically call an OCR service to extract text from the new bounding box
          // For now, we'll just mark it as updated
          console.log(`Updated bounding box for ${fieldKey}:`, boundingBox);
          
          // Update the highlight
          highlightEditedKey.value = fieldKey;
          
          // Exit drawing mode
          drawingMode.value = false;
          selectedFieldForRedraw.value = '';
        }
      }
      
      const drawingMode = ref(false);
      const selectedFieldForRedraw = ref('');
      
      function startRedrawing(fieldKey) {
        console.log('Starting redraw for field:', fieldKey);
        selectedFieldForRedraw.value = fieldKey;
        drawingMode.value = true;
        highlightKey.value = fieldKey;
        
        // Navigate to the correct page
        const field = fields.value[fieldKey];
        if (field && field.bounding_page && pageViewer.value?.setPage) {
          pageViewer.value.setPage(field.bounding_page);
        }
        
        // Use nextTick to ensure the component is updated
        Vue.nextTick(() => {
          if (pageViewer.value) {
            console.log('pageViewer available:', pageViewer.value);
          }
        });
      }

      return {
        tab, showAnnotated, highlightKey, highlightEditedKey, fields, filteredFields,
        searchQuery, annotations, editHistory, exportFormat, imagesToShow,
        swiftResult, ucpResult, swiftSummary, ucpSummary,
        onFieldEdit, revertField,
        onConfidenceClick, closeDialog, approve, reject, exportData,
        pageViewer,currentPageClassification,
        handleBoundingBoxUpdate, startRedrawing, drawingMode, selectedFieldForRedraw, annotatedImages
      };
    },
    template: `
      <v-dialog v-model="open" max-width="1280px" persistent scrollable>
        <v-card>
          <v-card-title class="bg-gray-100 dark:bg-gray-800 flex items-center gap-3 py-4 px-6">
            <v-icon size="24" color="primary">mdi-file-document-outline</v-icon>
            <span class="text-xl font-semibold">{{ fileName }}</span>
            <v-spacer />
            <v-btn icon @click="closeDialog" aria-label="Close dialog">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>
          <!-- ✅ Category and Document Type - Styled -->
<div class="px-6 pt-3 pb-2">
  <div class="flex items-center gap-6 bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-3 shadow-sm border border-gray-200 dark:border-gray-700">
    <div class="flex items-center gap-2 text-gray-700 dark:text-gray-300 text-sm">
      <v-icon size="18" color="primary">mdi-shape-outline</v-icon>
      <span><strong>Category:</strong> {{ currentPageClassification.category }}</span>
    </div>
    <div class="flex items-center gap-2 text-gray-700 dark:text-gray-300 text-sm">
      <v-icon size="18" color="primary">mdi-file-document</v-icon>
      <span><strong>Document Type:</strong> {{ currentPageClassification.document_type }}</span>
    </div>
  </div>
</div>


          <v-card-text class="p-0">
            <div class="flex flex-col lg:flex-row gap-6 p-6">
              <div class="w-full lg:w-1/2 min-w-[320px]">
                <!-- Drawing mode indicator -->
                <v-alert 
                  v-if="drawingMode" 
                  type="info" 
                  dense 
                  class="mb-3"
                >
                  <v-icon size="20" class="mr-2">mdi-draw</v-icon>
                  Drawing mode active for field: <strong>{{ selectedFieldForRedraw }}</strong>
                  <br>Click and drag on the image to select a new area
                  <v-btn size="x-small" variant="text" @click="drawingMode = false; selectedFieldForRedraw = ''" class="ml-2">
                    Cancel
                  </v-btn>
                </v-alert>
                
                <!-- Always show annotated images -->
                <div v-else class="mb-3 text-sm text-gray-600 dark:text-gray-400">
                  <v-icon size="16" class="mr-1">mdi-information</v-icon>
                  Click on a field's confidence % to highlight, then click the green box icon to redraw
                </div>
                
                <ImagePageViewer
                  :base64-images="annotatedImages"
                  :fields="fields"
                  ref="pageViewer"
                  :highlight-key="highlightKey"
                  :highlight-edited-key="highlightEditedKey"
                  :drawing-field-key="selectedFieldForRedraw"
                  @update-bounding-box="handleBoundingBoxUpdate"
                />
              </div>
              <div class="w-full lg:w-1/2 min-w-[300px]">
                <v-tabs v-model="tab" color="primary" class="mb-4">
                  <v-tab value="entities">
                    <v-icon size="20" class="mr-1">mdi-format-list-bulleted</v-icon> Entities
                  </v-tab>
                  <v-tab value="swift">
                    <v-icon size="20" class="mr-1">mdi-bank-transfer</v-icon> SWIFT
                  </v-tab>
                  <v-tab value="ucp">
                    <v-icon size="20" class="mr-1">mdi-gavel</v-icon> UCP600
                  </v-tab>
                </v-tabs>
                <v-window v-model="tab" class="h-[calc(100vh-350px)] lg:h-[450px] overflow-y-auto chat-container">
                  <v-window-item value="entities">
                    <v-text-field
                      v-model="searchQuery"
                      placeholder="Search entities..."
                      prepend-inner-icon="mdi-magnify"
                      variant="outlined"
                      density="compact"
                      hide-details
                      class="mb-4"
                      clearable
                    />
                    <div class="space-y-3">
                      <div v-if="Object.keys(filteredFields).length" class="space-y-3">
                        <div v-for="(field, fieldKey) in filteredFields" :key="fieldKey"
                          class="flex items-center gap-3 bg-gray-50 dark:bg-gray-700 p-3 rounded-lg smooth-transition">
                          <div class="w-40 truncate">
                            <span class="font-semibold text-gray-700 dark:text-gray-200">{{ fieldKey }}</span>
                          </div>
                          <v-text-field
                            v-model="field.value"
                            @input="onFieldEdit(fieldKey, $event.target.value)"
                            variant="outlined"
                            density="compact"
                            hide-details
                            :class="{ 'bg-yellow-50 dark:bg-yellow-900': field._edited }"
                            class="flex-1"
                          />
                          <v-chip
                            :color="highlightKey === fieldKey ? 'primary' : 'default'"
                            size="small"
                            class="cursor-pointer smooth-transition"
                            @click="onConfidenceClick(fieldKey)"
                          >
                            {{ field.confidence }}%
                          </v-chip>
                          <v-btn
                            v-if="field._edited"
                            icon
                            size="small"
                            color="warning"
                            @click="revertField(fieldKey)"
                            title="Revert changes"
                          >
                            <v-icon size="18">mdi-undo</v-icon>
                          </v-btn>
                          <v-btn
                            icon
                            size="small"
                            color="success"
                            @click="startRedrawing(fieldKey)"
                            :disabled="drawingMode"
                            title="Redraw bounding box"
                          >
                            <v-icon size="18">mdi-vector-square</v-icon>
                          </v-btn>
                        </div>
                      </div>
                      <div v-else class="text-gray-500 text-sm p-2 bg-gray-50 dark:bg-gray-700 rounded">
                        No matching entities found.
                      </div>
                    </div>
                  </v-window-item>
                  <v-window-item value="swift">
                    <div class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-gray-700 p-2 rounded">{{ swiftSummary }}</div>
                    <div v-if="Object.keys(swiftResult).length" class="overflow-x-auto">
                      <table class="w-full text-sm border-separate border-spacing-0">
                        <thead>
                          <tr class="bg-gray-100 dark:bg-gray-700">
                            <th class="text-left py-2 px-3 font-semibold">Field</th>
                            <th class="text-left py-2 px-3 font-semibold">Status</th>
                            <th class="text-left py-2 px-3 font-semibold">Reason</th>
                            <th class="text-left py-2 px-3 font-semibold">Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(item, fieldKey) in swiftResult" :key="fieldKey"
                            class="border-b border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td class="py-2 px-3 font-medium">{{ fieldKey }}</td>
                            <td class="py-2 px-3">
                              <v-icon :color="item.compliance ? 'success' : 'error'" size="20">
                                {{ item.compliance ? 'mdi-check-circle' : 'mdi-close-circle' }}
                              </v-icon>
                              <span class="ml-1 text-xs">{{ item.compliance ? 'Compliant' : 'Non-compliant' }}</span>
                            </td>
                            <td class="py-2 px-3 text-xs">{{ item.reason || '-' }}</td>
                            <td class="py-2 px-3">{{ item.value || '-' }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <div v-else class="text-gray-500 text-sm p-2 bg-gray-50 dark:bg-gray-700 rounded">No SWIFT compliance data available.</div>
                  </v-window-item>
                  <v-window-item value="ucp">
                    <div class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-gray-700 p-2 rounded">{{ ucpSummary }}</div>
                    <div v-if="Object.keys(ucpResult).length" class="overflow-x-auto">
                      <table class="w-full text-sm border-separate border-spacing-0">
                        <thead>
                          <tr class="bg-gray-100 dark:bg-gray-700">
                            <th class="text-left py-2 px-3 font-semibold">Field</th>
                            <th class="text-left py-2 px-3 font-semibold">Status</th>
                            <th class="text-left py-2 px-3 font-semibold">Error</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(item, fieldKey) in ucpResult" :key="fieldKey"
                            class="border-b border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td class="py-2 px-3 font-medium">{{ fieldKey }}</td>
                            <td class="py-2 px-3">
                              <v-icon :color="!item.error || item.error === 'None' ? 'success' : 'error'" size="20">
                                {{ !item.error || item.error === 'None' ? 'mdi-check-circle' : 'mdi-close-circle' }}
                              </v-icon>
                              <span class="ml-1 text-xs">{{ !item.error || item.error === 'None' ? 'Valid' : 'Error' }}</span>
                            </td>
                            <td class="py-2 px-3 text-xs" :class="item.error && item.error !== 'None' ? 'text-red-600' : 'text-gray-600'">
                              {{ item.error || 'None' }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <div v-else class="text-gray-500 text-sm p-2 bg-gray-50 dark:bg-gray-700 rounded">No UCP600 compliance data available.</div>
                  </v-window-item>
                </v-window>
              </div>
            </div>
          </v-card-text>
        <v-card-actions class="!justify-between bg-gray-50 dark:bg-gray-800 px-6 py-4 flex items-center">
  <!-- Left section with page navigation -->
<div class="flex gap-3 items-center">
  <v-btn size="small" @click="$refs.pageViewer?.prevPage()" :disabled="$refs.pageViewer?.pageNum <= 1" variant="outlined" color="primary">
    <v-icon>mdi-chevron-left</v-icon> Prev
  </v-btn>

  <span class="text-sm text-gray-700 dark:text-gray-200">
    Page {{ $refs.pageViewer?.pageNum }} of {{ $refs.pageViewer?.pageCount }}
  </span>

  <v-btn size="small" @click="$refs.pageViewer?.nextPage()" :disabled="$refs.pageViewer?.pageNum >= $refs.pageViewer?.pageCount" variant="outlined" color="primary">
    Next <v-icon>mdi-chevron-right</v-icon>
  </v-btn>

 <!-- Zoom Controls (functional) -->
<v-btn size="small" variant="outlined" color="primary" aria-label="Zoom Out"
  @click="$refs.pageViewer?.zoomOut()">
  <v-icon>mdi-magnify-minus</v-icon>
</v-btn>
<v-btn size="small" variant="outlined" color="primary" aria-label="Zoom In"
  @click="$refs.pageViewer?.zoomIn()">
  <v-icon>mdi-magnify-plus</v-icon>
</v-btn>
<v-btn size="small" variant="text" color="primary" @click="$refs.pageViewer.scale = 1">
  <v-icon>mdi-restore</v-icon> Reset Zoom
</v-btn>

</div>

  <!-- Center section (optional export controls) -->
  <div class="flex gap-2">
    <v-select
      v-model="exportFormat"
      :items="['json', 'csv']"
      label="Export as"
      variant="outlined"
      density="compact"
      hide-details
      class="w-32"
    />
    <v-btn color="primary" variant="outlined" @click="exportData">Export</v-btn>
  </div>

  <!-- Right section (Approve/Reject buttons) -->
  <div class="flex gap-2">
    <v-btn color="error" variant="outlined" @click="reject">Reject</v-btn>
    <v-btn color="success" variant="flat" @click="approve">Approve</v-btn>
  </div>
</v-card-actions>

        </v-card>
      </v-dialog>
    `
  };

  // Export functions for use in main.js
  window.isValidBase64 = isValidBase64;
})();