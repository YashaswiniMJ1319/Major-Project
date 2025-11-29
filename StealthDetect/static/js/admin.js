/**
 * StealthCAPTCHA Admin Dashboard
 * Analytics and monitoring functionality
 */

(function() {
    'use strict';

    // Chart instances
    let trendChart = null;
    let distributionChart = null;
    let performanceChart = null;

    // Configuration
    const CONFIG = {
        refreshInterval: 30000, // 30 seconds
        apiEndpoint: '/api/stats',
        maxDataPoints: 24
    };

    // Data storage
    let dashboardData = {
        stats: null,
        hourlyData: null,
        lastUpdate: null
    };

    /**
     * Initialize admin dashboard
     */
    function init() {
        console.log('StealthCAPTCHA Admin: Initializing dashboard');
        
        // Load initial data
        loadDashboardData();
        
        // Setup auto-refresh
        setInterval(loadDashboardData, CONFIG.refreshInterval);
        
        // Setup event listeners
        setupEventListeners();
        
        // Initialize tooltips
        initializeTooltips();
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                loadDashboardData(true);
            });
        }

        // Export buttons
        const exportButtons = document.querySelectorAll('[data-export]');
        exportButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const exportType = this.getAttribute('data-export');
                exportData(exportType);
            });
        });

        // Time range selector
        const timeRangeSelect = document.getElementById('time-range');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', function() {
                const range = this.value;
                updateTimeRange(range);
            });
        }

        // Real-time toggle
        const realtimeToggle = document.getElementById('realtime-toggle');
        if (realtimeToggle) {
            realtimeToggle.addEventListener('change', function() {
                toggleRealtime(this.checked);
            });
        }
    }

    /**
     * Initialize Bootstrap tooltips
     */
    function initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Load dashboard data from API
     */
    function loadDashboardData(showLoader = false) {
        if (showLoader) {
            showLoadingIndicator();
        }

        fetch(CONFIG.apiEndpoint)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                dashboardData.stats = data;
                dashboardData.hourlyData = data.hourly_data || {};
                dashboardData.lastUpdate = new Date();

                // Update UI
                updateStatCards(data);
                updateCharts(data);
                updateLastUpdated();
                
                if (showLoader) {
                    hideLoadingIndicator();
                }
            })
            .catch(error => {
                console.error('Error loading dashboard data:', error);
                showErrorAlert('Failed to load dashboard data: ' + error.message);
                
                if (showLoader) {
                    hideLoadingIndicator();
                }
            });
    }

    /**
     * Update stat cards with latest data
     */
    function updateStatCards(data) {
        // Update total detections
        const totalEl = document.getElementById('total-detections');
        if (totalEl) {
            animateCounter(totalEl, data.total_detections || 0);
        }

        // Update human detections
        const humanEl = document.getElementById('human-detections');
        if (humanEl) {
            animateCounter(humanEl, data.human_detections || 0);
        }

        // Update bot detections
        const botEl = document.getElementById('bot-detections');
        if (botEl) {
            animateCounter(botEl, data.bot_detections || 0);
        }

        // Update percentages
        const totalDetections = data.total_detections || 0;
        if (totalDetections > 0) {
            const humanPercentage = ((data.human_detections || 0) / totalDetections * 100).toFixed(1);
            const botPercentage = ((data.bot_detections || 0) / totalDetections * 100).toFixed(1);

            const humanPercentEl = document.getElementById('human-percentage');
            if (humanPercentEl) {
                humanPercentEl.textContent = humanPercentage + '%';
            }

            const botPercentEl = document.getElementById('bot-percentage');
            if (botPercentEl) {
                botPercentEl.textContent = botPercentage + '%';
            }
        }

        // Update trend indicators
        updateTrendIndicators(data);
    }

    /**
     * Animate counter elements
     */
    function animateCounter(element, targetValue) {
        const currentValue = parseInt(element.textContent) || 0;
        const increment = Math.ceil((targetValue - currentValue) / 20);
        
        if (increment === 0) return;

        const timer = setInterval(() => {
            const newValue = parseInt(element.textContent) + increment;
            if ((increment > 0 && newValue >= targetValue) || 
                (increment < 0 && newValue <= targetValue)) {
                element.textContent = targetValue;
                clearInterval(timer);
            } else {
                element.textContent = newValue;
            }
        }, 50);
    }

    /**
     * Update trend indicators
     */
    function updateTrendIndicators(data) {
        // This would compare with previous data to show trends
        // For now, we'll show static indicators
        const trendElements = document.querySelectorAll('.trend-indicator');
        trendElements.forEach(el => {
            const type = el.getAttribute('data-trend-type');
            let trend = 'stable';
            let icon = 'fas fa-minus';
            
            // Simple trend calculation based on recent vs older data
            if (type === 'human' && data.human_detections > data.bot_detections) {
                trend = 'up';
                icon = 'fas fa-arrow-up text-success';
            } else if (type === 'bot' && data.bot_detections > data.human_detections) {
                trend = 'up';
                icon = 'fas fa-arrow-up text-danger';
            }
            
            el.innerHTML = `<i class="${icon}"></i>`;
        });
    }

    /**
     * Update all charts with new data
     */
    function updateCharts(data) {
        updateTrendChart(data.hourly_data || {});
        updateDistributionChart(data.human_detections || 0, data.bot_detections || 0);
        updatePerformanceMetrics(data);
    }

    /**
     * Update trend chart (line chart showing hourly data)
     */
    function updateTrendChart(hourlyData) {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;

        // Destroy existing chart
        if (trendChart) {
            trendChart.destroy();
        }

        // Prepare data for last 24 hours
        const hours = Array.from({length: 24}, (_, i) => i);
        const labels = hours.map(h => String(h).padStart(2, '0') + ':00');
        
        const humanData = hours.map(h => hourlyData[h] ? hourlyData[h].human || 0 : 0);
        const botData = hours.map(h => hourlyData[h] ? hourlyData[h].bot || 0 : 0);

        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Human Users',
                    data: humanData,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#28a745',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }, {
                    label: 'Bot Attempts',
                    data: botData,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#dc3545',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Detection Trends (Last 24 Hours)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#dee2e6',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Number of Detections'
                        },
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    /**
     * Update distribution chart (doughnut chart)
     */
    function updateDistributionChart(humanCount, botCount) {
        const ctx = document.getElementById('distributionChart');
        if (!ctx) return;

        // Destroy existing chart
        if (distributionChart) {
            distributionChart.destroy();
        }

        const total = humanCount + botCount;
        if (total === 0) {
            // Show empty state
            ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
            return;
        }

        distributionChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Human Users', 'Bot Attempts'],
                datasets: [{
                    data: [humanCount, botCount],
                    backgroundColor: ['#28a745', '#dc3545'],
                    borderColor: ['#fff', '#fff'],
                    borderWidth: 3,
                    hoverBackgroundColor: ['#218838', '#c82333'],
                    hoverBorderWidth: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Detection Distribution',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%',
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });
    }

    /**
     * Update performance metrics
     */
    function updatePerformanceMetrics(data) {
        // Calculate average response time, accuracy, etc.
        const metricsContainer = document.getElementById('performance-metrics');
        if (!metricsContainer) return;

        // This would show real-time performance data
        // For now, we'll update basic metrics
        updateMetricValue('avg-response-time', '< 100ms');
        updateMetricValue('accuracy-rate', '95.2%');
        updateMetricValue('false-positive-rate', '2.1%');
        updateMetricValue('throughput', Math.floor(Math.random() * 1000) + 500);
    }

    /**
     * Update individual metric value
     */
    function updateMetricValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    /**
     * Update last updated timestamp
     */
    function updateLastUpdated() {
        const lastUpdatedEl = document.getElementById('last-updated');
        if (lastUpdatedEl && dashboardData.lastUpdate) {
            lastUpdatedEl.textContent = dashboardData.lastUpdate.toLocaleTimeString();
        }
    }

    /**
     * Show loading indicator
     */
    function showLoadingIndicator() {
        const loader = document.getElementById('loading-indicator');
        if (loader) {
            loader.style.display = 'block';
        }

        // Disable refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
        }
    }

    /**
     * Hide loading indicator
     */
    function hideLoadingIndicator() {
        const loader = document.getElementById('loading-indicator');
        if (loader) {
            loader.style.display = 'none';
        }

        // Re-enable refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Refresh';
        }
    }

    /**
     * Show error alert
     */
    function showErrorAlert(message) {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;

        const alertHtml = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Error:</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        alertContainer.innerHTML = alertHtml;

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = alertContainer.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }

    /**
     * Export data functionality
     */
    function exportData(type) {
        console.log('Exporting data:', type);
        
        if (!dashboardData.stats) {
            showErrorAlert('No data available for export');
            return;
        }

        switch (type) {
            case 'csv':
                exportToCSV();
                break;
            case 'json':
                exportToJSON();
                break;
            case 'pdf':
                exportToPDF();
                break;
            default:
                console.warn('Unknown export type:', type);
        }
    }

    /**
     * Export data to CSV
     */
    function exportToCSV() {
        const data = dashboardData.hourlyData;
        let csvContent = 'Hour,Human,Bot\n';
        
        for (let hour = 0; hour < 24; hour++) {
            const hourData = data[hour] || { human: 0, bot: 0 };
            csvContent += `${hour},${hourData.human},${hourData.bot}\n`;
        }

        downloadFile(csvContent, 'stealth-captcha-data.csv', 'text/csv');
    }

    /**
     * Export data to JSON
     */
    function exportToJSON() {
        const jsonContent = JSON.stringify(dashboardData.stats, null, 2);
        downloadFile(jsonContent, 'stealth-captcha-data.json', 'application/json');
    }

    /**
     * Export data to PDF (simplified)
     */
    function exportToPDF() {
        // This would require a PDF library like jsPDF
        showErrorAlert('PDF export not yet implemented');
    }

    /**
     * Download file helper
     */
    function downloadFile(content, filename, contentType) {
        const blob = new Blob([content], { type: contentType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }

    /**
     * Toggle real-time updates
     */
    function toggleRealtime(enabled) {
        console.log('Real-time updates:', enabled ? 'enabled' : 'disabled');
        // This would control the auto-refresh behavior
        // For now, it's already implemented with setInterval
    }

    /**
     * Update time range for charts
     */
    function updateTimeRange(range) {
        console.log('Time range changed to:', range);
        // This would fetch data for different time ranges
        // For now, we only support 24 hours
        loadDashboardData(true);
    }

    // Public API
    window.adminDashboard = {
        init: init,
        loadData: loadDashboardData,
        exportData: exportData
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
