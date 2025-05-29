#!/usr/bin/env python3
"""
Event Processor - IoT Industrial Project
Collega MQTT broker con InfluxDB per gestione dati industriali
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from src.config import Config
from src.mqtt_client import MQTTClient
from src.influx_writer import InfluxWriter
from src.data_processor import DataProcessor
from src.system_tracker import SystemTracker

# Setup logging
import os
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'processor.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class EventProcessor:
    """Main Event Processor Class"""
    
    def __init__(self):
        self.config = Config()
        logger.info("🚀 Initializing Event Processor...")
        
        # Initialize components
        self.influx_writer = InfluxWriter(self.config)
        self.data_processor = DataProcessor()
        self.mqtt_client = MQTTClient(self.config)
        self.system_tracker = SystemTracker()  # Add system tracker
        
        # State
        self.running = False
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    async def process_message(self, topic: str, payload: dict):
        """Process incoming MQTT message"""
        try:
            self.stats['messages_received'] += 1
            
            # Log raw message
            logger.debug(f"📨 Received message on {topic}: {payload}")
            
            # Process data based on topic
            if "/plant/data/" in topic:
                # Sensor data
                processed_data = self.data_processor.process_sensor_data(payload)
                await self.influx_writer.write_sensor_data(processed_data)
                
            elif "/plant/tracking/" in topic:
                # Event tracking data
                if payload.get('entity') == 'piece':
                    # Piece tracking
                    processed_data = self.data_processor.process_piece_tracking(payload)
                    await self.influx_writer.write_piece_tracking(processed_data)
                else:
                    # Machine events
                    processed_data = self.data_processor.process_machine_event(payload)
                    await self.influx_writer.write_machine_event(processed_data)
            
            else:
                logger.warning(f"⚠️  Unknown topic pattern: {topic}")
                return
            
            self.stats['messages_processed'] += 1
            
            # Log processing stats every 100 messages
            if self.stats['messages_processed'] % 100 == 0:
                await self.log_stats()
                
        except Exception as e:
            self.stats['errors'] += 1
            self.system_tracker.increment_error()  # Track errors in system
            logger.error(f"❌ Error processing message from {topic}: {e}")
            logger.exception(e)
    
    async def log_stats(self):
        """Log processing statistics"""
        uptime = datetime.now() - self.stats['start_time']
        rate = self.stats['messages_processed'] / max(uptime.total_seconds(), 1)
        
        logger.info(f"📊 Stats: {self.stats['messages_processed']} processed, "
                   f"{self.stats['errors']} errors, {rate:.1f} msg/sec")
        
        # Get system tracking data according to schema
        system_data = self.system_tracker.get_system_metrics()
        system_data.update({
            'messages_processed': self.stats['messages_processed'],
            'messages_received': self.stats['messages_received'],
            'processing_rate': rate,
        })
        
        # Write system tracking data (CPU, Free Memory, RAM, Errors)
        await self.influx_writer.write_system_tracking(system_data)
    
    async def start(self):
        """Start the event processor"""
        logger.info("🚀 Starting Event Processor...")
        self.running = True
        
        try:
            # Connect to InfluxDB
            await self.influx_writer.connect()
            logger.info("✅ Connected to InfluxDB")
            
            # Start MQTT client with message callback
            await self.mqtt_client.start(self.process_message)
            logger.info("✅ Connected to MQTT broker")
            
            # Main processing loop
            while self.running:
                await asyncio.sleep(1)
                
                # Periodic stats logging (every 5 minutes)
                if self.stats['messages_processed'] > 0 and \
                   (datetime.now() - self.stats['start_time']).total_seconds() % 300 < 1:
                    await self.log_stats()
        
        except Exception as e:
            logger.error(f"❌ Fatal error in event processor: {e}")
            logger.exception(e)
            raise
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🛑 Shutting down Event Processor...")
        self.running = False
        
        try:
            if hasattr(self, 'mqtt_client'):
                await self.mqtt_client.stop()
                logger.info("✅ MQTT client disconnected")
            
            if hasattr(self, 'influx_writer'):
                await self.influx_writer.close()
                logger.info("✅ InfluxDB connection closed")
                
        except Exception as e:
            logger.error(f"⚠️  Error during cleanup: {e}")
    
    async def stop(self):
        """Stop the event processor gracefully"""
        logger.info("🛑 Stop signal received")
        self.running = False

# Global processor instance for signal handling
processor = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"🛑 Received signal {signum}")
    if processor:
        asyncio.create_task(processor.stop())

async def main():
    """Main entry point"""
    global processor
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start processor
    processor = EventProcessor()
    
    try:
        logger.info("🏭 IoT Industrial Event Processor Starting...")
        await processor.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {e}")
        logger.exception(e)
        sys.exit(1)
    finally:
        if processor:
            await processor.cleanup()
        logger.info("👋 Event Processor stopped")

if __name__ == "__main__":
    asyncio.run(main())