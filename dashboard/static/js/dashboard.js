/**
 * Main Dashboard JavaScript
 * Handles InfluxDB connections, real-time data, and chart updates
 */

// Configuration
const CONFIG = {
    influxdb: {
        url: 'http://localhost:8086',
        token: 'factory-token-2024',
        org: 'factory',
        bucket: 'industrial_data'
    },
    ml_api: {
        url: 'http://localhost:5001'
    },
    refresh_interval: 10000, // 10 seconds
    chart_max_points: 20
};

// Global variables
let charts = {};
let isConnected = false;
let lastUpdateTime = null;

/**
 * Initialize dashboard
 */
async function initDashboard() {
    console.log('🚀 Initializing Industrial IoT Dashboard...');

    // Fix canvas dimensions BEFORE initializing charts
    fixCanvasDimensions();

    // Initialize charts
    initCharts();

    // Load initial data
    await updateAllData();

    // Setup auto-refresh
    setInterval(updateAllData, CONFIG.refresh_interval);

    console.log('✅ Dashboard initialized successfully');
}

/**
 * Fix canvas dimensions to prevent exceeding max size
 */
function fixCanvasDimensions() {
    const canvases = ['tempChart', 'powerChart', 'maintenanceChart', 'energyOptChart'];

    canvases.forEach(canvasId => {
        const canvas = document.getElementById(canvasId);
        if (canvas) {
            const container = canvas.parentElement;
            const containerRect = container.getBoundingClientRect();

            // Set reasonable dimensions that won't exceed browser limits
            const maxWidth = Math.min(containerRect.width - 50, 800);
            const maxHeight = Math.min(300, 400);

            canvas.width = maxWidth;
            canvas.height = maxHeight;

            // Also set CSS dimensions to match
            canvas.style.width = maxWidth + 'px';
            canvas.style.height = maxHeight + 'px';

            console.log(`📊 Fixed canvas ${canvasId}: ${maxWidth}x${maxHeight}`);
        }
    });
}

/**
 * Initialize all charts
 */
