/**
 * ML Integration JavaScript
 * Handles machine learning predictions and ML-specific visualizations
 */

// ML API Configuration
const ML_CONFIG = {
    api_url: 'http://localhost:5001',
    retry_attempts: 3,
    timeout: 5000
};

// Global ML data cache
let mlCache = {
    maintenance: {},
    energy: {},
    anomalies: {},
    efficiency: {},
    models_status: {},
    last_update: null
};

// ML Charts
let mlCharts = {};

/**
 * Initialize ML components
 */
async function initMLComponents() {
    console.log('🤖 Initializing ML components...');

    // Initialize ML charts
    initMLCharts();

    // Load initial ML data
    await updateMLData();

    // Setup ML-specific auto-refresh (every 30 seconds)
    setInterval(updateMLData, 30000);

    console.log('✅ ML components initialized');
}

/**
 * Initialize ML-specific charts
 */
function initMLCharts() {
    const mlChartConfig = {
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
                grid: { color: 'rgba(102, 126, 234, 0.2)' }
            },
            y: {
                ticks: { color: '#a0aec0' },
                grid: { color: 'rgba(102, 126, 234, 0.2)' }
            }
        }
    };

    // Maintenance Prediction Chart
    mlCharts.maintenance = new Chart(document.getElementById('maintenanceChart'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Giorni alla Manutenzione',
                data: [],
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: '#667eea',
                borderWidth: 2
            }]
        },
        options: {
            ...mlChartConfig,
            scales: {
                ...mlChartConfig.scales,
                y: {
                    ...mlChartConfig.scales.y,
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

    // Energy Optimization Chart
    mlCharts.energy = new Chart(document.getElementById('energyOptChart'), {
        type: 'doughnut',
        data: {
            labels: ['Attuale', 'Ottimizzato', 'Risparmio'],
            datasets: [{
                data: [0, 0, 0],
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
            ...mlChartConfig,
            plugins: {
                ...mlChartConfig.plugins,
                legend: {
                    position: 'bottom',
                    labels: { color: '#ffffff' }
                }
            }
        }
    });

    console.log('📊 ML Charts initialized');
}

/**
 * Call ML API endpoint
 */
async function callMLAPI(endpoint, params = {}) {
    const url = new URL(`${ML_CONFIG.api_url}/api/ml${endpoint}`);
    Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));

    for (let attempt = 1; attempt <= ML_CONFIG.retry_attempts; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), ML_CONFIG.timeout);

            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            console.warn(`ML API attempt ${attempt}/${ML_CONFIG.retry_attempts} failed:`, error.message);

            if (attempt === ML_CONFIG.retry_attempts) {
                console.error(`ML API call failed after ${ML_CONFIG.retry_attempts} attempts:`, error);
                return null;
            }

            // Wait before retry (exponential backoff)
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
}

/**
 * Update ML KPIs
 */
async function updateMLKPIs() {
    try {
        // Maintenance Prediction
        const maintenanceData = await callMLAPI('/maintenance/predict');
        if (maintenanceData) {
            mlCache.maintenance = maintenanceData;

            // Find machine with earliest maintenance need
            let earliestMaintenance = Infinity;
            let machineName = 'N/A';

            Object.entries(maintenanceData).forEach(([machine, data]) => {
                if (data.days_until_maintenance && data.days_until_maintenance < earliestMaintenance) {
                    earliestMaintenance = data.days_until_maintenance;
                    machineName = machine;
                }
            });

            const maintenanceEl = document.getElementById('maintenance-prediction');
            const confidenceEl = document.getElementById('maintenance-confidence');

            if (earliestMaintenance !== Infinity) {
                const statusClass = earliestMaintenance < 7 ? 'status-critical' :
                    earliestMaintenance < 14 ? 'status-warning' : 'status-online';

                maintenanceEl.innerHTML = `<span class="${statusClass}">${earliestMaintenance}d</span>`;
                confidenceEl.textContent = `${machineName} - ${(maintenanceData[machineName]?.confidence * 100 || 0).toFixed(0)}% confidence`;
            } else {
                maintenanceEl.innerHTML = '<span class="status-info">OK</span>';
                confidenceEl.textContent = 'Tutte le macchine OK';
            }
        }

        // Energy Optimization
        const energyData = await callMLAPI('/energy/optimize');
        if (energyData) {
            mlCache.energy = energyData;

            const savingsEl = document.getElementById('energy-optimization');
            const confidenceEl = document.getElementById('energy-confidence');

            const savings = energyData.savings_percentage || 0;
            const statusClass = savings > 15 ? 'status-online' :
                savings > 5 ? 'status-warning' : 'status-critical';

            savingsEl.innerHTML = `<span class="${statusClass}">${savings.toFixed(1)}%</span>`;
            confidenceEl.textContent = `${(energyData.confidence * 100 || 0).toFixed(0)}% ottimizzazione`;
        }

        // Efficiency Prediction
        const efficiencyData = await callMLAPI('/efficiency/predict');
        if (efficiencyData) {
            mlCache.efficiency = efficiencyData;

            const efficiencyEl = document.getElementById('efficiency-prediction');
            const trendEl = document.getElementById('efficiency-trend');

            const efficiency = efficiencyData.predicted_efficiency_24h || 0;
            const trend = efficiencyData.trend || 'stable';

            const statusClass = efficiency > 85 ? 'status-online' :
                efficiency > 70 ? 'status-warning' : 'status-critical';

            efficiencyEl.innerHTML = `<span class="${statusClass}">${efficiency.toFixed(1)}%</span>`;

            const trendIcon = trend === 'improving' ? '📈' :
                trend === 'declining' ? '📉' : '➡️';
            trendEl.textContent = `${trendIcon} ${trend}`;
        }

        // Anomaly Detection
        const anomalyData = await callMLAPI('/anomaly/detect');
        if (anomalyData) {
            mlCache.anomalies = anomalyData;

            // Calculate overall anomaly score
            const scores = Object.values(anomalyData).map(d => d.anomaly_score || 0);
            const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;

            const anomalyEl = document.getElementById('anomaly-score');
            const statusEl = document.getElementById('anomaly-status');

            const statusClass = avgScore > 0.8 ? 'status-critical' :
                avgScore > 0.6 ? 'status-warning' : 'status-online';

            anomalyEl.innerHTML = `<span class="${statusClass}">${(avgScore * 100).toFixed(0)}</span>`;

            const status = avgScore > 0.8 ? '🔴 Critico' :
                avgScore > 0.6 ? '🟡 Attenzione' : '🟢 Normale';
            statusEl.textContent = status;
        }

    } catch (error) {
        console.error('Error updating ML KPIs:', error);
    }
}

/**
 * Update ML charts
 */
async function updateMLCharts() {
    try {
        // Update maintenance chart
        if (mlCache.maintenance && Object.keys(mlCache.maintenance).length > 0) {
            const machines = Object.keys(mlCache.maintenance);
            const days = machines.map(m => mlCache.maintenance[m]?.days_until_maintenance || 0);

            mlCharts.maintenance.data.labels = machines;
            mlCharts.maintenance.data.datasets[0].data = days;

            // Color bars based on urgency
            mlCharts.maintenance.data.datasets[0].backgroundColor = days.map(d =>
                d < 7 ? 'rgba(245, 101, 101, 0.8)' :
                    d < 14 ? 'rgba(237, 137, 54, 0.8)' :
                        'rgba(72, 187, 120, 0.8)'
            );

            mlCharts.maintenance.update('none');
        }

        // Update energy chart
        if (mlCache.energy && mlCache.energy.current_consumption) {
            const current = mlCache.energy.current_consumption;
            const optimized = mlCache.energy.optimized_consumption;
            const savings = mlCache.energy.potential_savings;

            mlCharts.energy.data.datasets[0].data = [current, optimized, savings];
            mlCharts.energy.update('none');
        }

    } catch (error) {
        console.error('Error updating ML charts:', error);
    }
}

/**
 * Update ML models status
 */
async function updateMLModelsStatus() {
    try {
        const modelsData = await callMLAPI('/models/status');
        if (modelsData) {
            mlCache.models_status = modelsData;

            const modelsGrid = document.getElementById('mlModelsGrid');
            modelsGrid.innerHTML = '';

            Object.entries(modelsData).forEach(([modelName, modelData]) => {
                const statusClass = modelData.status === 'healthy' ? 'status-online' :
                    modelData.status === 'unavailable' ? 'status-critical' :
                        'status-warning';

                const statusIcon = modelData.status === 'healthy' ? '🟢' :
                    modelData.status === 'unavailable' ? '🔴' : '🟡';

                const modelCard = document.createElement('div');
                modelCard.className = 'ml-model-card fade-in';
                modelCard.innerHTML = `
                    <div class="model-name">${formatModelName(modelName)}</div>
                    <div class="model-status ${statusClass}">
                        ${statusIcon} ${modelData.status.toUpperCase()}
                    </div>
                    <div class="model-accuracy">
                        Accuracy: ${(modelData.accuracy * 100).toFixed(1)}%<br>
                        v${modelData.model_version}
                    </div>
                `;

                modelsGrid.appendChild(modelCard);
            });

            // Update ML status in footer
            const activeModels = Object.values(modelsData).filter(m => m.active).length;
            const totalModels = Object.keys(modelsData).length;
            document.getElementById('ml-status').textContent =
                `${activeModels}/${totalModels} attivi`;
        }

    } catch (error) {
        console.error('Error updating ML models status:', error);
        document.getElementById('ml-status').textContent = 'Errore connessione';
    }
}

/**
 * Get enhanced machine prediction with ML data
 */
async function getMachinePrediction(machine) {
    try {
        const predictions = {
            maintenance: 'N/A',
            efficiency: 'N/A',
            anomaly: 'N/A'
        };

        // Maintenance prediction
        if (mlCache.maintenance && mlCache.maintenance[machine]) {
            const days = mlCache.maintenance[machine].days_until_maintenance;
            const risk = mlCache.maintenance[machine].risk_level;

            if (days !== undefined) {
                const urgencyIcon = days < 7 ? '🔴' : days < 14 ? '🟡' : '🟢';
                predictions.maintenance = `${urgencyIcon} ${days}d (${risk})`;
            }
        }

        // Efficiency prediction
        if (mlCache.efficiency) {
            const efficiency = mlCache.efficiency.current_efficiency;
            if (efficiency !== undefined) {
                const effIcon = efficiency > 85 ? '🟢' : efficiency > 70 ? '🟡' : '🔴';
                predictions.efficiency = `${effIcon} ${efficiency.toFixed(1)}%`;
            }
        }

        // Anomaly detection
        if (mlCache.anomalies && mlCache.anomalies[machine]) {
            const score = mlCache.anomalies[machine].anomaly_score;
            const status = mlCache.anomalies[machine].status;

            if (score !== undefined) {
                const anomalyIcon = status === 'normal' ? '🟢' :
                    status === 'warning' ? '🟡' : '🔴';
                predictions.anomaly = `${anomalyIcon} ${(score * 100).toFixed(0)}%`;
            }
        }

        return predictions;

    } catch (error) {
        console.error(`Error getting ML prediction for ${machine}:`, error);
        return {
            maintenance: 'Error',
            efficiency: 'Error',
            anomaly: 'Error'
        };
    }
}

/**
 * Update all ML data
 */
async function updateMLData() {
    try {
        console.log('🤖 Updating ML data...');

        // Update all ML components
        await Promise.all([
            updateMLKPIs(),
            updateMLCharts(),
            updateMLModelsStatus()
        ]);

        mlCache.last_update = new Date();
        console.log('✅ ML data updated successfully');

    } catch (error) {
        console.error('Error updating ML data:', error);
    }
}

/**
 * Trigger model retraining
 */
async function retrain_models(modelType = 'all') {
    try {
        const response = await fetch(`${ML_CONFIG.api_url}/api/ml/retrain`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model_type: modelType })
        });

        if (response.ok) {
            const result = await response.json();
            console.log('🔄 Model retraining started:', result);

            // Show notification
            showMLNotification(`Retraining ${modelType} models started`, 'info');

            return result;
        } else {
            throw new Error(`Retraining failed: ${response.statusText}`);
        }

    } catch (error) {
        console.error('Error triggering retraining:', error);
        showMLNotification('Retraining failed', 'error');
        return null;
    }
}

