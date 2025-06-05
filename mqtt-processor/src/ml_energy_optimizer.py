"""
Energy Optimization Module
Ottimizza consumo energetico usando Random Forest e analisi efficienza
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from typing import Dict, List, Optional, Tuple
import joblib
import os

logger = logging.getLogger(__name__)

class EnergyOptimizer:
    """
    Ottimizzatore energetico che:
    - Predice consumo di potenza basato su parametri macchina
    - Suggerisce settaggi ottimali per ridurre consumi
    - Analizza pattern di efficienza energetica
    """
    
    def __init__(self, models_dir: str = "/app/ml_models"):
        self.models_dir = models_dir
        self.power_models = {}  # machine -> RandomForestRegressor
        self.efficiency_models = {}  # machine -> efficiency predictor
        self.scalers = {}  # machine -> StandardScaler
        self.training_data = {}  # machine -> DataFrame
        self.efficiency_baselines = {}  # machine -> baseline efficiency
        
        # Ensure models directory exists
        os.makedirs(models_dir, exist_ok=True)
        
        # Model parameters
        self.min_training_samples = 50
        self.model_params = {
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42,
            'n_jobs': -1
        }
        
        logger.info("⚡ Energy Optimizer initialized")
    
    def add_training_data(self, machine: str, sensor_data: Dict):
        """
        Aggiunge dati per training del modello energetico
        
        Args:
            machine: Nome macchina
            sensor_data: Dati sensori con timestamp
        """
        if machine not in self.training_data:
            self.training_data[machine] = []
        
        # Extract relevant features based on machine type
        training_sample = {
            'timestamp': sensor_data.get('timestamp', datetime.now()),
            'power': sensor_data.get('power', 0.0),
            'temperature': sensor_data.get('temperature', 20.0),
        }
        
        # Add machine-specific features
        machine_type = self._get_machine_type(machine)
        
        if machine_type == 'Milling':
            training_sample.update({
                'rpm_spindle': sensor_data.get('rpm_spindle', 2500),
                'feed_rate': sensor_data.get('feed_rate', 300),
                'vibration_level': sensor_data.get('vibration_level', 1.0)
            })
        elif machine_type == 'Lathe':
            training_sample.update({
                'rpm_spindle': sensor_data.get('rpm_spindle', 1500),
                'cut_depth': sensor_data.get('cut_depth', 2.0)
            })
        elif machine_type == 'Saw':
            training_sample.update({
                'blade_speed': sensor_data.get('blade_speed', 1800),
                'material_feed': sensor_data.get('material_feed', 1.0)
            })
        
        self.training_data[machine].append(training_sample)
        
        # Maintain reasonable data size
        if len(self.training_data[machine]) > 2000:
            self.training_data[machine] = self.training_data[machine][-2000:]
        
        logger.debug(f"Added energy training data for {machine}: {len(self.training_data[machine])} samples")
    
    def train_power_model(self, machine: str) -> bool:
        """
        Addestra modello per predire consumo di potenza
        
        Returns:
            bool: True se training successful
        """
        if machine not in self.training_data:
            logger.warning(f"No training data for {machine}")
            return False
        
        if len(self.training_data[machine]) < self.min_training_samples:
            logger.warning(f"Insufficient training data for {machine}: {len(self.training_data[machine])}")
            return False
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(self.training_data[machine])
            
            # Remove outliers (power consumption outside reasonable range)
            df = df[(df['power'] > 0.1) & (df['power'] < 15.0)]
            
            if len(df) < self.min_training_samples:
                logger.warning(f"Insufficient valid data after cleaning for {machine}")
                return False
            
            # Prepare features and target
            feature_columns = self._get_feature_columns(machine)
            X = df[feature_columns].fillna(0)
            y = df['power']
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Random Forest model
            model = RandomForestRegressor(**self.model_params)
            model.fit(X_train_scaled, y_train)
            
            # Validate model
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            logger.info(f"✅ Trained power model for {machine}: MAE={mae:.3f}, R²={r2:.3f}")
            
            # Store model and scaler
            self.power_models[machine] = model
            self.scalers[machine] = scaler
            
            # Calculate efficiency baseline
            self._calculate_efficiency_baseline(machine, df)
            
            # Save to disk
            self._save_power_model(machine, model, scaler)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error training power model for {machine}: {e}")
            return False
    
    def predict_power_consumption(self, machine: str, settings: Dict) -> Tuple[float, Dict]:
        """
        Predice consumo di potenza per dati settaggi
        
        Args:
            machine: Nome macchina
            settings: Parametri operativi (rpm, feed_rate, etc.)
            
        Returns:
            Tuple[float, Dict]: (predicted_power, insights)
        """
        if machine not in self.power_models:
            if not self._load_power_model(machine):
                return 0.0, {"error": "No trained model"}
        
        try:
            # Prepare features
            features = self._prepare_prediction_features(machine, settings)
            features_scaled = self.scalers[machine].transform([features])
            
            # Predict power
            predicted_power = self.power_models[machine].predict(features_scaled)[0]
            
            # Calculate efficiency
            efficiency = self._calculate_efficiency(machine, settings, predicted_power)
            
            insights = {
                "predicted_power": predicted_power,
                "efficiency_score": efficiency,
                "settings": settings
            }
            
            return predicted_power, insights
            
        except Exception as e:
            logger.error(f"❌ Error predicting power for {machine}: {e}")
            return 0.0, {"error": str(e)}
    
    def optimize_settings(self, machine: str, target_power: Optional[float] = None) -> Dict:
        """
        Trova settaggi ottimali per minimizzare consumo mantenendo produttività
        
        Args:
            machine: Nome macchina
            target_power: Consumo target (opzionale)
            
        Returns:
            Dict: Settaggi ottimali e insights
        """
        if machine not in self.power_models:
            if not self._load_power_model(machine):
                return {"error": "No trained model"}
        
        try:
            machine_type = self._get_machine_type(machine)
            best_settings = None
            best_efficiency = 0
            best_power = float('inf')
            
            # Generate parameter ranges based on machine type
            param_ranges = self._get_parameter_ranges(machine_type)
            
            # Grid search for optimal settings
            n_samples = 50  # Number of combinations to test
            
            for i in range(n_samples):
                # Random sampling within parameter ranges
                settings = {}
                for param, (min_val, max_val) in param_ranges.items():
                    settings[param] = np.random.uniform(min_val, max_val)
                
                # Add fixed parameters
                settings['temperature'] = 45.0  # Assume normal operating temp
                
                # Predict power and efficiency
                predicted_power, insights = self.predict_power_consumption(machine, settings)
                
                if predicted_power <= 0:
                    continue
                
                efficiency = insights.get('efficiency_score', 0)
                
                # Multi-objective optimization: efficiency + power
                if target_power:
                    # Minimize deviation from target power while maximizing efficiency
                    power_score = 1.0 / (1.0 + abs(predicted_power - target_power))
                    combined_score = 0.7 * efficiency + 0.3 * power_score
                else:
                    # Maximize efficiency while minimizing power
                    power_score = 1.0 / (1.0 + predicted_power)
                    combined_score = 0.6 * efficiency + 0.4 * power_score
                
                if combined_score > best_efficiency:
                    best_efficiency = combined_score
                    best_power = predicted_power
                    best_settings = settings.copy()
                    best_settings['predicted_power'] = predicted_power
                    best_settings['efficiency_score'] = efficiency
            
            if best_settings:
                # Calculate potential savings
                current_baseline = self._get_baseline_power(machine)
                savings_potential = max(0, (current_baseline - best_power) / current_baseline * 100)
                
                best_settings.update({
                    'optimization_timestamp': datetime.now().isoformat(),
                    'savings_potential_percent': savings_potential,
                    'recommended_action': self._get_optimization_recommendation(savings_potential)
                })
                
                logger.info(f"⚡ Optimized settings for {machine}: {savings_potential:.1f}% potential savings")
                
            return best_settings or {"error": "No valid optimization found"}
            
        except Exception as e:
            logger.error(f"❌ Error optimizing settings for {machine}: {e}")
            return {"error": str(e)}
    
    def _get_machine_type(self, machine: str) -> str:
        """Determina tipo macchina dal nome"""
        machine_lower = machine.lower()
        if 'milling' in machine_lower:
            return 'Milling'
        elif 'lathe' in machine_lower:
            return 'Lathe'
        elif 'saw' in machine_lower:
            return 'Saw'
        return 'Unknown'
    
    def _get_feature_columns(self, machine: str) -> List[str]:
        """Ritorna colonne features per tipo macchina"""
        machine_type = self._get_machine_type(machine)
        base_features = ['temperature']
        
        if machine_type == 'Milling':
            return base_features + ['rpm_spindle', 'feed_rate', 'vibration_level']
        elif machine_type == 'Lathe':
            return base_features + ['rpm_spindle', 'cut_depth']
        elif machine_type == 'Saw':
            return base_features + ['blade_speed', 'material_feed']
        
        return base_features
    
    def _get_parameter_ranges(self, machine_type: str) -> Dict:
        """Ritorna range parametri per ottimizzazione"""
        if machine_type == 'Milling':
            return {
                'rpm_spindle': (2000, 3500),
                'feed_rate': (200, 400),
                'vibration_level': (0.5, 2.0)
            }
        elif machine_type == 'Lathe':
            return {
                'rpm_spindle': (1000, 2500),
                'cut_depth': (0.5, 3.0)
            }
        elif machine_type == 'Saw':
            return {
                'blade_speed': (1500, 2200),
                'material_feed': (0.5, 1.5)
            }
        
        return {}
    
    def _prepare_prediction_features(self, machine: str, settings: Dict) -> np.ndarray:
        """Prepara features per predizione"""
        feature_columns = self._get_feature_columns(machine)
        features = []
        
        for col in feature_columns:
            features.append(settings.get(col, 0.0))
        
        return np.array(features)
    
    def _calculate_efficiency(self, machine: str, settings: Dict, power: float) -> float:
        """Calcola score di efficienza (0-1)"""
        machine_type = self._get_machine_type(machine)
        
        if machine_type == 'Milling':
            # Efficiency = (RPM * Feed Rate) / Power
            rpm = settings.get('rpm_spindle', 2500)
            feed = settings.get('feed_rate', 300)
            productivity = rpm * feed / 1000000  # Normalize
        elif machine_type == 'Lathe':
            # Efficiency = (RPM * Cut Depth) / Power
            rpm = settings.get('rpm_spindle', 1500)
            cut = settings.get('cut_depth', 2.0)
            productivity = rpm * cut / 10000  # Normalize
        else:
            # Default efficiency
            productivity = 1.0
        
        efficiency = productivity / max(power, 0.1)
        
        # Normalize to 0-1 scale
        baseline_efficiency = self.efficiency_baselines.get(machine, 0.5)
        normalized_efficiency = min(1.0, efficiency / baseline_efficiency)
        
        return max(0.0, normalized_efficiency)
    
    def _calculate_efficiency_baseline(self, machine: str, df: pd.DataFrame):
        """Calcola baseline di efficienza dalla training data"""
        try:
            machine_type = self._get_machine_type(machine)
            
            if machine_type == 'Milling':
                productivity = (df['rpm_spindle'] * df['feed_rate']) / 1000000
            elif machine_type == 'Lathe':
                productivity = (df['rpm_spindle'] * df['cut_depth']) / 10000
            else:
                productivity = pd.Series([1.0] * len(df))
            
            efficiency = productivity / df['power']
            self.efficiency_baselines[machine] = efficiency.median()
            
            logger.debug(f"Calculated efficiency baseline for {machine}: {self.efficiency_baselines[machine]:.3f}")
            
        except Exception as e:
            logger.error(f"Error calculating efficiency baseline for {machine}: {e}")
            self.efficiency_baselines[machine] = 0.5
    
    def _get_baseline_power(self, machine: str) -> float:
        """Ritorna consumo baseline per calcolo risparmi"""
        if machine not in self.training_data or not self.training_data[machine]:
            return 3.0  # Default baseline
        
        recent_data = self.training_data[machine][-100:]  # Last 100 samples
        powers = [d['power'] for d in recent_data]
        return np.median(powers) if powers else 3.0
    
    def _get_optimization_recommendation(self, savings_potential: float) -> str:
        """Genera raccomandazione basata su potenziale risparmio"""
        if savings_potential > 20:
            return "High savings potential - implement immediately"
        elif savings_potential > 10:
            return "Good savings potential - consider implementing"
        elif savings_potential > 5:
            return "Moderate savings potential - monitor and evaluate"
        else:
            return "Current settings are near optimal"
    
    def _save_power_model(self, machine: str, model, scaler):
        """Salva modello su disco"""
        try:
            model_path = os.path.join(self.models_dir, f"{machine}_power_model.pkl")
            scaler_path = os.path.join(self.models_dir, f"{machine}_power_scaler.pkl")
            baseline_path = os.path.join(self.models_dir, f"{machine}_efficiency_baseline.pkl")
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            joblib.dump(self.efficiency_baselines.get(machine, 0.5), baseline_path)
            
            logger.debug(f"Saved power model for {machine}")
        except Exception as e:
            logger.error(f"Error saving power model for {machine}: {e}")
    
    def _load_power_model(self, machine: str) -> bool:
        """Carica modello da disco"""
        try:
            model_path = os.path.join(self.models_dir, f"{machine}_power_model.pkl")
            scaler_path = os.path.join(self.models_dir, f"{machine}_power_scaler.pkl")
            baseline_path = os.path.join(self.models_dir, f"{machine}_efficiency_baseline.pkl")
            
            if all(os.path.exists(p) for p in [model_path, scaler_path, baseline_path]):
                self.power_models[machine] = joblib.load(model_path)
                self.scalers[machine] = joblib.load(scaler_path)
                self.efficiency_baselines[machine] = joblib.load(baseline_path)
                logger.info(f"Loaded power model for {machine}")
                return True
            
        except Exception as e:
            logger.error(f"Error loading power model for {machine}: {e}")
        
        return False
    
    def get_energy_insights(self, machine: str) -> Dict:
        """Ritorna insights energetici per dashboard"""
        insights = {
            "machine": machine,
            "timestamp": datetime.now().isoformat(),
            "model_available": machine in self.power_models
        }
        
        if machine in self.training_data and self.training_data[machine]:
            recent_data = self.training_data[machine][-100:]
            
            # Power statistics
            powers = [d['power'] for d in recent_data]
            insights.update({
                "avg_power_consumption": np.mean(powers),
                "power_trend": "stable",  # Could add trend analysis
                "efficiency_baseline": self.efficiency_baselines.get(machine, 0.5),
                "training_samples": len(self.training_data[machine])
            })
            
            # Power trend analysis
            if len(powers) > 20:
                recent_avg = np.mean(powers[-20:])
                older_avg = np.mean(powers[-40:-20]) if len(powers) >= 40 else recent_avg
                
                if recent_avg > older_avg * 1.1:
                    insights["power_trend"] = "increasing"
                elif recent_avg < older_avg * 0.9:
                    insights["power_trend"] = "decreasing"
        
        return insights
    
    def get_optimization_stats(self) -> Dict:
        """Ritorna statistiche sui modelli di ottimizzazione"""
        stats = {
            "trained_machines": list(self.power_models.keys()),
            "total_models": len(self.power_models),
            "training_data_sizes": {},
            "efficiency_baselines": self.efficiency_baselines.copy()
        }
        
        for machine, data in self.training_data.items():
            stats["training_data_sizes"][machine] = len(data)
        
        return stats