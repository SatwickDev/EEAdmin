// Enhanced Dynamic Table Renderer
class DynamicTableRenderer {
    constructor() {
        this.tableCache = new Map();
    }

    // Main render function for tables
    renderDynamicTable(data, containerId = null) {
        try {
            // Parse data if it's a string
            const tableData = typeof data === 'string' ? JSON.parse(data) : data;
            
            // Create unique ID for the table
            const tableId = containerId || `dynamic-table-${Date.now()}`;
            
            // Build the complete table HTML
            const tableHtml = this.buildTableHTML(tableData, tableId);
            
            // Cache the table data for future operations
            this.tableCache.set(tableId, tableData);
            
            // Initialize interactive features after a small delay
            setTimeout(() => {
                this.initializeTableFeatures(tableId, tableData);
            }, 100);
            
            return tableHtml;
        } catch (error) {
            console.error('Error rendering table:', error);
            return this.renderErrorTable(error.message);
        }
    }

    // Build the complete table HTML structure
    buildTableHTML(data, tableId) {
        const { headers, rows, metadata = {} } = this.extractTableData(data);
        
        return `
            <div class="enhanced-table-container" id="${tableId}-container">
                ${this.buildTableControls(tableId, metadata)}
                <div class="table-responsive">
                    <table class="enhanced-table" id="${tableId}">
                        ${this.buildTableHead(headers)}
                        ${this.buildTableBody(rows, headers)}
                    </table>
                </div>
                ${this.buildTablePagination(tableId)}
            </div>
        `;
    }

    // Extract headers and rows from various data formats
    extractTableData(data) {
        let headers = [];
        let rows = [];
        let metadata = {};

        // Handle array of objects
        if (Array.isArray(data)) {
            if (data.length > 0 && typeof data[0] === 'object') {
                headers = Object.keys(data[0]);
                rows = data;
            }
        } 
        // Handle object with headers and rows
        else if (data.headers && data.rows) {
            headers = data.headers;
            rows = data.rows;
            metadata = data.metadata || {};
        }
        // Handle object with columns and data
        else if (data.columns && data.data) {
            headers = data.columns.map(col => col.name || col.title || col);
            rows = data.data;
            metadata = data.metadata || {};
        }
        // Handle simple object (convert to single row)
        else if (typeof data === 'object') {
            headers = Object.keys(data);
            rows = [data];
        }

        return { headers, rows, metadata };
    }

    // Build table controls (search, filters, export)
    buildTableControls(tableId, metadata) {
        return `
            <div class="table-controls">
                <div class="table-search">
                    <i class="fas fa-search"></i>
                    <input type="text" 
                           class="enhanced-table-search" 
                           placeholder="Search table..."
                           data-table="${tableId}">
                </div>
                
                <div class="table-actions">
                    ${this.buildDateRangeFilters(tableId)}
                    ${this.buildColumnToggle(tableId)}
                    ${this.buildExportButtons(tableId)}
                </div>
            </div>
            ${metadata.showStats ? this.buildTableStats(tableId, metadata) : ''}
        `;
    }

    // Build date range filter buttons
    buildDateRangeFilters(tableId) {
        return `
            <div class="date-range-filters">
                <button class="date-range-btn" data-range="1d" data-table="${tableId}">1 Day</button>
                <button class="date-range-btn" data-range="1w" data-table="${tableId}">1 Week</button>
                <button class="date-range-btn" data-range="1m" data-table="${tableId}">1 Month</button>
                <button class="date-range-btn" data-range="3m" data-table="${tableId}">3 Months</button>
                <button class="date-range-btn" data-range="1y" data-table="${tableId}">1 Year</button>
                <button class="date-range-btn" data-range="custom" data-table="${tableId}">
                    <i class="fas fa-calendar"></i> Custom
                </button>
            </div>
        `;
    }

    // Build column toggle dropdown
    buildColumnToggle(tableId) {
        return `
            <div class="column-toggle">
                <button class="column-toggle-btn" data-table="${tableId}">
                    <i class="fas fa-columns"></i> Columns
                </button>
                <div class="column-dropdown" id="${tableId}-columns">
                    <!-- Populated dynamically -->
                </div>
            </div>
        `;
    }

