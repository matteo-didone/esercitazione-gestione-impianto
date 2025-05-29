# 🗄️ Database Configuration - IoT Industrial Project

## 📁 Struttura Directory

```
database/
├── setup_database.py      # Script setup automatico InfluxDB
├── schema.json            # Definizione schema completo
├── sample_queries.flux    # Query di esempio per Grafana/InfluxDB
├── validate_data.py       # Script validazione integrità dati
├── requirements.txt       # Dipendenze Python
└── README.md             # Questa documentazione
```

## 🚀 Quick Start

### 1. Prerequisiti
```bash
# Assicurati che InfluxDB sia in esecuzione
docker-compose up -d influxdb

# Installa dipendenze Python
pip install -r database/requirements.txt
```

### 2. Setup Database
```bash
# Esegui script setup automatico
python database/setup_database.py

# Output atteso:
# ✅ InfluxDB è pronto!
# ✅ Creato bucket: industrial_data (retention: 7 giorni)
# ✅ Test data written successfully
# 🎉 SETUP INFLUXDB COMPLETATO!
```

### 3. Validazione
```bash
# Verifica integrità database
python database/validate_data.py

# Output atteso:
# ✅ Database connection OK
# ✅ sensor_data: 150 records
# ✅ Performance: Excellent
```

## 📊 Schema Database

### Bucket Principale: `industrial_data`
- **Retention**: 7 giorni
- **Purpose**: Dati operativi in tempo reale

#### Measurements:

1. **sensor_data** - Dati sensori continui (ogni 3 sec)
   - Tags: `machine`, `machine_type`, `location`
   - Fields: `temperature`, `power`, `rpm_spindle`, `vibration_level`

2. **machine_events** - Eventi macchina discreti
   - Tags: `machine`, `event_type`, `piece_id`, `tool`
   - Fields: `duration`, `status`, `tool_wear`, `cycle_time`

3. **piece_tracking** - Tracciamento pezzi
   - Tags: `piece_id`, `event_type`, `from_station`, `to_station`
   - Fields: `duration`, `distance`, `material`

4. **system_metrics** - Metriche sistema (ogni 30 sec)
   - Tags: `component`, `metric_type`, `severity`
   - Fields: `messages_processed`, `processing_time`, `memory_usage`

## 🔍 Query di Esempio

### Monitoraggio Real-time
```flux
from(bucket:"industrial_data")
|> range(start: -1h)
|> filter(fn: (r) => r._measurement == "sensor_data")
|> filter(fn: (r) => r._field == "temperature")
|> filter(fn: (r) => r.machine == "Milling1")
```

### Efficienza Macchine
```flux
from(bucket:"industrial_data")
|> range(start: -24h)
|> filter(fn: (r) => r._measurement == "machine_events")
|> filter(fn: (r) => r.event_type == "processing_end")
|> group(columns: ["machine"])
|> mean(column: "cycle_time")
```

### Rilevamento Anomalie
```flux
from(bucket:"industrial_data")
|> range(start: -1h)
|> filter(fn: (r) => r._measurement == "sensor_data")
|> filter(fn: (r) => r._field == "temperature")
|> filter(fn: (r) => r._value > 80.0)
```

## 🔧 Configurazione

### Environment Variables
```bash
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=factory-token-2024
INFLUXDB_ORG=factory
INFLUXDB_BUCKET=industrial_data
```

### Accesso Web UI
- **URL**: http://localhost:8086
- **Username**: admin
- **Password**: admin123
- **Organization**: factory

## 📈 Performance Ottimizzazioni

### Tags vs Fields
- **Tags**: Usare per filtri e raggruppamenti (indicizzati)
- **Fields**: Usare per valori numerici (non indicizzati)

### Query Ottimizzazioni
```flux
# ✅ Efficiente - specifica range temporale
from(bucket:"industrial_data")
|> range(start: -1h)  # Sempre specificare range!

# ❌ Inefficiente - nessun filtro temporale
from(bucket:"industrial_data")
|> filter(fn: (r) => r.machine == "Milling1")
```

### Retention Policies
- **industrial_data**: 7 giorni (dati operativi)
- **historical_data**: 1 anno (aggregati)
- **alerts**: 30 giorni (allarmi)

## 🚨 Troubleshooting

### Problemi Comuni

#### 1. Connessione Database
```bash
# Verifica stato container
docker ps | grep influxdb

# Check logs
docker logs influxdb

# Test connessione
curl http://localhost:8086/health
```

#### 2. Token Authentication
```bash
# Lista token esistenti (InfluxDB UI)
# Settings > API Tokens

# O via CLI
docker exec influxdb influx auth list
```

#### 3. Performance Lente
```bash
# Verifica uso risorse
docker stats influxdb

# Analizza query lente nel UI InfluxDB
# Data Explorer > Query Inspector
```

#### 4. Spazio Disco
```bash
# Verifica retention policies
docker exec influxdb influx bucket list

# Forza compattazione
docker exec influxdb influx database retention-policy show
```

### Script di Debug
```bash
# Test completo database
python database/validate_data.py

# Reinizializza database (ATTENZIONE: cancella dati)
python database/setup_database.py --reset
```

## 📝 Note per il Team

### Persona 1 (Database): Task
1. ✅ Eseguire `setup_database.py`
2. ✅ Verificare con `validate_data.py`
3. ✅ Testare query in InfluxDB UI
4. ✅ Documentare eventuali modifiche schema

### Integrazione con Event Processor
```python
# Esempio connessione da event processor
from influxdb_client import InfluxDBClient

client = InfluxDBClient(
    url=os.getenv("INFLUXDB_URL"),
    token=os.getenv("INFLUXDB_TOKEN"),
    org=os.getenv("INFLUXDB_ORG")
)
```

### Integrazione con Grafana
1. Aggiungi datasource InfluxDB
2. URL: `http://influxdb:8086`
3. Token: `factory-token-2024`
4. Organization: `factory`
5. Default bucket: `industrial_data`

## 🎯 Success Criteria

Database setup è completo quando:
- ✅ Tutti i bucket sono creati
- ✅ Schema è validato
- ✅ Query di test funzionano
- ✅ Performance < 500ms per query base
- ✅ Event processor può scrivere dati
- ✅ Grafana può leggere dati

---

**📞 Supporto**: Se hai problemi, controlla prima i logs con `docker logs influxdb` e poi esegui `validate_data.py` per diagnostica automatica.