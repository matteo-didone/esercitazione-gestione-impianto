// ==============================================
// SAMPLE FLUX QUERIES FOR IOT INDUSTRIAL PROJECT
// ==============================================
// Queste query possono essere copiate direttamente in Grafana o InfluxDB UI

// ----------------------------------------------
// 1. REAL-TIME SENSOR MONITORING
// ----------------------------------------------

// Temperature monitoring - ultima ora
from(bucket:"industrial_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "temperature")
  |> filter(fn: (r) => r.machine == "Milling1")

// All sensors for specific machine - ultimi 30 minuti
from(bucket:"industrial_data")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r.machine == "Milling1")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")

// Power consumption all machines - ultima ora
from(bucket:"industrial_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "power")
  |> group(columns: ["machine"])

// ----------------------------------------------
// 2. MACHINE EFFICIENCY & UTILIZATION
// ----------------------------------------------

// Total processing time per machine - ultime 24 ore
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "machine_events")
  |> filter(fn: (r) => r.event_type == "processing_end")
  |> filter(fn: (r) => r._field == "cycle_time")
  |> group(columns: ["machine"])
  |> sum()

// Machine availability - percentage uptime
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "machine_events")
  |> filter(fn: (r) => r.event_type =~ /processing_/)
  |> group(columns: ["machine", "event_type"])
  |> count()

// Average cycle time per machine
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "machine_events")
  |> filter(fn: (r) => r.event_type == "processing_end")
  |> filter(fn: (r) => r._field == "cycle_time")
  |> group(columns: ["machine"])
  |> mean()

// ----------------------------------------------
// 3. ANOMALY DETECTION & ALERTS
// ----------------------------------------------

// High temperature alert (>80°C)
from(bucket:"industrial_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "temperature")
  |> filter(fn: (r) => r._value > 80.0)

// High vibration detection (>2.5g)
from(bucket:"industrial_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "vibration_level")
  |> filter(fn: (r) => r._value > 2.5)

// Power consumption anomaly (>5kW)
from(bucket:"industrial_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "power")
  |> filter(fn: (r) => r._value > 5.0)

// Tool wear monitoring (>0.8)
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "machine_events")
  |> filter(fn: (r) => r._field == "tool_wear")
  |> filter(fn: (r) => r._value > 0.8)
  |> group(columns: ["machine", "tool"])
  |> last()

// ----------------------------------------------
// 4. PIECE TRACKING & TRACEABILITY
// ----------------------------------------------

// Complete traceability for specific piece
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "piece_tracking")
  |> filter(fn: (r) => r.piece_id == "PZ001")
  |> sort(columns: ["_time"])

// Current pieces in production
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "machine_events")
  |> filter(fn: (r) => r.event_type == "processing_start")
  |> group(columns: ["piece_id"])
  |> last()

// Average transport time between stations
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "piece_tracking")
  |> filter(fn: (r) => r.event_type == "move_end")
  |> filter(fn: (r) => r._field == "duration")
  |> group(columns: ["from_station", "to_station"])
  |> mean()

// Production by material type
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "piece_tracking")
  |> filter(fn: (r) => r.event_type == "deposit")
  |> group(columns: ["material"])
  |> count()

// ----------------------------------------------
// 5. SYSTEM PERFORMANCE MONITORING
// ----------------------------------------------

// Event processor performance
from(bucket:"industrial_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "system_metrics")
  |> filter(fn: (r) => r.component == "event_processor")
  |> filter(fn: (r) => r._field =~ /messages_processed|processing_time|memory_usage|cpu_usage/)
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")

// System health overview
from(bucket:"industrial_data")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "system_metrics")
  |> filter(fn: (r) => r.metric_type == "health")
  |> group(columns: ["component"])
  |> last()

// Error count by component
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "system_metrics")
  |> filter(fn: (r) => r._field == "error_count")
  |> group(columns: ["component"])
  |> sum()

// ----------------------------------------------
// 6. AGGREGATED DATA & REPORTS
// ----------------------------------------------

// Daily production summary
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "piece_tracking")
  |> filter(fn: (r) => r.event_type == "deposit")
  |> group(columns: ["material"])
  |> count()
  |> rename(columns: {_value: "pieces_completed"})

// Average temperature by machine (hourly)
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "temperature")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> group(columns: ["machine"])

// Machine efficiency report (daily)
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "machine_events")
  |> filter(fn: (r) => r.event_type == "processing_end")
  |> filter(fn: (r) => r._field == "cycle_time")
  |> group(columns: ["machine"])
  |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)

// ----------------------------------------------
// 7. ADVANCED ANALYTICS
// ----------------------------------------------

// Temperature trend analysis (moving average)
from(bucket:"industrial_data")
  |> range(start: -6h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field == "temperature")
  |> filter(fn: (r) => r.machine == "Milling1")
  |> movingAverage(n: 10)

// Power consumption correlation with temperature
from(bucket:"industrial_data")
  |> range(start: -2h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r._field =~ /temperature|power/)
  |> filter(fn: (r) => r.machine == "Milling1")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")

// Production rate per hour
from(bucket:"industrial_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "machine_events")
  |> filter(fn: (r) => r.event_type == "processing_end")
  |> aggregateWindow(every: 1h, fn: count, createEmpty: false)
  |> group(columns: ["machine"])

// ----------------------------------------------
// 8. CONTINUOUS QUERIES (FOR HISTORICAL BUCKET)
// ----------------------------------------------

// Create hourly averages (da usare come task InfluxDB)
option task = {name: "hourly-averages", every: 1h}

from(bucket:"industrial_data")
  |> range(start: -2h, stop: -1h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> to(bucket: "historical_data", org: "factory")

// Create daily efficiency summary
option task = {name: "daily-efficiency", every: 1d}

from(bucket:"industrial_data")
  |> range(start: -2d, stop: -1d)
  |> filter(fn: (r) => r._measurement == "machine_events")
  |> filter(fn: (r) => r.event_type == "processing_end")
  |> filter(fn: (r) => r._field == "cycle_time")
  |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)
  |> to(bucket: "historical_data", org: "factory")