    // Build export buttons
    buildExportButtons(tableId) {
        return `
            <div class="table-export">
                <button class="export-btn" data-format="csv" data-table="${tableId}">
                    <i class="fas fa-file-csv"></i> CSV
                </button>
                <button class="export-btn" data-format="excel" data-table="${tableId}">
                    <i class="fas fa-file-excel"></i> Excel
                </button>
                <button class="export-btn" data-format="pdf" data-table="${tableId}">
                    <i class="fas fa-file-pdf"></i> PDF
                </button>
            </div>
        `;
    }

    // Build table statistics section
    buildTableStats(tableId, metadata) {
        return `
            <div class="table-stats" id="${tableId}-stats">
                <div class="stat-card">
                    <div class="stat-value stat-total-count">0</div>
                    <div class="stat-label">Total Records</div>
                </div>
                ${metadata.statFields ? metadata.statFields.map(field => `
                    <div class="stat-card">
                        <div class="stat-value stat-${field.key}-count">0</div>
                        <div class="stat-label">${field.label}</div>
                    </div>
                `).join('') : ''}
            </div>
        `;
    }

    // Build table head with sortable columns
    buildTableHead(headers) {
        return `
            <thead>
                <tr>
                    ${headers.map((header, index) => {
                        const columnName = this.formatColumnName(header);
                        const isSortable = !this.isNonSortableColumn(header);
                        
                        return `
                            <th data-column="${header}" 
                                data-sortable="${isSortable}"
                                data-column-index="${index}">
                                ${columnName}
                                ${isSortable ? '<i class="fas fa-sort sort-icon"></i>' : ''}
                            </th>
                        `;
                    }).join('')}
                </tr>
            </thead>
        `;
    }

    // Build table body
    buildTableBody(rows, headers) {
        if (!rows || rows.length === 0) {
            return this.buildEmptyTableBody(headers.length);
        }

        return `
            <tbody>
                ${rows.map((row, rowIndex) => this.buildTableRow(row, headers, rowIndex)).join('')}
            </tbody>
        `;
    }

    // Build individual table row
    buildTableRow(row, headers, rowIndex) {
        return `
            <tr data-row-index="${rowIndex}">
                ${headers.map(header => {
                    const value = this.getCellValue(row, header);
                    const formattedValue = this.formatCellValue(value, header);
                    
                    return `
                        <td data-label="${this.formatColumnName(header)}"
                            data-column="${header}">
                            ${formattedValue}
                        </td>
                    `;
                }).join('')}
            </tr>
        `;
    }

    // Get cell value from row data
    getCellValue(row, header) {
        // Handle nested properties
        if (header.includes('.')) {
            return header.split('.').reduce((obj, key) => obj?.[key], row);
        }
        
        // Handle array-based rows
        if (Array.isArray(row)) {
            const index = parseInt(header);
            return !isNaN(index) ? row[index] : '';
        }
        
        return row[header] || '';
    }

    // Format cell value based on type
    formatCellValue(value, header) {
        // Handle null/undefined
        if (value === null || value === undefined) {
            return '<span class="text-gray-400">-</span>';
        }

        // Handle boolean
        if (typeof value === 'boolean') {
            return `<span class="status-badge ${value ? 'success' : 'error'}">
                ${value ? 'Yes' : 'No'}
            </span>`;
        }

        // Handle status fields
        if (header.toLowerCase().includes('status')) {
            return this.formatStatusBadge(value);
        }

        // Handle dates
        if (this.isDateValue(value)) {
            return this.formatDate(value);
        }

        // Handle numbers
        if (typeof value === 'number') {
            return this.formatNumber(value, header);
        }

        // Handle long text
        if (typeof value === 'string' && value.length > 50) {
            return `<span title="${this.escapeHtml(value)}">${this.escapeHtml(value.substring(0, 50))}...</span>`;
        }

        // Default: escape HTML and return
        return this.escapeHtml(String(value));
    }

