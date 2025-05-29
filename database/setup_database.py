#!/usr/bin/env python3
"""
InfluxDB Setup Script for IoT Industrial Project
Configura automaticamente bucket, retention policies e struttura database
"""

import os
import sys
import time
from influxdb_client import InfluxDBClient, BucketRetentionRules
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import json

# Configurazione
CONFIG = {
    "url": "http://localhost:8086",
    "token": "factory-token-2024",  # Token dal docker-compose
    "org": "factory",
    "timeout": 30000  # 30 secondi
}

# Definizione bucket con retention
BUCKETS_CONFIG = [
    {
        "name": "industrial_data",
        "description": "Dati principali: sensori, eventi, tracking",
        "retention_days": 7,
    },
    {
        "name": "historical_data", 
        "description": "Dati aggregati storici",
        "retention_days": 365,
    },
    {
        "name": "alerts",
        "description": "Allarmi e anomalie sistema",
        "retention_days": 30,
    },
    {
        "name": "system_metrics",
        "description": "Metriche performance sistema",
        "retention_days": 14,
    }
]

def wait_for_influxdb(max_retries=10):
    """Aspetta che InfluxDB sia pronto"""
    print("🔄 Attendendo InfluxDB...")
    
    for attempt in range(max_retries):
        try:
            client = InfluxDBClient(
                url=CONFIG["url"], 
                token=CONFIG["token"], 
                org=CONFIG["org"],
                timeout=CONFIG["timeout"]
            )
            # Test connessione
            client.ping()
            client.close()
            print("✅ InfluxDB è pronto!")
            return True
        except Exception as e:
            print(f"⏳ Tentativo {attempt + 1}/{max_retries} - InfluxDB non ancora pronto: {e}")
            time.sleep(5)
    
    print("❌ Impossibile connettersi a InfluxDB dopo 10 tentativi")
    return False

def create_buckets():
    """Crea tutti i bucket necessari"""
    client = InfluxDBClient(
        url=CONFIG["url"], 
        token=CONFIG["token"], 
        org=CONFIG["org"],
        timeout=CONFIG["timeout"]
    )
    
    try:
        buckets_api = client.buckets_api()
        
        for bucket_config in BUCKETS_CONFIG:
            bucket_name = bucket_config["name"]
            
            # Controlla se bucket esiste già
            try:
                existing_bucket = buckets_api.find_bucket_by_name(bucket_name)
                if existing_bucket:
                    print(f"✅ Bucket '{bucket_name}' già esistente")
                    continue
            except:
                pass  # Bucket non esiste, lo creiamo
            
            # Crea retention policy
            retention_seconds = bucket_config["retention_days"] * 24 * 60 * 60
            retention_rules = BucketRetentionRules(
                type="expire",
                every_seconds=retention_seconds
            )
            
            # Crea bucket
            bucket = buckets_api.create_bucket(
                bucket_name=bucket_name,
                description=bucket_config["description"],
                org=CONFIG["org"],
                retention_rules=retention_rules
            )
            
            print(f"✅ Creato bucket: {bucket_name} (retention: {bucket_config['retention_days']} giorni)")
            
    except Exception as e:
        print(f"❌ Errore creazione bucket: {e}")
        return False
    finally:
        client.close()
    
    return True

def create_sample_data():
    """Inserisce dati di esempio per test"""
    client = InfluxDBClient(
        url=CONFIG["url"], 
        token=CONFIG["token"], 
        org=CONFIG["org"],
        timeout=CONFIG["timeout"]
    )
    
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        # Dati di esempio
        sample_points = [
            # Sensor data
            {
                "measurement": "sensor_data",
                "tags": {
                    "machine": "Milling1",
                    "machine_type": "Milling", 
                    "location": "workshop_A"
                },
                "fields": {
                    "temperature": 45.2,
                    "power": 2.3,
                    "rpm_spindle": 2800.0,
                    "vibration_level": 1.8
                },
                "time": datetime.utcnow()
            },
            # Machine event
            {
                "measurement": "machine_events",
                "tags": {
                    "machine": "Milling1",
                    "event_type": "processing_start",
                    "piece_id": "PZ001",
                    "tool": "TM10"
                },
                "fields": {
                    "duration": 0.0,
                    "status": "active"
                },
                "time": datetime.utcnow()
            },
            # Piece tracking
            {
                "measurement": "piece_tracking",
                "tags": {
                    "piece_id": "PZ001",
                    "event_type": "move_start",
                    "from_station": "Saw1",
                    "to_station": "Milling1",
                    "material": "steel"
                },
                "fields": {
                    "duration": 2.5,
                    "distance": 50.0
                },
                "time": datetime.utcnow()
            }
        ]
        
        # Scrivi dati di esempio
        write_api.write(
            bucket="industrial_data",
            org=CONFIG["org"],
            record=sample_points
        )
        
        print("✅ Dati di esempio inseriti con successo")
        
        # Verifica lettura dati
        query_api = client.query_api()
        test_query = '''
        from(bucket:"industrial_data")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "sensor_data")
        |> limit(n: 1)
        '''
        
        result = query_api.query(org=CONFIG["org"], query=test_query)
        if result:
            print("✅ Test lettura dati completato con successo")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore inserimento dati di esempio: {e}")
        return False
    finally:
        client.close()

def print_connection_info():
    """Stampa informazioni di connessione"""
    print("\n" + "="*60)
    print("🎉 SETUP INFLUXDB COMPLETATO!")
    print("="*60)
    print(f"🌐 URL InfluxDB:     {CONFIG['url']}")
    print(f"🔑 Token:           {CONFIG['token']}")
    print(f"🏢 Organization:    {CONFIG['org']}")
    print(f"📦 Bucket principale: industrial_data")
    print("\n📊 Accesso Web UI:")
    print(f"   - Vai su: {CONFIG['url']}")
    print("   - Username: admin")
    print("   - Password: admin123")
    print("\n🔧 Per Event Processor:")
    print("   Usa le variabili d'ambiente nel docker-compose")
    print("="*60)

def main():
    """Funzione principale setup"""
    print("🚀 Avvio setup InfluxDB per progetto IoT Industrial")
    
    # 1. Aspetta che InfluxDB sia pronto
    if not wait_for_influxdb():
        sys.exit(1)
    
    # 2. Crea bucket
    print("\n📦 Creazione bucket...")
    if not create_buckets():
        print("❌ Errore nella creazione dei bucket")
        sys.exit(1)
    
    # 3. Inserisci dati di esempio
    print("\n📊 Inserimento dati di esempio...")
    if not create_sample_data():
        print("⚠️  Warning: Errore nei dati di esempio (non critico)")
    
    # 4. Stampa info finali
    print_connection_info()

if __name__ == "__main__":
    main()