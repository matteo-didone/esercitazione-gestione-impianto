"""
Data Processor Module
Trasforma i dati MQTT in formato InfluxDB e rileva anomalie
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes and transforms data from MQTT to InfluxDB format"""
    
    def __init__(self):
        self.anomaly_count = 0
        self.processed_count = 0
    
    def process_sensor_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process sensor data from MQTT message
        Input: {"entity": "Milling1", "data": {...}, "timestamp": "..."}
        Output: InfluxDB point format
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
            
            # Check for anomalies
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
    
    def process_machine_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process machine event from MQTT message
        Input: {"entity": "Milling1", "event": "setup_start", "data": {...}, "timestamp": "..."}
        """
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
        """
        Process piece tracking event from MQTT message
        Input: {"entity": "piece", "event": "move_start", "data": {...}, "timestamp": "..."}
        """
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
            # This might need to be enriched from a lookup table
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
        """Detect anomalies in sensor data"""
        anomalies = []
        
        # Temperature anomalies
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
        
        # RPM anomalies
        rpm = fields.get('rpm_spindle')
        if rpm is not None:
            machine_type = self._get_machine_type(machine)
            if machine_type == 'Milling':
                if rpm > 4000 or rpm < 1000:
                    anomalies.append(f"Abnormal RPM for milling: {rpm}")
            elif machine_type == 'Lathe':
                if rpm > 3000 or rpm < 500:
                    anomalies.append(f"Abnormal RPM for lathe: {rpm}")
        
        return anomalies
    
    def _get_piece_material(self, piece_id: str) -> Optional[str]:
        """Get material type for piece (simplified lookup)"""
        # Simple heuristic based on piece ID
        # In a real system, this would query a database
        if piece_id.startswith('PZ00'):
            # First pieces are steel
            return 'steel'
        elif piece_id.startswith('PZ01'):
            # Later pieces might be aluminum
            return 'alu'
        else:
            return None
    
    def _estimate_distance(self, from_station: str, to_station: str) -> float:
        """Estimate distance between stations (meters)"""
        # Simplified distance matrix
        distances = {
            ('Warehouse', 'Saw1'): 30.0,
            ('Saw1', 'Milling1'): 25.0,
            ('Saw1', 'Milling2'): 35.0,
            ('Saw1', 'Lathe1'): 40.0,
            ('Milling1', 'Warehouse'): 45.0,
            ('Milling2', 'Warehouse'): 50.0,
            ('Lathe1', 'Warehouse'): 55.0,
        }
        
        # Try both directions
        distance = distances.get((from_station, to_station))
        if distance is None:
            distance = distances.get((to_station, from_station))
        
        return distance or 30.0  # Default distance
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'processed_count': self.processed_count,
            'anomaly_count': self.anomaly_count,
            'anomaly_rate': self.anomaly_count / max(self.processed_count, 1)
        }

    def reset_stats(self):
        """Reset processing statistics"""
        self.processed_count = 0
        self.anomaly_count = 0