    // Format status badge
    formatStatusBadge(status) {
        const statusLower = String(status).toLowerCase();
        let badgeClass = 'info';
        
        if (['active', 'success', 'completed', 'approved'].includes(statusLower)) {
            badgeClass = 'success';
        } else if (['pending', 'processing', 'warning'].includes(statusLower)) {
            badgeClass = 'warning';
        } else if (['error', 'failed', 'rejected', 'cancelled'].includes(statusLower)) {
            badgeClass = 'error';
        }

        return `<span class="status-badge ${badgeClass}">${this.escapeHtml(status)}</span>`;
    }

    // Format date values
    formatDate(value) {
        try {
            const date = new Date(value);
            if (isNaN(date.getTime())) return value;
            
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return value;
        }
    }

    // Format number values
    formatNumber(value, header) {
        const headerLower = header.toLowerCase();
        
        // Currency formatting
        if (headerLower.includes('amount') || headerLower.includes('price') || 
            headerLower.includes('cost') || headerLower.includes('value')) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(value);
        }
        
        // Percentage formatting
        if (headerLower.includes('percent') || headerLower.includes('rate')) {
            return `${value.toFixed(2)}%`;
        }
        
        // Default number formatting
        return new Intl.NumberFormat('en-US').format(value);
    }

    // Build empty table body
    buildEmptyTableBody(columnCount) {
        return `
            <tbody>
                <tr>
                    <td colspan="${columnCount}" class="table-empty">
                        <div class="table-empty-icon">
                            <i class="fas fa-inbox"></i>
                        </div>
                        <p>No data available</p>
                    </td>
                </tr>
            </tbody>
        `;
    }

    // Build pagination controls
    buildTablePagination(tableId) {
        return `
            <div class="table-pagination">
                <div class="pagination-info"></div>
                <div class="pagination-controls">
                    <button class="pagination-btn pagination-prev" data-table="${tableId}">
                        <i class="fas fa-chevron-left"></i>
                    </button>
                    <div class="pagination-numbers"></div>
                    <button class="pagination-btn pagination-next" data-table="${tableId}">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        `;
    }

    // Initialize interactive features
    initializeTableFeatures(tableId, tableData) {
        try {
            // Create enhanced table instance
            if (window.EnhancedTable) {
                const tableElement = document.getElementById(tableId);
                if (!tableElement) {
                    console.warn(`Table element not found: ${tableId}`);
                    return;
                }
                
                const tableInstance = new window.EnhancedTable(tableId);
                
                // Load data
                const { rows } = this.extractTableData(tableData);
                tableInstance.loadData(rows);
                
                // Store instance
                this.tableCache.set(`${tableId}-instance`, tableInstance);
            }

            // Initialize column toggle
            this.initializeColumnToggle(tableId);
            
            // Initialize export buttons
            this.initializeExportButtons(tableId);
            
            // Add responsive behavior
            this.initializeResponsiveBehavior(tableId);
        } catch (error) {
            console.error('Error initializing table features:', error);
        }
    }

    // Initialize column toggle functionality
    initializeColumnToggle(tableId) {
        const toggleBtn = document.querySelector(`[data-table="${tableId}"].column-toggle-btn`);
        const dropdown = document.getElementById(`${tableId}-columns`);
        
        if (!toggleBtn || !dropdown) return;

        // Populate columns
        const headers = document.querySelectorAll(`#${tableId} th`);
        dropdown.innerHTML = Array.from(headers).map((th, index) => `
            <label class="column-item">
                <input type="checkbox" 
                       checked 
                       data-column-index="${index}"
                       data-table="${tableId}">
                <span>${th.textContent.trim()}</span>
            </label>
        `).join('');

        // Toggle dropdown
        toggleBtn.addEventListener('click', () => {
            dropdown.classList.toggle('show');
        });

        // Handle column visibility
        dropdown.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                const columnIndex = parseInt(e.target.dataset.columnIndex);
                this.toggleColumn(tableId, columnIndex, e.target.checked);
            }
        });

        // Close dropdown on outside click
        document.addEventListener('click', (e) => {
            if (!toggleBtn.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    }

    // Toggle column visibility
    toggleColumn(tableId, columnIndex, visible) {
        const table = document.getElementById(tableId);
        const cells = table.querySelectorAll(
            `th:nth-child(${columnIndex + 1}), td:nth-child(${columnIndex + 1})`
        );
        
        cells.forEach(cell => {
            cell.style.display = visible ? '' : 'none';
        });
    }

    // Initialize export functionality
    initializeExportButtons(tableId) {
        const exportBtns = document.querySelectorAll(`[data-table="${tableId}"].export-btn`);
        
        exportBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const format = btn.dataset.format;
                this.exportTable(tableId, format);
            });
        });
    }

    // Export table data
    exportTable(tableId, format) {
        const tableInstance = this.tableCache.get(`${tableId}-instance`);
        
        if (tableInstance && tableInstance.exportToExcel) {
            if (format === 'csv' || format === 'excel') {
                tableInstance.exportToExcel();
            } else if (format === 'pdf') {
                tableInstance.exportToPDF();
            }
        } else {
            // Fallback export
            this.simpleExport(tableId, format);
        }
    }

    // Simple export fallback
    simpleExport(tableId, format) {
        const table = document.getElementById(tableId);
        const data = [];
        
        // Get headers
        const headers = Array.from(table.querySelectorAll('thead th'))
            .map(th => th.textContent.trim());
        data.push(headers);
        
        // Get rows
        table.querySelectorAll('tbody tr').forEach(tr => {
            const row = Array.from(tr.querySelectorAll('td'))
                .map(td => td.textContent.trim());
            data.push(row);
        });
        
        // Create CSV
        const csv = data.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
        
        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `table-export-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // Initialize responsive behavior
    initializeResponsiveBehavior(tableId) {
        const table = document.getElementById(tableId);
        const container = document.getElementById(`${tableId}-container`);
        
        // Check table width on resize
        const checkTableWidth = () => {
            const containerWidth = container.offsetWidth;
            const tableWidth = table.offsetWidth;
            
            if (window.innerWidth < 768) {
                table.classList.add('mobile-cards');
                this.addMobileLabels(tableId);
            } else {
                table.classList.remove('mobile-cards');
            }
        };
        
        // Initial check
        checkTableWidth();
        
        // Add resize listener with debounce
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(checkTableWidth, 250);
        });
    }

    // Add mobile labels to cells
    addMobileLabels(tableId) {
        const table = document.getElementById(tableId);
        const headers = Array.from(table.querySelectorAll('thead th'))
            .map(th => th.textContent.trim());
        
        table.querySelectorAll('tbody tr').forEach(tr => {
            tr.querySelectorAll('td').forEach((td, index) => {
                td.setAttribute('data-label', headers[index] || '');
            });
        });
    }

    // Utility functions
    formatColumnName(name) {
        return name
            .replace(/_/g, ' ')
            .replace(/([A-Z])/g, ' $1')
            .trim()
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
    }

    isNonSortableColumn(header) {
        const nonSortable = ['actions', 'checkbox', 'select'];
        return nonSortable.includes(header.toLowerCase());
    }

    isDateValue(value) {
        if (typeof value !== 'string') return false;
        
        // Common date patterns
        const datePatterns = [
            /^\d{4}-\d{2}-\d{2}/, // ISO date
            /^\d{2}\/\d{2}\/\d{4}/, // US date
            /^\d{2}-\d{2}-\d{4}/ // EU date
        ];
        
        return datePatterns.some(pattern => pattern.test(value));
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderErrorTable(errorMessage) {
        return `
            <div class="enhanced-table-container error">
                <div class="table-empty">
                    <div class="table-empty-icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <p>Error rendering table: ${this.escapeHtml(errorMessage)}</p>
                </div>
            </div>
        `;
    }
}

// Create global instance
window.dynamicTableRenderer = new DynamicTableRenderer();

// Integration with existing chat system
document.addEventListener('DOMContentLoaded', () => {
    // Override existing table rendering if needed
    if (window.renderTable) {
        const originalRenderTable = window.renderTable;
        window.renderTable = function(data) {
            // Use new renderer for complex tables
            if (typeof data === 'object' && (Array.isArray(data) || data.headers || data.columns)) {
                return window.dynamicTableRenderer.renderDynamicTable(data);
            }
            // Fall back to original for simple tables
            return originalRenderTable(data);
        };
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DynamicTableRenderer;
}