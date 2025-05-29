"""
MQTT Client for Event Processor
Gestisce connessione e ricezione messaggi MQTT con fix per async callbacks
"""

import asyncio
import json
import logging
from typing import Callable, Optional
import paho.mqtt.client as mqtt
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

class MQTTClient:
    """Async MQTT Client wrapper with proper async callback handling"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.message_callback = None
        self.connected = False
        self.event_loop = None  # Store reference to event loop
        self.stats = {
            'messages_received': 0,
            'connection_errors': 0,
            'last_message_time': None
        }
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback quando si connette al broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"✅ Connected to MQTT broker {self.config.mqtt_broker}:{self.config.mqtt_port}")
            
            # Subscribe to all configured topics
            for topic in self.config.get_mqtt_topics():
                client.subscribe(topic)
                logger.info(f"📡 Subscribed to topic: {topic}")
                
        else:
            self.connected = False
            self.stats['connection_errors'] += 1
            logger.error(f"❌ Failed to connect to MQTT broker, code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback quando si disconnette dal broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"⚠️  Unexpected MQTT disconnection, code: {rc}")
        else:
            logger.info("🔌 MQTT client disconnected")
    
    def _on_message(self, client, userdata, msg):
        """Callback per messaggi ricevuti - FIXED for async"""
        try:
            # Decode message
            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')
            
            # Parse JSON
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in message from {topic}: {e}")
                return
            
            # Update stats
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            # Log message (debug level)
            logger.debug(f"📨 Message from {topic}: {payload}")
            
            # Call the registered callback safely
            if self.message_callback and self.event_loop:
                # Schedule callback in the correct event loop
                try:
                    # Use call_soon_threadsafe to schedule in the main event loop
                    future = asyncio.run_coroutine_threadsafe(
                        self.message_callback(topic, payload), 
                        self.event_loop
                    )
                    # Don't wait for the result to avoid blocking
                except Exception as e:
                    logger.error(f"❌ Error scheduling async callback: {e}")
            elif not self.message_callback:
                logger.warning("⚠️  No message callback registered")
                
        except Exception as e:
            logger.error(f"❌ Error processing MQTT message: {e}")
            logger.exception(e)
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback per conferma sottoscrizione"""
        logger.debug(f"📡 Subscription confirmed, QoS: {granted_qos}")
    
    def _on_log(self, client, userdata, level, buf):
        """Callback per log MQTT (solo per debug)"""
        if self.config.log_level == 'DEBUG':
            logger.debug(f"MQTT: {buf}")
    
    async def start(self, message_callback: Callable[[str, dict], None]):
        """Start MQTT client"""
        self.message_callback = message_callback
        
        # Store reference to current event loop
        try:
            self.event_loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.error("❌ No running event loop found")
            raise
        
        # Create MQTT client
        self.client = mqtt.Client()
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        
        # Enable logging for debug
        if self.config.log_level == 'DEBUG':
            self.client.on_log = self._on_log
        
        # Set credentials if provided
        mqtt_config = self.config.get_mqtt_config()
        if 'username' in mqtt_config and 'password' in mqtt_config:
            self.client.username_pw_set(
                mqtt_config['username'], 
                mqtt_config['password']
            )
        
        try:
            # Connect to broker
            logger.info(f"🔌 Connecting to MQTT broker {self.config.mqtt_broker}:{self.config.mqtt_port}...")
            
            self.client.connect(
                self.config.mqtt_broker,
                self.config.mqtt_port,
                self.config.mqtt_keepalive
            )
            
            # Start network loop
            self.client.loop_start()
            
            # Wait for connection
            retry_count = 0
            while not self.connected and retry_count < 10:
                await asyncio.sleep(1)
                retry_count += 1
            
            if not self.connected:
                raise ConnectionError("Failed to connect to MQTT broker after 10 retries")
            
            logger.info("✅ MQTT client started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start MQTT client: {e}")
            raise
    
    async def stop(self):
        """Stop MQTT client"""
        if self.client:
            logger.info("🛑 Stopping MQTT client...")
            
            # Unsubscribe from all topics
            for topic in self.config.get_mqtt_topics():
                self.client.unsubscribe(topic)
            
            # Disconnect and stop loop
            self.client.disconnect()
            self.client.loop_stop()
            
            self.connected = False
            self.event_loop = None
            logger.info("✅ MQTT client stopped")
    
    def get_stats(self) -> dict:
        """Get client statistics"""
        return {
            'connected': self.connected,
            'messages_received': self.stats['messages_received'],
            'connection_errors': self.stats['connection_errors'],
            'last_message_time': self.stats['last_message_time'].isoformat() if self.stats['last_message_time'] else None
        }
    
    async def publish_test_message(self, topic: str = "test/processor"):
        """Publish a test message (for debugging)"""
        if not self.connected:
            logger.error("❌ Cannot publish: MQTT client not connected")
            return False
        
        test_payload = {
            'timestamp': datetime.now().isoformat(),
            'message': 'Test from Event Processor',
            'stats': self.get_stats()
        }
        
        try:
            result = self.client.publish(topic, json.dumps(test_payload))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Test message published to {topic}")
                return True
            else:
                logger.error(f"❌ Failed to publish test message, code: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"❌ Error publishing test message: {e}")
            return False