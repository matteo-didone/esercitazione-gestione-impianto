"""
Configuration module for Event Processor
Gestisce tutte le configurazioni tramite environment variables
"""

import os
from dataclasses import dataclass
from typing import List

@dataclass
class Config:
    """Configuration class with environment variable defaults"""
    
    # MQTT Configuration
    mqtt_broker: str = os.getenv('MQTT_BROKER', 'localhost')
    mqtt_port: int = int(os.getenv('MQTT_PORT', '1883'))
    mqtt_username: str = os.getenv('MQTT_USERNAME', '')
    mqtt_password: str = os.getenv('MQTT_PASSWORD', '')
    mqtt_keepalive: int = int(os.getenv('MQTT_KEEPALIVE', '60'))
    
    # MQTT Topics to subscribe
    mqtt_topics: List[str] = None
    
    # InfluxDB Configuration
    influxdb_url: str = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
    influxdb_token: str = os.getenv('INFLUXDB_TOKEN', 'factory-token-2024')
    influxdb_org: str = os.getenv('INFLUXDB_ORG', 'factory')
    influxdb_bucket: str = os.getenv('INFLUXDB_BUCKET', 'industrial_data')
    
    # Processing Configuration
    batch_size: int = int(os.getenv('PROCESSING_BATCH_SIZE', '10'))
    flush_interval: int = int(os.getenv('FLUSH_INTERVAL', '5'))  # seconds
    
    # Anomaly Detection Configuration
    anomaly_detection_enabled: bool = os.getenv('ANOMALY_DETECTION_ENABLED', 'true').lower() == 'true'
    temp_warning_threshold: float = float(os.getenv('TEMP_WARNING_THRESHOLD', '80.0'))
    temp_critical_threshold: float = float(os.getenv('TEMP_CRITICAL_THRESHOLD', '90.0'))
    vibration_warning_threshold: float = float(os.getenv('VIBRATION_WARNING_THRESHOLD', '2.5'))
    vibration_critical_threshold: float = float(os.getenv('VIBRATION_CRITICAL_THRESHOLD', '3.0'))
    power_warning_threshold: float = float(os.getenv('POWER_WARNING_THRESHOLD', '5.0'))
    
    # Logging Configuration
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', '/app/logs/processor.log')
    
    # Health Check Configuration
    health_check_port: int = int(os.getenv('HEALTH_CHECK_PORT', '8080'))
    health_check_enabled: bool = os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
    
    def __post_init__(self):
        """Post-initialization setup"""
        if self.mqtt_topics is None:
            self.mqtt_topics = [
                '/plant/data/+',      # All sensor data
                '/plant/tracking/+',  # All tracking events
                '/plant/alerts/+',    # All alerts (future)
            ]
    
    def get_mqtt_topics(self) -> List[str]:
        """Get list of MQTT topics to subscribe to"""
        return self.mqtt_topics
    
    def get_influxdb_config(self) -> dict:
        """Get InfluxDB connection configuration"""
        return {
            'url': self.influxdb_url,
            'token': self.influxdb_token,
            'org': self.influxdb_org,
            'bucket': self.influxdb_bucket
        }
    
    def get_mqtt_config(self) -> dict:
        """Get MQTT connection configuration"""
        config = {
            'broker': self.mqtt_broker,
            'port': self.mqtt_port,
            'keepalive': self.mqtt_keepalive,
        }
        
        # Add credentials if provided
        if self.mqtt_username:
            config['username'] = self.mqtt_username
        if self.mqtt_password:
            config['password'] = self.mqtt_password
            
        return config
    
    def get_anomaly_thresholds(self) -> dict:
        """Get anomaly detection thresholds"""
        return {
            'temperature': {
                'warning': self.temp_warning_threshold,
                'critical': self.temp_critical_threshold
            },
            'vibration': {
                'warning': self.vibration_warning_threshold,
                'critical': self.vibration_critical_threshold
            },
            'power': {
                'warning': self.power_warning_threshold,
                'critical': self.power_warning_threshold * 1.5  # 150% of warning
            }
        }
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return os.getenv('ENVIRONMENT', 'production').lower() in ['dev', 'development']
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        # Check required InfluxDB settings
        if not self.influxdb_url:
            errors.append("INFLUXDB_URL is required")
        if not self.influxdb_token:
            errors.append("INFLUXDB_TOKEN is required")
        if not self.influxdb_org:
            errors.append("INFLUXDB_ORG is required")
        if not self.influxdb_bucket:
            errors.append("INFLUXDB_BUCKET is required")
        
        # Check MQTT settings
        if not self.mqtt_broker:
            errors.append("MQTT_BROKER is required")
        if not (1 <= self.mqtt_port <= 65535):
            errors.append("MQTT_PORT must be between 1 and 65535")
        
        # Check thresholds are positive
        if self.temp_warning_threshold <= 0:
            errors.append("TEMP_WARNING_THRESHOLD must be positive")
        if self.temp_critical_threshold <= self.temp_warning_threshold:
            errors.append("TEMP_CRITICAL_THRESHOLD must be higher than warning")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    def __str__(self) -> str:
        """String representation (safe for logging)"""
        return f"""Event Processor Configuration:
MQTT: {self.mqtt_broker}:{self.mqtt_port}
InfluxDB: {self.influxdb_url} (org: {self.influxdb_org}, bucket: {self.influxdb_bucket})
Batch Size: {self.batch_size}
Anomaly Detection: {'Enabled' if self.anomaly_detection_enabled else 'Disabled'}
Log Level: {self.log_level}
Topics: {', '.join(self.mqtt_topics)}"""