function initCharts() {
    const chartConfig = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#ffffff' }
            }
        },
        scales: {
            x: {
                ticks: { color: '#a0aec0' },
                grid: { color: 'rgba(255, 255, 255, 0.1)' }
            },
            y: {
                ticks: { color: '#a0aec0' },
                grid: { color: 'rgba(255, 255, 255, 0.1)' }
            }
        },
        // Prevent canvas from growing too large
        onResize: function (chart, newSize) {
            if (newSize.width > 1200) {
                chart.canvas.width = 1200;
            }
            if (newSize.height > 600) {
                chart.canvas.height = 600;
            }
        }
    };

    // Temperature Chart
    const tempCanvas = document.getElementById('tempChart');
    if (tempCanvas) {
        charts.temperature = new Chart(tempCanvas, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                ...chartConfig,
                scales: {
                    ...chartConfig.scales,
                    y: {
                        ...chartConfig.scales.y,
                        min: 15,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Temperatura (°C)',
                            color: '#ffffff'
                        }
                    }
                }
            }
        });
    }

    // Power Chart
    const powerCanvas = document.getElementById('powerChart');
    if (powerCanvas) {
        charts.power = new Chart(powerCanvas, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                ...chartConfig,
                scales: {
                    ...chartConfig.scales,
                    y: {
                        ...chartConfig.scales.y,
                        min: 0,
                        title: {
                            display: true,
                            text: 'Potenza (kW)',
                            color: '#ffffff'
                        }
                    }
                }
            }
        });
    }

    // Maintenance Chart (ML)
    const maintenanceCanvas = document.getElementById('maintenanceChart');
    if (maintenanceCanvas) {
        charts.maintenance = new Chart(maintenanceCanvas, {
            type: 'bar',
            data: {
                labels: ['Milling1', 'Milling2', 'Lathe1', 'Saw1'],
                datasets: [{
                    label: 'Giorni alla Manutenzione',
                    data: [12, 8, 15, 6],
                    backgroundColor: 'rgba(102, 126, 234, 0.6)',
                    borderColor: '#667eea',
                    borderWidth: 2
                }]
            },
            options: {
                ...chartConfig,
                scales: {
                    ...chartConfig.scales,
                    y: {
                        ...chartConfig.scales.y,
                        min: 0,
                        title: {
                            display: true,
                            text: 'Giorni',
                            color: '#ffffff'
                        }
                    }
                }
            }
        });
    }

    // Energy Optimization Chart (ML)
    const energyCanvas = document.getElementById('energyOptChart');
    if (energyCanvas) {
        charts.energy = new Chart(energyCanvas, {
            type: 'doughnut',
            data: {
                labels: ['Attuale', 'Ottimizzato', 'Risparmio'],
                datasets: [{
                    data: [70, 60, 10],
                    backgroundColor: [
                        'rgba(237, 137, 54, 0.8)',
                        'rgba(72, 187, 120, 0.8)',
                        'rgba(102, 126, 234, 0.8)'
                    ],
                    borderColor: [
                        '#ed8936',
                        '#48bb78',
                        '#667eea'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                ...chartConfig,
                plugins: {
                    ...chartConfig.plugins,
                    legend: {
                        position: 'bottom',
                        labels: { color: '#ffffff' }
                    }
                }
            }
        });
    }

    console.log('📊 Charts initialized');
}

/**
 * Query InfluxDB
 */
async function queryInfluxDB(fluxQuery) {
    try {
        const response = await fetch(`${CONFIG.influxdb.url}/api/v2/query?org=${CONFIG.influxdb.org}`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${CONFIG.influxdb.token}`,
                'Content-Type': 'application/vnd.flux',
                'Accept': 'application/csv'
            },
            body: fluxQuery
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const csvData = await response.text();
        return parseInfluxCSV(csvData);

    } catch (error) {
        console.error('InfluxDB Query Error:', error);
        showError(`Errore connessione InfluxDB: ${error.message}`);
        return null;
    }
}

/**
 * Parse InfluxDB CSV response
 */
function parseInfluxCSV(csvData) {
    const lines = csvData.trim().split('\n');
    if (lines.length < 2) return [];

    const headers = lines[0].split(',');
    const data = [];

    for (let i = 1; i < lines.length; i++) {
        if (lines[i].trim() === '') continue;

        const values = lines[i].split(',');
        const row = {};

        headers.forEach((header, index) => {
            const cleanHeader = header.trim();
            const cleanValue = values[index] ? values[index].trim() : '';

            if (cleanValue !== '') {
                if (!isNaN(cleanValue) && cleanValue !== '') {
                    row[cleanHeader] = parseFloat(cleanValue);
                } else {
                    row[cleanHeader] = cleanValue;
                }
            }
        });

        if (Object.keys(row).length > 0) {
            data.push(row);
        }
    }

    return data;
}

/**
 * Update connection status
 */
function updateConnectionStatus(connected, message = '') {
    const statusEl = document.getElementById('connectionStatus');
    isConnected = connected;

    if (connected) {
        statusEl.className = 'connection-status connected';
        statusEl.innerHTML = '🟢 Connesso';
    } else {
        statusEl.className = 'connection-status error';
        statusEl.innerHTML = `🔴 ${message || 'Disconnesso'}`;
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorContainer = document.getElementById('errorContainer');
    errorContainer.innerHTML = `<div class="error-message">⚠️ ${message}</div>`;
    updateConnectionStatus(false, 'Errore');
}

/**
 * Clear errors
 */
function clearErrors() {
    document.getElementById('errorContainer').innerHTML = '';
}

/**
 * Update KPIs with mock data (since database might be empty)
 */
async function updateKPIs() {
    try {
        // For now, use mock data to test the interface
        // Plant Status - simulate based on current time
        const isOnline = new Date().getSeconds() % 2 === 0; // Alternate every second for demo

        const plantStatusEl = document.getElementById('plant-status');
        if (isOnline) {
            plantStatusEl.innerHTML = '<span class="status-online">🟢 ONLINE</span>';
        } else {
            plantStatusEl.innerHTML = '<span class="status-critical">🔴 OFFLINE</span>';
        }

        // Mock data for other KPIs
        const piecesCount = Math.floor(Math.random() * 20) + 5;
        document.getElementById('pieces-count').innerHTML = `<span class="status-info">${piecesCount}</span>`;

        const alertsCount = Math.floor(Math.random() * 3);
        const alertsEl = document.getElementById('alerts-count');
        if (alertsCount === 0) {
            alertsEl.innerHTML = '<span class="status-online">0</span>';
        } else {
            alertsEl.innerHTML = `<span class="status-critical">${alertsCount}</span>`;
        }

        const totalPower = (Math.random() * 8 + 2).toFixed(1);
        document.getElementById('total-power').innerHTML = `<span class="status-info">${totalPower}</span>`;

        updateConnectionStatus(true);

    } catch (error) {
        console.error('Error updating KPIs:', error);
        showError('Errore aggiornamento KPI');
    }
}

/**
 * Update temperature chart with mock data
 */
async function updateTemperatureChart() {
    try {
        if (!charts.temperature) return;

        // Generate mock temperature data
        const machines = ['Milling1', 'Milling2', 'Lathe1', 'Saw1'];
        const now = new Date();
        const labels = [];

        // Generate last 10 time points
        for (let i = 9; i >= 0; i--) {
            const time = new Date(now.getTime() - i * 60000); // Every minute
            labels.push(time.toLocaleTimeString('it-IT', {
                hour: '2-digit',
                minute: '2-digit'
            }));
        }

        const datasets = machines.map((machine, index) => {
            const colors = ['#48bb78', '#ed8936', '#4299e1', '#9f7aea'];
            const baseTemp = 45 + index * 10;
            const data = labels.map(() => baseTemp + Math.random() * 20 - 10);

            return {
                label: machine,
                data: data,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                tension: 0.4,
                borderWidth: 3
            };
        });

        charts.temperature.data.labels = labels;
        charts.temperature.data.datasets = datasets;
        charts.temperature.update('none');

    } catch (error) {
        console.error('Error updating temperature chart:', error);
    }
}

/**
 * Update power chart with mock data
 */
async function updatePowerChart() {
    try {
        if (!charts.power) return;

        const now = new Date();
        const labels = [];
        const values = [];

        // Generate last 10 time points
        for (let i = 9; i >= 0; i--) {
            const time = new Date(now.getTime() - i * 60000); // Every minute
            labels.push(time.toLocaleTimeString('it-IT', {
                hour: '2-digit',
                minute: '2-digit'
            }));
            values.push((Math.random() * 6 + 2).toFixed(1)); // 2-8 kW
        }

        charts.power.data.labels = labels;
        charts.power.data.datasets = [{
            label: 'Consumo Totale',
            data: values,
            borderColor: '#00d4ff',
            backgroundColor: 'rgba(0, 212, 255, 0.2)',
            tension: 0.4,
            fill: true,
            borderWidth: 3
        }];

        charts.power.update('none');

    } catch (error) {
        console.error('Error updating power chart:', error);
    }
}

/**
 * Update machine status
 */
async function updateMachineStatus() {
    try {
        const machines = [
            { name: 'Milling1', temp: 45.2 + Math.random() * 20, power: 2.3 + Math.random() * 2 },
            { name: 'Milling2', temp: 52.1 + Math.random() * 15, power: 3.1 + Math.random() * 1.5 },
            { name: 'Lathe1', temp: 38.5 + Math.random() * 25, power: 1.8 + Math.random() * 2.5 },
            { name: 'Saw1', temp: 28.3 + Math.random() * 15, power: 0.5 + Math.random() * 1 }
        ];

        const machineGrid = document.getElementById('machineGrid');
        machineGrid.innerHTML = '';

        for (const machine of machines) {
            const temp = machine.temp;
            const power = machine.power;

            let statusClass = 'online';
            let statusText = '🟢 Operativa';
            let tempClass = 'status-online';

            if (temp > 85) {
                statusClass = 'critical';
                statusText = '🔴 Critica';
                tempClass = 'status-critical';
            } else if (temp > 70) {
                statusClass = 'warning';
                statusText = '🟡 Attenzione';
                tempClass = 'status-warning';
            } else if (power < 0.1) {
                statusClass = 'offline';
                statusText = '⚫ Idle';
                tempClass = 'status-info';
            }

            // Get ML prediction
            const mlPrediction = await getMachinePrediction(machine.name);

            const machineCard = document.createElement('div');
            machineCard.className = `machine-card ${statusClass} fade-in`;
            machineCard.innerHTML = `
                <div class="machine-header">
                    <div class="machine-name">${machine.name}</div>
                    <div class="machine-ml-badge">🤖 ML</div>
                </div>
                <div class="machine-metrics">
                    <div class="metric">
                        <div class="metric-value ${tempClass}">${temp.toFixed(1)}°C</div>
                        <div class="metric-label">Temperatura</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value status-info">${power.toFixed(1)} kW</div>
                        <div class="metric-label">Potenza</div>
                    </div>
                </div>
                <div class="machine-status">${statusText}</div>
                <div class="ml-prediction">
                    🔧 Manutenzione: ${mlPrediction.maintenance}<br>
                    📊 Efficienza: ${mlPrediction.efficiency}
                </div>
            `;

            machineGrid.appendChild(machineCard);
        }

    } catch (error) {
        console.error('Error updating machine status:', error);
    }
}

/**
 * Get ML prediction for a machine (mock data)
 */
async function getMachinePrediction(machine) {
    // Mock ML predictions
    const maintenanceDays = Math.floor(Math.random() * 25) + 5;
    const efficiency = (Math.random() * 15 + 80).toFixed(1);

    return {
        maintenance: `${maintenanceDays} giorni`,
        efficiency: `${efficiency}%`
    };
}

/**
 * Update all data
 */
async function updateAllData() {
    try {
        clearErrors();

        // Update all sections in parallel
        await Promise.all([
            updateKPIs(),
            updateTemperatureChart(),
            updatePowerChart(),
            updateMachineStatus()
        ]);

        updateConnectionStatus(true);
        lastUpdateTime = new Date();

        // Update timestamp
        document.getElementById('last-update').textContent =
            lastUpdateTime.toLocaleTimeString('it-IT');

        console.log('📊 Data updated successfully');

    } catch (error) {
        console.error('Error updating data:', error);
        showError('Errore generale aggiornamento dati');
    }
}

/**
 * Handle window resize to fix canvas dimensions
 */
function handleResize() {
    fixCanvasDimensions();
    // Recreate charts if needed
    if (Object.keys(charts).length === 0) {
        initCharts();
    }
}

// Add resize listener
window.addEventListener('resize', handleResize);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard);

// Export functions for use by other modules
window.DashboardAPI = {
    updateAllData,
    queryInfluxDB,
    showError,
    clearErrors,
    CONFIG
};