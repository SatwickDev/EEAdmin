// Enhanced Table Interactive Features
(function() {
    'use strict';
    
class EnhancedTable {
    constructor(tableId) {
        this.tableId = tableId;
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.searchTerm = '';
        this.filters = {};
        this.data = [];
        this.filteredData = [];
        
        this.init();
    }

    init() {
        try {
            this.bindEvents();
            this.setupPagination();
            this.setupSorting();
            this.setupFiltering();
            this.setupSearch();
        } catch (error) {
            console.error('Error initializing enhanced table:', error);
        }
    }

    bindEvents() {
        // Search functionality
        const searchInput = document.querySelector(`#${this.tableId} .enhanced-table-search`);
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchTerm = e.target.value.toLowerCase();
                this.applyFilters();
            });
        }

        // Filter buttons
        const filterBtns = document.querySelectorAll(`#${this.tableId} .filter-btn`);
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                btn.classList.toggle('active');
                const filterType = btn.dataset.filter;
                const filterValue = btn.dataset.value;
                
                if (btn.classList.contains('active')) {
                    this.filters[filterType] = filterValue;
                } else {
                    delete this.filters[filterType];
                }
                
                this.applyFilters();
            });
        });
    }

    setupSorting() {
        const headers = document.querySelectorAll(`#${this.tableId} th[data-sortable="true"]`);
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const column = header.dataset.column;
                
                if (this.sortColumn === column) {
                    this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortColumn = column;
                    this.sortDirection = 'asc';
                }
                
                this.updateSortIcons(header);
                this.sortData();
                this.renderTable();
            });
        });
    }

    updateSortIcons(activeHeader) {
        // Reset all sort icons
        document.querySelectorAll(`#${this.tableId} .sort-icon`).forEach(icon => {
            icon.classList.remove('active', 'fa-sort-up', 'fa-sort-down');
            icon.classList.add('fa-sort');
        });

        // Update active header icon
        const icon = activeHeader.querySelector('.sort-icon');
        if (icon) {
            icon.classList.add('active');
            icon.classList.remove('fa-sort');
            icon.classList.add(this.sortDirection === 'asc' ? 'fa-sort-up' : 'fa-sort-down');
        }
    }

    sortData() {
        if (!this.sortColumn) return;

        this.filteredData.sort((a, b) => {
            let aVal = a[this.sortColumn];
            let bVal = b[this.sortColumn];

            // Handle numeric values
            if (!isNaN(aVal) && !isNaN(bVal)) {
                aVal = parseFloat(aVal);
                bVal = parseFloat(bVal);
            }

            // Handle dates
            if (this.isDate(aVal) && this.isDate(bVal)) {
                aVal = new Date(aVal);
                bVal = new Date(bVal);
            }

            if (aVal < bVal) {
                return this.sortDirection === 'asc' ? -1 : 1;
            }
            if (aVal > bVal) {
                return this.sortDirection === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }

    isDate(value) {
        return !isNaN(Date.parse(value));
    }

    setupPagination() {
        const prevBtn = document.querySelector(`#${this.tableId} .pagination-prev`);
        const nextBtn = document.querySelector(`#${this.tableId} .pagination-next`);
        const pageButtons = document.querySelectorAll(`#${this.tableId} .page-number`);

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.renderTable();
                    this.updatePagination();
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(this.filteredData.length / this.itemsPerPage);
                if (this.currentPage < totalPages) {
                    this.currentPage++;
                    this.renderTable();
                    this.updatePagination();
                }
            });
        }

        pageButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                this.currentPage = parseInt(btn.dataset.page);
                this.renderTable();
                this.updatePagination();
            });
        });
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredData.length / this.itemsPerPage);
        const paginationInfo = document.querySelector(`#${this.tableId} .pagination-info`);
        
        if (paginationInfo) {
            const start = (this.currentPage - 1) * this.itemsPerPage + 1;
            const end = Math.min(start + this.itemsPerPage - 1, this.filteredData.length);
            paginationInfo.textContent = `Showing ${start} to ${end} of ${this.filteredData.length} entries`;
        }

        // Update button states
        const prevBtn = document.querySelector(`#${this.tableId} .pagination-prev`);
        const nextBtn = document.querySelector(`#${this.tableId} .pagination-next`);
        
        if (prevBtn) {
            prevBtn.disabled = this.currentPage === 1;
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.currentPage === totalPages;
        }

        // Update page numbers
        this.renderPageNumbers();
    }

    renderPageNumbers() {
        const totalPages = Math.ceil(this.filteredData.length / this.itemsPerPage);
        const paginationWrapper = document.querySelector(`#${this.tableId} .pagination-numbers`);
        
        if (!paginationWrapper) return;

        paginationWrapper.innerHTML = '';
        
        // Calculate page range to show
        let startPage = Math.max(1, this.currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }

        // Add page buttons
        for (let i = startPage; i <= endPage; i++) {
            const btn = document.createElement('button');
            btn.className = 'pagination-btn page-number';
            btn.textContent = i;
            btn.dataset.page = i;
            
            if (i === this.currentPage) {
                btn.classList.add('active');
            }
            
            btn.addEventListener('click', () => {
                this.currentPage = i;
                this.renderTable();
                this.updatePagination();
            });
            
            paginationWrapper.appendChild(btn);
        }
    }

    setupFiltering() {
        // Setup date range filtering
        const dateRangeButtons = document.querySelectorAll(`#${this.tableId} .date-range-btn`);
        dateRangeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const range = btn.dataset.range;
                this.applyDateRangeFilter(range);
            });
        });
    }

    applyDateRangeFilter(range) {
        const now = new Date();
        let startDate;

        switch (range) {
            case '1d':
                startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                break;
            case '1w':
                startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                break;
            case '1m':
                startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                break;
            case '3m':
                startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                break;
            case '1y':
                startDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
                break;
            default:
                startDate = null;
        }

        if (startDate) {
            this.filters.dateRange = { start: startDate, end: now };
        } else {
            delete this.filters.dateRange;
        }

        this.applyFilters();
    }

    setupSearch() {
        // Add debouncing for search
        let searchTimeout;
        const searchInput = document.querySelector(`#${this.tableId} .enhanced-table-search`);
        
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchTerm = e.target.value.toLowerCase();
                    this.applyFilters();
                }, 300);
            });
        }
    }

    applyFilters() {
        this.filteredData = this.data.filter(row => {
            // Apply search filter
            if (this.searchTerm) {
                const searchMatch = Object.values(row).some(value => 
                    String(value).toLowerCase().includes(this.searchTerm)
                );
                if (!searchMatch) return false;
            }

            // Apply other filters
            for (const [filterType, filterValue] of Object.entries(this.filters)) {
                if (filterType === 'status' && row.status !== filterValue) {
                    return false;
                }
                
                if (filterType === 'dateRange' && row.date) {
                    const rowDate = new Date(row.date);
                    if (rowDate < filterValue.start || rowDate > filterValue.end) {
                        return false;
                    }
                }
            }

            return true;
        });

        this.currentPage = 1;
        this.renderTable();
        this.updatePagination();
        this.updateStats();
    }

    renderTable() {
        const tbody = document.querySelector(`#${this.tableId} tbody`);
        if (!tbody) return;

        const start = (this.currentPage - 1) * this.itemsPerPage;
        const end = start + this.itemsPerPage;
        const pageData = this.filteredData.slice(start, end);

        tbody.innerHTML = pageData.map(row => this.renderRow(row)).join('');
        
        // Add row animations
        const rows = tbody.querySelectorAll('tr');
        rows.forEach((row, index) => {
            row.style.animation = `fadeInUp 0.3s ease ${index * 0.05}s`;
        });
    }

    renderRow(row) {
        // This should be customized based on your table structure
        return `<tr>${Object.values(row).map(value => `<td>${value}</td>`).join('')}</tr>`;
    }

    updateStats() {
        // Update table statistics
        const totalCount = document.querySelector(`#${this.tableId} .stat-total-count`);
        if (totalCount) {
            totalCount.textContent = this.filteredData.length;
        }

        // Update other stats as needed
        this.updateStatusCounts();
    }

    updateStatusCounts() {
        const statusCounts = {};
        this.filteredData.forEach(row => {
            if (row.status) {
                statusCounts[row.status] = (statusCounts[row.status] || 0) + 1;
            }
        });

        Object.entries(statusCounts).forEach(([status, count]) => {
            // Sanitize status for use in CSS selector
            const sanitizedStatus = this.sanitizeForSelector(status);
            const element = document.querySelector(`#${this.tableId} .stat-${sanitizedStatus}-count`);
            if (element) {
                element.textContent = count;
            }
        });
    }
    
    // Sanitize string for use in CSS selectors
    sanitizeForSelector(str) {
        // Convert to string and lowercase
        const sanitized = String(str).toLowerCase()
            // Remove HTML tags
            .replace(/<[^>]*>/g, '')
            // Replace non-alphanumeric characters with hyphens
            .replace(/[^a-z0-9]/g, '-')
            // Remove multiple consecutive hyphens
            .replace(/-+/g, '-')
            // Remove leading/trailing hyphens
            .replace(/^-|-$/g, '');
        
        return sanitized || 'unknown';
    }

    // Export functionality
    exportToExcel() {
        const headers = this.getTableHeaders();
        const rows = this.filteredData.map(row => headers.map(header => row[header.key] || ''));
        
        // Create CSV content
        const csvContent = [
            headers.map(h => h.label).join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        // Download CSV
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `table-export-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
    }

    exportToPDF() {
        // This would require a PDF library like jsPDF
        console.log('PDF export functionality would be implemented here');
    }

    getTableHeaders() {
        const headers = [];
        document.querySelectorAll(`#${this.tableId} th`).forEach(th => {
            if (th.dataset.column) {
                headers.push({
                    key: th.dataset.column,
                    label: th.textContent.trim()
                });
            }
        });
        return headers;
    }

    // Load data into table
    loadData(data) {
        try {
            this.data = data || [];
            this.filteredData = [...this.data];
            this.applyFilters();
        } catch (error) {
            console.error('Error loading data into enhanced table:', error);
            this.data = [];
            this.filteredData = [];
        }
    }
}

// CSS animation keyframes
const enhancedTableStyle = document.createElement('style');
enhancedTableStyle.textContent = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(enhancedTableStyle);

// Initialize tables when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Auto-initialize tables with class 'enhanced-table'
    document.querySelectorAll('.enhanced-table').forEach(table => {
        const tableInstance = new EnhancedTable(table.id);
        // Store instance for later use
        window[`${table.id}Instance`] = tableInstance;
    });
});

// Export for global use
window.EnhancedTable = EnhancedTable;

})(); // End IIFE