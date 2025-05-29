"""
InfluxDB Writer Module
Gestisce la scrittura dei dati su InfluxDB in modo asincrono
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import ASYNCHRONOUS

logger = logging.getLogger(__name__)

class InfluxWriter:
    """Async InfluxDB writer with batching and retry logic"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.write_api = None
        self.connected = False
        self.write_buffer = []
        self.stats = {
            'points_written': 0,
            'write_errors': 0,
            'last_write_time': None,
            'buffer_size': 0
        }
        
    async def connect(self):
        """Connect to InfluxDB"""
        try:
            influx_config = self.config.get_influxdb_config()
            
            logger.info(f"🔌 Connecting to InfluxDB at {influx_config['url']}...")
            
            self.client = InfluxDBClient(
                url=influx_config['url'],
                token=influx_config['token'],
                org=influx_config['org'],
                timeout=30000  # 30 seconds timeout
            )
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                logger.info("✅ InfluxDB connection healthy")
                self.connected = True
                
                # Create write API
                self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
                
                # Start background flush task
                asyncio.create_task(self._flush_loop())
                
            else:
                raise ConnectionError(f"InfluxDB health check failed: {health.message}")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to InfluxDB: {e}")
            self.connected = False
            raise
    
    async def write_sensor_data(self, data: Dict[str, Any]):
        """Write sensor data point to InfluxDB"""
        try:
            point = Point(data['measurement'])
            
            # Add tags
            for tag_key, tag_value in data['tags'].items():
                point = point.tag(tag_key, str(tag_value))
            
            # Add fields
            for field_key, field_value in data['fields'].items():
                point = point.field(field_key, field_value)
            
            # Set timestamp
            point = point.time(data['time'])
            
            # Add to buffer
            await self._buffer_point(point)
            
            # Write anomaly alerts if present
            if data.get('anomalies'):
                await self._write_anomaly_alerts(data['tags']['machine'], data['anomalies'], data['time'])
            
            logger.debug(f"📊 Buffered sensor data for {data['tags']['machine']}")
            
        except Exception as e:
            logger.error(f"❌ Error writing sensor data: {e}")
            self.stats['write_errors'] += 1
            raise
    
    async def write_machine_event(self, data: Dict[str, Any]):
        """Write machine event to InfluxDB"""
        try:
            point = Point(data['measurement'])
            
            # Add tags
            for tag_key, tag_value in data['tags'].items():
                point = point.tag(tag_key, str(tag_value))
            
            # Add fields
            for field_key, field_value in data['fields'].items():
                point = point.field(field_key, field_value)
            
            # Set timestamp
            point = point.time(data['time'])
            
            # Add to buffer
            await self._buffer_point(point)
            
            logger.debug(f"⚙️  Buffered machine event: {data['tags']['event_type']} for {data['tags']['machine']}")
            
        except Exception as e:
            logger.error(f"❌ Error writing machine event: {e}")
            self.stats['write_errors'] += 1
            raise
    
    async def write_piece_tracking(self, data: Dict[str, Any]):
        """Write piece tracking event to InfluxDB"""
        try:
            point = Point(data['measurement'])
            
            # Add tags
            for tag_key, tag_value in data['tags'].items():
                point = point.tag(tag_key, str(tag_value))
            
            # Add fields
            for field_key, field_value in data['fields'].items():
                point = point.field(field_key, field_value)
            
            # Set timestamp
            point = point.time(data['time'])
            
            # Add to buffer
            await self._buffer_point(point)
            
            logger.debug(f"🚛 Buffered piece tracking: {data['tags']['event_type']} for {data['tags']['piece_id']}")
            
        except Exception as e:
            logger.error(f"❌ Error writing piece tracking: {e}")
            self.stats['write_errors'] += 1
            raise
    
    async def write_system_tracking(self, metrics: Dict[str, Any]):
        """Write system tracking data according to schema: CPU, Free Memory, RAM, Errors"""
        try:
            point = Point("system_tracking")  # Changed from system_metrics
            point = point.tag("component", "event_processor")
            point = point.tag("metric_type", "system_resources")
            point = point.tag("severity", "info")
            
            # Schema-compliant fields
            point = point.field("cpu", metrics.get("cpu", 0.0))
            point = point.field("free_memory", metrics.get("free_memory", 0.0))  # GB
            point = point.field("ram", metrics.get("ram", 0.0))  # GB
            point = point.field("errors", metrics.get("errors", 0))
            
            # Additional useful fields
            point = point.field("memory_used_percent", metrics.get("memory_used_percent", 0.0))
            point = point.field("uptime_seconds", metrics.get("uptime_seconds", 0.0))
            
            point = point.time(datetime.utcnow())
            
            # Add to buffer
            await self._buffer_point(point)
            
            logger.debug("💻 Buffered system tracking data")
            
        except Exception as e:
            logger.error(f"❌ Error writing system tracking: {e}")
            self.stats['write_errors'] += 1

    # Keep the old method for backward compatibility
    async def write_system_metrics(self, metrics: Dict[str, Any]):
        """Legacy method - redirects to write_system_tracking"""
        await self.write_system_tracking(metrics)
    
    async def _write_anomaly_alerts(self, machine: str, anomalies: List[str], timestamp: datetime):
        """Write anomaly alerts to alerts bucket"""
        for anomaly in anomalies:
            try:
                point = Point("temperature_alerts" if "temperature" in anomaly.lower() 
                            else "vibration_alerts" if "vibration" in anomaly.lower()
                            else "system_alerts")
                
                point = point.tag("machine", machine)
                point = point.tag("severity", "critical" if "Critical" in anomaly else "warning")
                point = point.tag("alert_type", "anomaly")
                
                point = point.field("message", anomaly)
                point = point.field("resolved", False)
                
                point = point.time(timestamp)
                
                # Write immediately to alerts bucket (don't buffer)
                if self.connected and self.write_api:
                    self.write_api.write(
                        bucket="alerts",
                        org=self.config.influxdb_org,
                        record=point
                    )
                    logger.warning(f"🚨 Alert written: {anomaly}")
                
            except Exception as e:
                logger.error(f"❌ Error writing anomaly alert: {e}")
    
    async def _buffer_point(self, point: Point):
        """Add point to write buffer"""
        self.write_buffer.append((point, datetime.utcnow()))
        self.stats['buffer_size'] = len(self.write_buffer)
        
        # Flush if buffer is full
        if len(self.write_buffer) >= self.config.batch_size:
            await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Flush write buffer to InfluxDB"""
        if not self.write_buffer or not self.connected:
            return
        
        try:
            # Get points to write (copy buffer and clear it)
            points_to_write = [point for point, _ in self.write_buffer]
            buffer_size = len(points_to_write)
            self.write_buffer.clear()
            self.stats['buffer_size'] = 0
            
            # Write to InfluxDB
            if self.write_api:
                self.write_api.write(
                    bucket=self.config.influxdb_bucket,
                    org=self.config.influxdb_org,
                    record=points_to_write
                )
                
                self.stats['points_written'] += buffer_size
                self.stats['last_write_time'] = datetime.utcnow()
                
                logger.info(f"✅ Flushed {buffer_size} points to InfluxDB")
            
        except Exception as e:
            logger.error(f"❌ Error flushing buffer to InfluxDB: {e}")
            self.stats['write_errors'] += 1
            
            # Put points back in buffer for retry (only recent ones)
            recent_threshold = datetime.utcnow().timestamp() - 300  # 5 minutes
            for point, timestamp in [(p, t) for p, t in self.write_buffer if t.timestamp() > recent_threshold]:
                self.write_buffer.append((point, timestamp))
    
    async def _flush_loop(self):
        """Background task to periodically flush buffer"""
        while self.connected:
            try:
                await asyncio.sleep(self.config.flush_interval)
                if self.write_buffer:
                    await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in flush loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def close(self):
        """Close InfluxDB connection"""
        if self.write_buffer:
            logger.info("📤 Flushing remaining buffer before closing...")
            await self._flush_buffer()
        
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("✅ InfluxDB connection closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get writer statistics"""
        return {
            'connected': self.connected,
            'points_written': self.stats['points_written'],
            'write_errors': self.stats['write_errors'],
            'buffer_size': self.stats['buffer_size'],
            'last_write_time': self.stats['last_write_time'].isoformat() if self.stats['last_write_time'] else None
        }