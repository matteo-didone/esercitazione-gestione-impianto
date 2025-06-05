"""
Data Processor Module - ENHANCED WITH ML
Trasforma i dati MQTT in formato InfluxDB, rileva anomalie e integra ML
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

# Import ML modules
from .ml_predictive_maintenance import PredictiveMaintenanceModel
from .ml_energy_optimizer import EnergyOptimizer

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes and transforms data from MQTT to InfluxDB format with ML integration"""
    
    def __init__(self, config=None):
        self.anomaly_count = 0
        self.processed_count = 0
        
        # ML Components
        self.predictive_model = PredictiveMaintenanceModel()
        self.energy_optimizer = EnergyOptimizer()
        
        # ML data buffers (keep recent data for analysis)
        self.ml_data_buffer = {}
        self.buffer_size = 200  # Keep last 200 readings per machine
        
        # ML update intervals
        self.ml_prediction_interval = 10  # Run ML prediction every N messages
        self.ml_training_interval = 100   # Add training data every N messages
        
        logger.info("🤖 Data Processor initialized with ML capabilities")
    
    def process_sensor_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process sensor data from MQTT message with ML enhancement
        """
        try:
            entity = payload.get('entity')
            sensor_data = payload.get('data', {})
            timestamp_str = payload.get('timestamp')
            
            if not entity or not sensor_data:
                raise ValueError("Missing entity or data in sensor message")
            
            # Parse timestamp
            timestamp = self._parse_timestamp(timestamp_str)
            
            # Determine machine type from entity name
            machine_type = self._get_machine_type(entity)
            
            # Extract tags
            tags = {
                'machine': entity,
                'machine_type': machine_type,
                'location': 'workshop_A'  # Default location
            }
            
            # Extract fields (sensor values)
            fields = {}
            for key, value in sensor_data.items():
                if isinstance(value, (int, float)):
                    fields[key] = float(value)
            
            # ===== ML INTEGRATION =====
            
            # Add to ML buffer
            ml_data_point = {
                'timestamp': timestamp,
                'machine': entity,
                'temperature': sensor_data.get('temperature', 20.0),
                'power': sensor_data.get('power', 0.0),
                'rpm_spindle': sensor_data.get('rpm_spindle'),
                'feed_rate': sensor_data.get('feed_rate'),
                'vibration_level': sensor_data.get('vibration_level'),
                'cut_depth': sensor_data.get('cut_depth'),
                'blade_speed': sensor_data.get('blade_speed'),
                'material_feed': sensor_data.get('material_feed'),
                'tool_wear': self._estimate_tool_wear(entity)
            }
            
            self._add_to_ml_buffer(entity, ml_data_point)
            
            # Run ML analysis periodically
            if self.processed_count % self.ml_prediction_interval == 0:
                ml_insights = self._run_ml_analysis(entity)
                if ml_insights:
                    # Add ML predictions as fields
                    fields.update(ml_insights)
                    logger.debug(f"🤖 Added ML insights for {entity}: {list(ml_insights.keys())}")
            
            # Add training data periodically
            if self.processed_count % self.ml_training_interval == 0:
                self._add_ml_training_data(entity, ml_data_point)
            
            # Check for anomalies (original + ML enhanced)
            anomalies = self._detect_sensor_anomalies(entity, fields)
            if anomalies:
                logger.warning(f"🚨 Anomalies detected for {entity}: {anomalies}")
                self.anomaly_count += 1
            
            self.processed_count += 1
            
            return {
                'measurement': 'sensor_data',
                'tags': tags,
                'fields': fields,
                'time': timestamp,
                'anomalies': anomalies
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing sensor data: {e}")
            raise
    
    def _add_to_ml_buffer(self, machine: str, data_point: Dict):
        """Add data point to ML buffer"""
        if machine not in self.ml_data_buffer:
            self.ml_data_buffer[machine] = []
        
        self.ml_data_buffer[machine].append(data_point)
        
        # Maintain buffer size
        if len(self.ml_data_buffer[machine]) > self.buffer_size:
            self.ml_data_buffer[machine] = self.ml_data_buffer[machine][-self.buffer_size:]
    
    def _run_ml_analysis(self, machine: str) -> Dict[str, Any]:
        """Run ML analysis and return insights as fields"""
        if machine not in self.ml_data_buffer or len(self.ml_data_buffer[machine]) < 20:
            return {}
        
        ml_fields = {}
        
        try:
            # 1. Predictive Maintenance
            failure_prob, maintenance_insights = self.predictive_model.predict_failure_probability(
                machine, self.ml_data_buffer[machine]
            )
            
            if 'error' not in maintenance_insights:
                ml_fields['failure_probability'] = failure_prob
                ml_fields['maintenance_risk_level'] = maintenance_insights.get('risk_level', 'unknown')
                
                # Add specific warnings as separate fields
                if 'temperature_warning' in maintenance_insights:
                    ml_fields['ml_temp_warning'] = 1.0
                if 'vibration_warning' in maintenance_insights:
                    ml_fields['ml_vibration_warning'] = 1.0
                if 'tool_wear_warning' in maintenance_insights:
                    ml_fields['ml_tool_wear_warning'] = 1.0
            
            # 2. Energy Optimization (run less frequently)
            if self.processed_count % (self.ml_prediction_interval * 5) == 0:
                optimal_settings = self.energy_optimizer.optimize_settings(machine)
                
                if 'error' not in optimal_settings:
                    ml_fields['energy_savings_potential'] = optimal_settings.get('savings_potential_percent', 0)
                    ml_fields['optimal_rpm'] = optimal_settings.get('rpm_spindle', 0)
                    ml_fields['optimal_feed_rate'] = optimal_settings.get('feed_rate', 0)
                    ml_fields['efficiency_score'] = optimal_settings.get('efficiency_score', 0)
            
            # 3. Energy insights
            energy_insights = self.energy_optimizer.get_energy_insights(machine)
            if energy_insights.get('model_available'):
                ml_fields['avg_power_baseline'] = energy_insights.get('avg_power_consumption', 0)
                ml_fields['power_trend_score'] = self._trend_to_score(energy_insights.get('power_trend', 'stable'))
            
        except Exception as e:
            logger.error(f"❌ Error in ML analysis for {machine}: {e}")
        
        return ml_fields
    
    def _add_ml_training_data(self, machine: str, data_point: Dict):
        """Add data to ML training datasets"""
        try:
            # Add to predictive maintenance training (assume healthy operation unless anomalies detected)
            is_healthy = data_point.get('temperature', 0) < 85 and data_point.get('power', 0) < 8.0
            
            self.predictive_model.add_training_data(
                machine, 
                self.ml_data_buffer[machine][-50:],  # Last 50 points for context
                is_healthy=is_healthy
            )
            
            # Add to energy optimizer training
            self.energy_optimizer.add_training_data(machine, data_point)
            
            # Train models periodically
            if len(self.ml_data_buffer[machine]) % 500 == 0:
                logger.info(f"🔄 Training ML models for {machine}")
                self.predictive_model.train_model(machine)
                self.energy_optimizer.train_power_model(machine)
            
        except Exception as e:
            logger.error(f"❌ Error adding ML training data for {machine}: {e}")
    
    def _trend_to_score(self, trend: str) -> float:
        """Convert trend string to numerical score"""
        trend_scores = {
            'decreasing': 1.0,  # Good - power going down
            'stable': 0.5,      # Neutral
            'increasing': 0.0   # Bad - power going up
        }
        return trend_scores.get(trend, 0.5)
    
    def _estimate_tool_wear(self, machine: str) -> float:
        """Estimate tool wear based on operating time and conditions"""
        # Simple heuristic - in real system would track actual tool usage
        if machine not in self.ml_data_buffer:
            return 0.0
        
        # Estimate based on temperature and vibration trends
        recent_data = self.ml_data_buffer[machine][-10:] if machine in self.ml_data_buffer else []
        if not recent_data:
            return 0.0
        
        avg_temp = sum(d.get('temperature', 20) for d in recent_data) / len(recent_data)
        avg_vib = sum(d.get('vibration_level', 0) for d in recent_data) / len(recent_data)
        
        # Simple wear estimation
        wear = min(1.0, (avg_temp - 20) / 80 + avg_vib / 5.0)
        return max(0.0, wear)
    
    # ===== REST OF ORIGINAL METHODS (unchanged) =====
    
    def process_machine_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process machine event from MQTT message (unchanged)"""
        try:
            entity = payload.get('entity')
            event_type = payload.get('event')
            event_data = payload.get('data', {})
            timestamp_str = payload.get('timestamp')
            
            if not entity or not event_type:
                raise ValueError("Missing entity or event in machine event message")
            
            timestamp = self._parse_timestamp(timestamp_str)
            
            # Extract tags
            tags = {
                'machine': entity,
                'event_type': event_type
            }
            
            # Add additional tags from event data
            if 'piece_id' in event_data:
                tags['piece_id'] = event_data['piece_id']
            if 'tool' in event_data:
                tags['tool'] = event_data['tool']
            
            # Extract fields
            fields = {}
            
            # Duration (0 for start events, actual value for end events)
            if 'duration' in event_data:
                fields['duration'] = float(event_data['duration'])
            else:
                fields['duration'] = 0.0 if 'start' in event_type else None
            
            # Status
            if event_type.endswith('start'):
                fields['status'] = 'active'
            elif event_type.endswith('end'):
                fields['status'] = 'completed'
            else:
                fields['status'] = event_data.get('status', 'unknown')
            
            # Tool wear (if available)
            if 'tool_wear' in event_data:
                fields['tool_wear'] = float(event_data['tool_wear'])
            
            # Cycle time for processing end events
            if event_type == 'processing_end' and 'cycle_time' in event_data:
                fields['cycle_time'] = float(event_data['cycle_time'])
            
            # Remove None values
            fields = {k: v for k, v in fields.items() if v is not None}
            
            self.processed_count += 1
            
            return {
                'measurement': 'machine_events',
                'tags': tags,
                'fields': fields,
                'time': timestamp
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing machine event: {e}")
            raise
    
    def process_piece_tracking(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process piece tracking event from MQTT message (unchanged)"""
        try:
            event_type = payload.get('event')
            event_data = payload.get('data', {})
            timestamp_str = payload.get('timestamp')
            
            if not event_type or not event_data:
                raise ValueError("Missing event or data in piece tracking message")
            
            timestamp = self._parse_timestamp(timestamp_str)
            
            # Extract piece ID
            piece_id = event_data.get('piece_id')
            if not piece_id:
                raise ValueError("Missing piece_id in tracking event")
            
            # Extract tags
            tags = {
                'piece_id': piece_id,
                'event_type': event_type
            }
            
            # Add station information
            if 'from' in event_data:
                tags['from_station'] = event_data['from']
            if 'to' in event_data:
                tags['to_station'] = event_data['to']
            
            # Add material information (if available from context)
            material = self._get_piece_material(piece_id)
            if material:
                tags['material'] = material
            
            # Extract fields
            fields = {}
            
            # Duration (0 for start events)
            if event_type.endswith('start'):
                fields['duration'] = 0.0
            elif 'duration' in event_data:
                fields['duration'] = float(event_data['duration'])
            
            # Distance (estimated based on stations)
            if 'from' in event_data and 'to' in event_data:
                distance = self._estimate_distance(event_data['from'], event_data['to'])
                fields['distance'] = distance
            
            # Priority (default to normal)
            fields['priority'] = event_data.get('priority', 3)  # 1-5 scale, 3 = normal
            
            self.processed_count += 1
            
            return {
                'measurement': 'piece_tracking',
                'tags': tags,
                'fields': fields,
                'time': timestamp
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing piece tracking: {e}")
            raise
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return datetime.utcnow()
        
        try:
            # Try ISO format first
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                # Try other common formats
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            logger.warning(f"⚠️  Could not parse timestamp '{timestamp_str}', using current time")
            return datetime.utcnow()
    
    def _get_machine_type(self, machine_name: str) -> str:
        """Determine machine type from machine name"""
        machine_name_lower = machine_name.lower()
        
        if 'milling' in machine_name_lower:
            return 'Milling'
        elif 'lathe' in machine_name_lower:
            return 'Lathe'
        elif 'saw' in machine_name_lower:
            return 'Saw'
        else:
            return 'Unknown'
    
    def _detect_sensor_anomalies(self, machine: str, fields: Dict[str, float]) -> List[str]:
        """Detect anomalies in sensor data (enhanced with ML context)"""
        anomalies = []
        
        # Original threshold-based detection
        temp = fields.get('temperature')
        if temp is not None:
            if temp > 90.0:
                anomalies.append(f"Critical temperature: {temp}°C")
            elif temp > 80.0:
                anomalies.append(f"High temperature: {temp}°C")
        
        # Vibration anomalies (for milling machines)
        vibration = fields.get('vibration_level')
        if vibration is not None:
            if vibration > 3.0:
                anomalies.append(f"Critical vibration: {vibration}g")
            elif vibration > 2.5:
                anomalies.append(f"High vibration: {vibration}g")
        
        # Power anomalies
        power = fields.get('power')
        if power is not None:
            if power > 8.0:
                anomalies.append(f"Critical power consumption: {power}kW")
            elif power > 5.0:
                anomalies.append(f"High power consumption: {power}kW")
            elif power < 0.1:
                anomalies.append(f"Suspiciously low power: {power}kW")
        
        # ML-enhanced anomaly detection
        if fields.get('failure_probability', 0) > 70:
            anomalies.append(f"ML: High failure risk detected")
        
        if fields.get('ml_temp_warning'):
            anomalies.append(f"ML: Temperature pattern anomaly")
        
        if fields.get('ml_vibration_warning'):
            anomalies.append(f"ML: Vibration pattern anomaly")
        
        return anomalies
    
    def _get_piece_material(self, piece_id: str) -> Optional[str]:
        """Get material type for piece (simplified lookup)"""
        if piece_id.startswith('PZ00'):
            return 'steel'
        elif piece_id.startswith('PZ01'):
            return 'alu'
        else:
            return None
    
    def _estimate_distance(self, from_station: str, to_station: str) -> float:
        """Estimate distance between stations (meters)"""
        distances = {
            ('Warehouse', 'Saw1'): 30.0,
            ('Saw1', 'Milling1'): 25.0,
            ('Saw1', 'Milling2'): 35.0,
            ('Saw1', 'Lathe1'): 40.0,
            ('Milling1', 'Warehouse'): 45.0,
            ('Milling2', 'Warehouse'): 50.0,
            ('Lathe1', 'Warehouse'): 55.0,
        }
        
        distance = distances.get((from_station, to_station))
        if distance is None:
            distance = distances.get((to_station, from_station))
        
        return distance or 30.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics including ML stats"""
        base_stats = {
            'processed_count': self.processed_count,
            'anomaly_count': self.anomaly_count,
            'anomaly_rate': self.anomaly_count / max(self.processed_count, 1)
        }
        
        # Add ML statistics
        try:
            ml_stats = {
                'predictive_maintenance': self.predictive_model.get_model_stats(),
                'energy_optimization': self.energy_optimizer.get_optimization_stats(),
                'ml_buffer_sizes': {machine: len(data) for machine, data in self.ml_data_buffer.items()}
            }
            base_stats['ml_stats'] = ml_stats
        except Exception as e:
            logger.error(f"Error getting ML stats: {e}")
            base_stats['ml_stats'] = {"error": str(e)}
        
        return base_stats
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.processed_count = 0
        self.anomaly_count = 0