/**
 * Show ML notification
 */
function showMLNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `ml-notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">
                ${type === 'error' ? '❌' : type === 'warning' ? '⚠️' : '🤖'}
            </span>
            <span class="notification-message">${message}</span>
        </div>
    `;

    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: rgba(102, 126, 234, 0.9);
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        border-left: 4px solid ${type === 'error' ? '#f56565' : type === 'warning' ? '#ed8936' : '#667eea'};
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 1001;
        animation: slideIn 0.3s ease-out;
    `;

    document.body.appendChild(notification);

    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

/**
 * Format model name for display
 */
function formatModelName(modelName) {
    const names = {
        'predictive_maintenance': 'Manutenzione Predittiva',
        'energy_optimizer': 'Ottimizzazione Energia',
        'anomaly_detector': 'Rilevamento Anomalie',
        'efficiency_predictor': 'Predizione Efficienza'
    };

    return names[modelName] || modelName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Get ML insights summary
 */
function getMLInsightsSummary() {
    const insights = [];

    // Maintenance insights
    if (mlCache.maintenance) {
        const urgentMachines = Object.entries(mlCache.maintenance)
            .filter(([machine, data]) => data.days_until_maintenance < 7)
            .map(([machine]) => machine);

        if (urgentMachines.length > 0) {
            insights.push({
                type: 'maintenance',
                severity: 'critical',
                message: `Manutenzione urgente richiesta per: ${urgentMachines.join(', ')}`
            });
        }
    }

    // Energy insights
    if (mlCache.energy && mlCache.energy.savings_percentage > 10) {
        insights.push({
            type: 'energy',
            severity: 'info',
            message: `Potenziale risparmio energetico: ${mlCache.energy.savings_percentage.toFixed(1)}%`
        });
    }

    // Anomaly insights
    if (mlCache.anomalies) {
        const criticalAnomalies = Object.entries(mlCache.anomalies)
            .filter(([machine, data]) => data.status === 'critical')
            .map(([machine]) => machine);

        if (criticalAnomalies.length > 0) {
            insights.push({
                type: 'anomaly',
                severity: 'critical',
                message: `Anomalie critiche rilevate su: ${criticalAnomalies.join(', ')}`
            });
        }
    }

    return insights;
}

/**
 * Enhanced machine status update with ML
 */
async function updateMachineStatusWithML() {
    try {
        const machineQuery = `
            from(bucket:"${window.DashboardAPI.CONFIG.influxdb.bucket}")
            |> range(start: -2m)
            |> filter(fn: (r) => r._measurement == "sensor_data")
            |> filter(fn: (r) => r._field == "temperature" or r._field == "power")
            |> group(columns: ["machine", "_field"])
            |> last()
            |> pivot(rowKey:["machine"], columnKey: ["_field"], valueColumn: "_value")
        `;

        const machineData = await window.DashboardAPI.queryInfluxDB(machineQuery);
        if (!machineData || machineData.length === 0) return;

        const machineGrid = document.getElementById('machineGrid');
        machineGrid.innerHTML = '';

        for (const machine of machineData) {
            if (!machine.machine) continue;

            const temp = machine.temperature || 0;
            const power = machine.power || 0;

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

            // Get ML predictions
            const mlPrediction = await getMachinePrediction(machine.machine);

            const machineCard = document.createElement('div');
            machineCard.className = `machine-card ${statusClass} fade-in`;
            machineCard.innerHTML = `
                <div class="machine-header">
                    <div class="machine-name">${machine.machine}</div>
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
                    🔧 ${mlPrediction.maintenance}<br>
                    📊 ${mlPrediction.efficiency}<br>
                    🎯 ${mlPrediction.anomaly}
                </div>
            `;

            machineGrid.appendChild(machineCard);
        }

    } catch (error) {
        console.error('Error updating machine status with ML:', error);
    }
}

// Add CSS for ML notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .notification-icon {
        font-size: 1.2rem;
    }
    
    .notification-message {
        font-weight: 500;
    }
`;
document.head.appendChild(style);

// Initialize ML components when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for main dashboard to initialize
    setTimeout(initMLComponents, 1000);
});

// Export ML functions for global access
window.MLIntegration = {
    updateMLData,
    getMachinePrediction,
    retrain_models,
    getMLInsightsSummary,
    updateMachineStatusWithML,
    mlCache
};

// Override the machine status update to include ML
if (window.DashboardAPI) {
    // Replace the original function
    window.updateMachineStatus = updateMachineStatusWithML;
}