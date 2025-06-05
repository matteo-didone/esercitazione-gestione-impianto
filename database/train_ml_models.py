#!/usr/bin/env python3
"""
ML Models Training Script - ROBUST VERSION
Versione robusta con fix per permission e data handling
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import pandas as pd
import numpy as np

# Add the src directory to Python path
sys.path.insert(0, '/app/src')

print("🔍 Checking ML modules availability...")

# Import ML modules
try:
    from ml_predictive_maintenance import PredictiveMaintenanceModel
    from ml_energy_optimizer import EnergyOptimizer
    print("✅ ML modules imported successfully")
except ImportError as e:
    print(f"❌ Error importing ML modules: {e}")
    sys.exit(1)

# Configuration
CONFIG = {
    "url": os.getenv("INFLUXDB_URL", "http://influxdb:8086"),
    "token": os.getenv("INFLUXDB_TOKEN", "factory-token-2024"),
    "org": os.getenv("INFLUXDB_ORG", "factory"),
    "bucket": os.getenv("INFLUXDB_BUCKET", "industrial_data")
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

class RobustMLTrainer:
    """Robust ML trainer with better error handling"""
    
    def __init__(self):
        logger.info(f"🔌 Connecting to InfluxDB at {CONFIG['url']}")
        self.client = InfluxDBClient(
            url=CONFIG["url"],
            token=CONFIG["token"], 
            org=CONFIG["org"]
        )
        self.query_api = self.client.query_api()
        
        # Initialize ML models with temporary directory if needed
        models_dir = '/tmp/ml_models'  # Use /tmp if /app/ml_models not writable
        os.makedirs(models_dir, exist_ok=True)
        
        logger.info("🤖 Initializing ML models...")
        self.predictive_model = PredictiveMaintenanceModel(models_dir=models_dir)
        self.energy_optimizer = EnergyOptimizer(models_dir=models_dir)
        
        # All machines from simulator
        self.machines = ['Saw1', 'Milling1', 'Milling2', 'Lathe1']
        
        logger.info("✅ ML Trainer initialized")
    
    async def collect_historical_data(self, machine: str, hours: int = 12) -> pd.DataFrame:
        """Collect historical sensor data for a machine"""
        try:
            query = f'''
            from(bucket:"{CONFIG["bucket"]}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "sensor_data")
            |> filter(fn: (r) => r.machine == "{machine}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"])
            '''
            
            logger.info(f"📊 Collecting {hours} hours of data for {machine}...")
            
            result = self.query_api.query_data_frame(query)
            
            # Handle different result formats
            if isinstance(result, list):
                if len(result) == 0:
                    logger.warning(f"⚠️  No data returned for {machine}")
                    return pd.DataFrame()
                result = pd.concat(result, ignore_index=True) if len(result) > 1 else result[0]
            
            if result.empty:
                logger.warning(f"⚠️  No historical data found for {machine}")
                return pd.DataFrame()
            
            # Clean result columns
            for col in ['result', 'table']:
                if col in result.columns:
                    result = result.drop(columns=[col])
            
            logger.info(f"✅ Collected {len(result)} data points for {machine}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error collecting data for {machine}: {e}")
            return pd.DataFrame()
    
    def prepare_training_windows(self, df: pd.DataFrame, machine: str, window_size: int = 15) -> list:
        """Convert DataFrame to training windows with robust data handling"""
        if df.empty:
            return []
        
        training_windows = []
        
        # Create sliding windows
        for i in range(0, len(df) - window_size, 5):  # Step by 5
            window = df.iloc[i:i + window_size]
            
            # Convert window to sensor data format with safe value extraction
            sensor_data = []
            for _, row in window.iterrows():
                data_point = {
                    'timestamp': row.get('_time', datetime.now()),
                    'temperature': self._safe_float(row.get('temperature'), 25.0),
                    'power': self._safe_float(row.get('power'), 1.0),
                    'rpm_spindle': self._safe_float(row.get('rpm_spindle'), None),
                    'feed_rate': self._safe_float(row.get('feed_rate'), None),
                    'vibration_level': self._safe_float(row.get('vibration_level'), None),
                    'cut_depth': self._safe_float(row.get('cut_depth'), None),
                    'blade_speed': self._safe_float(row.get('blade_speed'), None),
                    'material_feed': self._safe_float(row.get('material_feed'), None),
                    'tool_wear': 0.1  # Simple default
                }
                sensor_data.append(data_point)
            
            training_windows.append(sensor_data)
        
        logger.info(f"📦 Created {len(training_windows)} training windows for {machine}")
        return training_windows
    
    def _safe_float(self, value, default):
        """Safely convert value to float"""
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def classify_health_status(self, sensor_data: list) -> bool:
        """Robust health classification"""
        try:
            temps = [d['temperature'] for d in sensor_data if d['temperature'] is not None]
            powers = [d['power'] for d in sensor_data if d['power'] is not None]
            
            if not temps or not powers:
                return True  # Default to healthy if no valid data
            
            avg_temp = np.mean(temps)
            avg_power = np.mean(powers)
            max_temp = max(temps)
            
            # Healthy criteria
            return avg_temp < 70.0 and max_temp < 85.0 and avg_power < 5.0
            
        except Exception as e:
            logger.warning(f"Error in health classification: {e}")
            return True  # Default to healthy on error
    
    async def train_predictive_maintenance(self, machine: str) -> bool:
        """Train predictive maintenance with robust error handling"""
        logger.info(f"🔧 Training predictive model for {machine}")
        
        try:
            df = await self.collect_historical_data(machine, hours=12)
            if df.empty:
                return False
            
            windows = self.prepare_training_windows(df, machine, window_size=10)  # Smaller windows
            if len(windows) < 3:
                logger.warning(f"Insufficient windows for {machine}: {len(windows)}")
                return False
            
            # Add training data with health classification
            healthy_count = 0
            unhealthy_count = 0
            
            for window in windows:
                try:
                    is_healthy = self.classify_health_status(window)
                    self.predictive_model.add_training_data(machine, window, is_healthy)
                    
                    if is_healthy:
                        healthy_count += 1
                    else:
                        unhealthy_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error adding training window: {e}")
                    continue
            
            logger.info(f"📊 {machine}: {healthy_count} healthy, {unhealthy_count} unhealthy windows")
            
            if healthy_count + unhealthy_count < 3:
                logger.warning(f"Too few valid windows for {machine}")
                return False
            
            # Train model with lower requirements
            return self.predictive_model.train_model(machine)
            
        except Exception as e:
            logger.error(f"❌ Error training predictive model for {machine}: {e}")
            return False
    
    async def train_energy_optimization(self, machine: str) -> bool:
        """Train energy optimization with robust error handling"""
        logger.info(f"⚡ Training energy model for {machine}")
        
        try:
            df = await self.collect_historical_data(machine, hours=12)
            if df.empty:
                return False
            
            valid_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Extract data with safe conversion
                    power = self._safe_float(row.get('power'), None)
                    temp = self._safe_float(row.get('temperature'), None)
                    
                    if power is None or temp is None:
                        continue
                    
                    training_point = {
                        'timestamp': row.get('_time', datetime.now()),
                        'power': power,
                        'temperature': temp,
                        'rpm_spindle': self._safe_float(row.get('rpm_spindle'), 2500),
                        'feed_rate': self._safe_float(row.get('feed_rate'), 300),
                        'vibration_level': self._safe_float(row.get('vibration_level'), 1.0),
                        'cut_depth': self._safe_float(row.get('cut_depth'), 2.0),
                        'blade_speed': self._safe_float(row.get('blade_speed'), 1800),
                        'material_feed': self._safe_float(row.get('material_feed'), 1.0)
                    }
                    
                    # Only add if power is reasonable
                    if 0.1 <= power <= 10.0:
                        self.energy_optimizer.add_training_data(machine, training_point)
                        valid_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing energy data point: {e}")
                    continue
            
            logger.info(f"📊 Added {valid_count} energy samples for {machine}")
            
            if valid_count < 10:
                logger.warning(f"Insufficient energy data for {machine}")
                return False
            
            return self.energy_optimizer.train_power_model(machine)
            
        except Exception as e:
            logger.error(f"❌ Error training energy model for {machine}: {e}")
            return False
    
    async def train_all_robust(self) -> dict:
        """Train all models with robust error handling"""
        logger.info("🚀 Starting robust ML training...")
        
        results = {'predictive': {}, 'energy': {}}
        
        for machine in self.machines:
            logger.info(f"\n🏭 Training {machine}...")
            
            # Predictive maintenance
            try:
                pm_success = await self.train_predictive_maintenance(machine)
                results['predictive'][machine] = pm_success
                logger.info(f"{'✅' if pm_success else '⚠️ '} Predictive: {machine}")
            except Exception as e:
                logger.error(f"❌ Predictive error for {machine}: {e}")
                results['predictive'][machine] = False
            
            # Energy optimization
            try:
                eo_success = await self.train_energy_optimization(machine)
                results['energy'][machine] = eo_success
                logger.info(f"{'✅' if eo_success else '⚠️ '} Energy: {machine}")
            except Exception as e:
                logger.error(f"❌ Energy error for {machine}: {e}")
                results['energy'][machine] = False
        
        return results
    
    def close(self):
        """Close connection"""
        if self.client:
            self.client.close()

async def main():
    """Main training function"""
    print("🤖 Starting Robust ML Training...")
    
    trainer = RobustMLTrainer()
    
    try:
        # Check for data
        logger.info("🔍 Checking for data availability...")
        test_df = await trainer.collect_historical_data('Saw1', hours=6)
        
        if test_df.empty:
            logger.error("❌ No data found! Make sure simulator has been running.")
            logger.error("   Try: docker-compose up simulator")
            return
        
        logger.info(f"✅ Found {len(test_df)} data points - proceeding with training")
        
        # Train all models
        results = await trainer.train_all_robust()
        
        # Summary
        total_predictive = sum(results['predictive'].values())
        total_energy = sum(results['energy'].values())
        total_machines = len(trainer.machines)
        
        logger.info(f"\n🎉 Training Results:")
        logger.info(f"   Predictive: {total_predictive}/{total_machines} machines")
        logger.info(f"   Energy: {total_energy}/{total_machines} machines")
        logger.info(f"   Success Rate: {(total_predictive + total_energy)/(total_machines*2)*100:.1f}%")
        
        if total_predictive > 0 or total_energy > 0:
            logger.info("✅ ML models ready! Check dashboard at:")
            logger.info("   http://localhost:3000/d/ml-insights")
            
            # Show which models are trained
            logger.info("\n📋 Trained Models:")
            for machine, success in results['predictive'].items():
                if success:
                    logger.info(f"   🔧 {machine}: Predictive Maintenance")
            for machine, success in results['energy'].items():
                if success:
                    logger.info(f"   ⚡ {machine}: Energy Optimization")
        else:
            logger.warning("⚠️  No models trained successfully.")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        trainer.close()

if __name__ == "__main__":
    asyncio.run(main())