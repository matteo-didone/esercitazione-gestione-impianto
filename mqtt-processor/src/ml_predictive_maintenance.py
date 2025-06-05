"""
Predictive Maintenance Module - FIXED VERSION
Predice guasti delle macchine usando Isolation Forest e analisi temporale
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional, Tuple
import joblib
import os

logger = logging.getLogger(__name__)

class PredictiveMaintenanceModel:
    """
    Modello per manutenzione predittiva basato su:
    - Isolation Forest per anomaly detection
    - Analisi trend temporali
    - Pattern di usura utensili
    """
    
    def __init__(self, models_dir: str = "/app/ml_models"):
        self.models_dir = models_dir
        self.models = {}  # machine -> IsolationForest model
        self.scalers = {}  # machine -> StandardScaler
        self.feature_history = {}  # machine -> list of feature vectors
        self.baseline_metrics = {}  # machine -> normal operating ranges
        
        # Ensure models directory exists
        os.makedirs(models_dir, exist_ok=True)
        
        # Model parameters
        self.contamination = 0.1  # Expected 10% anomalous data
        self.min_samples_for_training = 10  # REDUCED from 100
        self.max_history_length = 1000
        
        logger.info("🤖 Predictive Maintenance model initialized")
    
    def extract_features(self, sensor_data: List[Dict]) -> np.ndarray:
        """
        Estrae features per ML da dati sensori - FIXED VERSION
        """
        if len(sensor_data) < 3:  # Reduced minimum
            return np.zeros(10)  # Not enough data
        
        # Extract time series with SAFE handling
        timestamps = []
        temperatures = []
        powers = []
        vibrations = []
        rpms = []
        tool_wears = []
        
        # SAFE extraction with None checks
        for d in sensor_data:
            if d.get('timestamp'):
                timestamps.append(d['timestamp'])
            
            temp = d.get('temperature')
            if temp is not None:
                temperatures.append(float(temp))
            
            power = d.get('power') 
            if power is not None:
                powers.append(float(power))
            
            vib = d.get('vibration_level')
            if vib is not None:
                vibrations.append(float(vib))
            
            rpm = d.get('rpm_spindle')
            if rpm is not None:
                rpms.append(float(rpm))
            
            wear = d.get('tool_wear')
            if wear is not None:
                tool_wears.append(float(wear))
        
        # If we don't have enough valid data, return zeros
        if len(temperatures) < 2 or len(powers) < 2:
            return np.zeros(10)
        
        features = []
        
        # 1. Temperature trend (°C/hour) - SAFE
        try:
            if len(timestamps) >= 2 and len(temperatures) >= 2:
                time_diff_hours = max(0.1, (timestamps[-1] - timestamps[0]).total_seconds() / 3600)
                temp_slope = (temperatures[-1] - temperatures[0]) / time_diff_hours
            else:
                temp_slope = 0.0
        except:
            temp_slope = 0.0
        features.append(temp_slope)
        
        # 2. Temperature variance - SAFE
        temp_variance = np.var(temperatures) if len(temperatures) > 1 else 0.0
        features.append(temp_variance)
        
        # 3. Vibration trend - SAFE
        try:
            if len(vibrations) >= 2 and len(timestamps) >= 2:
                time_diff_hours = max(0.1, (timestamps[-1] - timestamps[0]).total_seconds() / 3600)
                vib_slope = (vibrations[-1] - vibrations[0]) / time_diff_hours
            else:
                vib_slope = 0.0
        except:
            vib_slope = 0.0
        features.append(vib_slope)
        
        # 4. Vibration variance - SAFE
        vib_variance = np.var(vibrations) if len(vibrations) > 1 else 0.0
        features.append(vib_variance)
        
        # 5. Power trend - SAFE
        try:
            if len(powers) >= 2 and len(timestamps) >= 2:
                time_diff_hours = max(0.1, (timestamps[-1] - timestamps[0]).total_seconds() / 3600)
                power_slope = (powers[-1] - powers[0]) / time_diff_hours
            else:
                power_slope = 0.0
        except:
            power_slope = 0.0
        features.append(power_slope)
        
        # 6. Power variance - SAFE
        power_variance = np.var(powers) if len(powers) > 1 else 0.0
        features.append(power_variance)
        
        # 7. Operating efficiency - SAFE
        avg_power = np.mean(powers) if powers else 1.0
        avg_rpm = np.mean(rpms) if rpms else 2500.0
        efficiency = avg_power / max(avg_rpm, 100) * 1000  # Normalize
        features.append(efficiency)
        
        # 8. Current tool wear - SAFE
        current_tool_wear = tool_wears[-1] if tool_wears else 0.0
        features.append(current_tool_wear)
        
        # 9. Operating hours - SAFE
        operating_hours = len(sensor_data) * 3 / 3600  # 3 second intervals
        features.append(operating_hours)
        
        # 10. Max temperature - SAFE
        max_temp = max(temperatures) if temperatures else 25.0
        features.append(max_temp)
        
        return np.array(features, dtype=float)
    
    def update_baseline(self, machine: str, features: np.ndarray):
        """Aggiorna metriche baseline per macchina"""
        if machine not in self.baseline_metrics:
            self.baseline_metrics[machine] = {
                'temp_normal_range': [20, 60],
                'vib_normal_range': [0, 2.0],
                'power_normal_range': [0.5, 4.0],
                'efficiency_normal': 1.0
            }
        
        # Update running averages safely
        baseline = self.baseline_metrics[machine]
        
        try:
            # Temperature baseline (features[1] = temp variance, features[9] = max temp)
            if len(features) > 9:
                baseline['temp_normal_range'][1] = max(baseline['temp_normal_range'][1], features[9] * 0.8)
            
            # Vibration baseline (features[3] = vib variance)
            if len(features) > 3:
                baseline['vib_normal_range'][1] = max(baseline['vib_normal_range'][1], features[3] * 2.0)
            
            # Power baseline (features[5] = power variance)
            if len(features) > 5:
                baseline['power_normal_range'][1] = max(baseline['power_normal_range'][1], features[5] * 3.0)
            
            # Efficiency baseline (features[6])
            if len(features) > 6:
                baseline['efficiency_normal'] = features[6] * 0.9  # 90% of current as normal
        except Exception as e:
            logger.warning(f"Error updating baseline for {machine}: {e}")
    
    def add_training_data(self, machine: str, sensor_data: List[Dict], is_healthy: bool = True):
        """
        Aggiunge dati per training del modello
        """
        try:
            features = self.extract_features(sensor_data)
            
            # Check if features are valid
            if np.all(features == 0) or np.any(np.isnan(features)) or np.any(np.isinf(features)):
                logger.warning(f"Invalid features extracted for {machine}, skipping")
                return
            
            if machine not in self.feature_history:
                self.feature_history[machine] = []
            
            # Add label to features (1 = healthy, -1 = anomalous)
            labeled_features = np.append(features, 1 if is_healthy else -1)
            self.feature_history[machine].append(labeled_features)
            
            # Update baseline only with healthy data
            if is_healthy:
                self.update_baseline(machine, features)
            
            # Maintain history size
            if len(self.feature_history[machine]) > self.max_history_length:
                self.feature_history[machine] = self.feature_history[machine][-self.max_history_length:]
            
            logger.debug(f"Added training data for {machine}: {len(self.feature_history[machine])} samples")
            
        except Exception as e:
            logger.error(f"Error adding training data for {machine}: {e}")
    
    def train_model(self, machine: str) -> bool:
        """
        Addestra modello Isolation Forest per una macchina
        """
        if machine not in self.feature_history:
            logger.warning(f"No training data for machine {machine}")
            return False
        
        history = np.array(self.feature_history[machine])
        if len(history) < self.min_samples_for_training:
            logger.warning(f"Insufficient training data for {machine}: {len(history)} < {self.min_samples_for_training}")
            return False
        
        # Separate features and labels
        X = history[:, :-1]  # All columns except last (label)
        y = history[:, -1]   # Last column (label)
        
        # Use only healthy data for training (Isolation Forest is unsupervised)
        healthy_data = X[y == 1]
        
        if len(healthy_data) < self.min_samples_for_training // 2:
            logger.warning(f"Insufficient healthy data for {machine}: {len(healthy_data)}")
            return False
        
        try:
            # Check for valid data
            if np.any(np.isnan(healthy_data)) or np.any(np.isinf(healthy_data)):
                logger.warning(f"Invalid data in training set for {machine}")
                return False
            
            # Initialize and train scaler
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(healthy_data)
            
            # Initialize and train Isolation Forest
            model = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=50  # Reduced for faster training
            )
            model.fit(X_scaled)
            
            # Store model and scaler
            self.models[machine] = model
            self.scalers[machine] = scaler
            
            # Save to disk
            self._save_model(machine, model, scaler)
            
            logger.info(f"✅ Trained predictive maintenance model for {machine} with {len(healthy_data)} samples")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error training model for {machine}: {e}")
            return False
    
    def predict_failure_probability(self, machine: str, sensor_data: List[Dict]) -> Tuple[float, Dict]:
        """
        Predice probabilità di guasto nei prossimi giorni
        """
        if machine not in self.models:
            # Try to load from disk
            if not self._load_model(machine):
                logger.warning(f"No trained model for {machine}")
                return 0.0, {"error": "No trained model"}
        
        try:
            features = self.extract_features(sensor_data)
            
            # Check for valid features
            if np.all(features == 0) or np.any(np.isnan(features)) or np.any(np.isinf(features)):
                return 0.0, {"error": "Invalid features"}
            
            # Scale features
            features_scaled = self.scalers[machine].transform([features])
            
            # Get anomaly score (-1 = anomaly, 1 = normal)
            anomaly_score = self.models[machine].decision_function(features_scaled)[0]
            
            # Convert to failure probability (0-100%)
            # Anomaly score typically ranges from -0.5 to 0.5
            # More negative = more anomalous = higher failure probability
            failure_probability = max(0, min(100, (0.5 - anomaly_score) * 100))
            
            # Generate insights
            insights = self._generate_insights(machine, features, failure_probability)
            
            return failure_probability, insights
            
        except Exception as e:
            logger.error(f"❌ Error predicting failure for {machine}: {e}")
            return 0.0, {"error": str(e)}
    
    def _generate_insights(self, machine: str, features: np.ndarray, failure_prob: float) -> Dict:
        """Genera insights dettagliati sulla predizione"""
        insights = {
            "prediction_timestamp": datetime.now().isoformat(),
            "failure_probability": failure_prob,
            "risk_level": "low"
        }
        
        # Risk level
        if failure_prob > 70:
            insights["risk_level"] = "critical"
            insights["recommended_action"] = "Schedule immediate maintenance"
        elif failure_prob > 40:
            insights["risk_level"] = "high"
            insights["recommended_action"] = "Schedule maintenance within 24h"
        elif failure_prob > 20:
            insights["risk_level"] = "medium"
            insights["recommended_action"] = "Monitor closely, plan maintenance"
        else:
            insights["recommended_action"] = "Continue normal operation"
        
        # Feature analysis - SAFE
        if machine in self.baseline_metrics and len(features) >= 10:
            baseline = self.baseline_metrics[machine]
            
            # Temperature analysis (features[9] = max temp)
            if features[9] > baseline['temp_normal_range'][1]:
                insights["temperature_warning"] = f"High temperature: {features[9]:.1f}°C"
            
            # Vibration analysis (features[3] = vib variance)
            if features[3] > baseline['vib_normal_range'][1]:
                insights["vibration_warning"] = f"High vibration variance: {features[3]:.3f}"
            
            # Tool wear analysis (features[7])
            if features[7] > 0.8:
                insights["tool_wear_warning"] = f"High tool wear: {features[7]:.2f}"
        
        return insights
    
    def _save_model(self, machine: str, model, scaler):
        """Salva modello su disco"""
        try:
            model_path = os.path.join(self.models_dir, f"{machine}_isolation_forest.pkl")
            scaler_path = os.path.join(self.models_dir, f"{machine}_scaler.pkl")
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            
            logger.debug(f"Saved model for {machine}")
        except Exception as e:
            logger.error(f"Error saving model for {machine}: {e}")
    
    def _load_model(self, machine: str) -> bool:
        """Carica modello da disco"""
        try:
            model_path = os.path.join(self.models_dir, f"{machine}_isolation_forest.pkl")
            scaler_path = os.path.join(self.models_dir, f"{machine}_scaler.pkl")
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.models[machine] = joblib.load(model_path)
                self.scalers[machine] = joblib.load(scaler_path)
                logger.info(f"Loaded model for {machine}")
                return True
            
        except Exception as e:
            logger.error(f"Error loading model for {machine}: {e}")
        
        return False
    
    def get_model_stats(self) -> Dict:
        """Ritorna statistiche sui modelli"""
        stats = {
            "trained_machines": list(self.models.keys()),
            "total_models": len(self.models),
            "training_data_sizes": {}
        }
        
        for machine, history in self.feature_history.items():
            stats["training_data_sizes"][machine] = len(history)
        
        return stats