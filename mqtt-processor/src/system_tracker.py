"""
System Tracking Module
Monitora CPU, RAM, Memory e Errors secondo lo schema richiesto
"""

import psutil
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SystemTracker:
    """Tracks system resources according to schema requirements"""
    
    def __init__(self):
        self.error_count = 0
        self.start_time = datetime.now()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system metrics matching the schema:
        - CPU
        - Free Memory  
        - RAM
        - Errors
        """
        try:
            # CPU Usage (percentage)
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory Information
            memory = psutil.virtual_memory()
            
            # RAM Total (GB)
            ram_total_gb = memory.total / (1024**3)
            
            # Free Memory (GB) 
            free_memory_gb = memory.available / (1024**3)
            
            # Memory Usage Percentage
            memory_used_percent = memory.percent
            
            return {
                'cpu': round(cpu_percent, 2),
                'free_memory': round(free_memory_gb, 2),  # GB
                'ram': round(ram_total_gb, 2),           # GB  
                'errors': self.error_count,
                'memory_used_percent': round(memory_used_percent, 2),
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting system metrics: {e}")
            self.increment_error()
            return {
                'cpu': 0.0,
                'free_memory': 0.0,
                'ram': 0.0, 
                'errors': self.error_count,
                'memory_used_percent': 0.0,
                'uptime_seconds': 0.0
            }
    
    def increment_error(self):
        """Increment error counter"""
        self.error_count += 1
        logger.warning(f"⚠️  System error count: {self.error_count}")
    
    def reset_errors(self):
        """Reset error counter"""
        self.error_count = 0
        logger.info("✅ Error count reset")
    
    def get_detailed_system_info(self) -> Dict[str, Any]:
        """Get additional system information for debugging"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                'disk_usage': psutil.disk_usage('/')._asdict(),
                'network_io': psutil.net_io_counters()._asdict(),
                'process_count': len(psutil.pids())
            }
        except Exception as e:
            logger.error(f"❌ Error getting detailed system info: {e}")
            return {}