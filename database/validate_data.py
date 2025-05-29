#!/usr/bin/env python3
"""
Data Validation Script for InfluxDB
Verifica integrità dati e performance del database
"""

import sys
import time
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi
import statistics

# Configurazione
CONFIG = {
    "url": "http://localhost:8086",
    "token": "factory-token-2024",
    "org": "factory",
    "bucket": "industrial_data"
}

class DatabaseValidator:
    def __init__(self):
        self.client = InfluxDBClient(
            url=CONFIG["url"],
            token=CONFIG["token"], 
            org=CONFIG["org"]
        )
        self.query_api = self.client.query_api()
        self.results = {}

    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()

    def test_connection(self):
        """Test connessione database"""
        print("🔗 Testing database connection...")
        try:
            ping_result = self.client.ping()
            if ping_result:
                print("✅ Database connection OK")
                return True
            else:
                print("❌ Database ping failed")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def validate_buckets(self):
        """Verifica esistenza bucket"""
        print("\n📦 Validating buckets...")
        try:
            buckets_api = self.client.buckets_api()
            buckets = buckets_api.find_buckets()
            
            expected_buckets = ["industrial_data", "historical_data", "alerts", "system_metrics"]
            found_buckets = [bucket.name for bucket in buckets.buckets]
            
            for bucket_name in expected_buckets:
                if bucket_name in found_buckets:
                    print(f"✅ Bucket '{bucket_name}' exists")
                else:
                    print(f"❌ Bucket '{bucket_name}' missing")
            
            return all(bucket in found_buckets for bucket in expected_buckets)
            
        except Exception as e:
            print(f"❌ Bucket validation error: {e}")
            return False

    def validate_measurements(self):
        """Verifica presenza measurements"""
        print("\n📊 Validating measurements...")
        
        expected_measurements = [
            "sensor_data",
            "machine_events", 
            "piece_tracking",
            "system_metrics"
        ]
        
        results = {}
        
        for measurement in expected_measurements:
            try:
                query = f'''
                from(bucket:"{CONFIG["bucket"]}")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "{measurement}")
                |> count()
                |> yield(name: "count")
                '''
                
                result = self.query_api.query(query)
                count = 0
                
                for table in result:
                    for record in table.records:
                        count += record.get_value()
                
                results[measurement] = count
                
                if count > 0:
                    print(f"✅ {measurement}: {count} records")
                else:
                    print(f"⚠️  {measurement}: No data found")
                    
            except Exception as e:
                print(f"❌ Error checking {measurement}: {e}")
                results[measurement] = -1
        
        self.results['measurements'] = results
        return all(count >= 0 for count in results.values())

    def validate_data_quality(self):
        """Verifica qualità dati"""
        print("\n🔍 Validating data quality...")
        
        # Test 1: Sensor data completeness
        try:
            query = '''
            from(bucket:"industrial_data")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "sensor_data")
            |> filter(fn: (r) => r._field == "temperature")
            |> group(columns: ["machine"])
            |> count()
            '''
            
            result = self.query_api.query(query)
            machine_counts = {}
            
            for table in result:
                for record in table.records:
                    machine = record.values.get('machine', 'unknown')
                    count = record.get_value()
                    machine_counts[machine] = count
            
            if machine_counts:
                print("✅ Temperature data by machine:")
                for machine, count in machine_counts.items():
                    print(f"   {machine}: {count} readings")
            else:
                print("⚠️  No temperature data found")
                
        except Exception as e:
            print(f"❌ Data quality check error: {e}")

        # Test 2: Data continuity (gaps detection)
        try:
            query = '''
            from(bucket:"industrial_data")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "sensor_data")
            |> filter(fn: (r) => r.machine == "Milling1")
            |> filter(fn: (r) => r._field == "temperature")
            |> elapsed(unit: 1s)
            |> filter(fn: (r) => r.elapsed > 10)
            '''
            
            result = self.query_api.query(query)
            gaps = len(list(result))
            
            if gaps == 0:
                print("✅ No significant data gaps detected")
            else:
                print(f"⚠️  {gaps} data gaps detected (>10s)")
                
        except Exception as e:
            print(f"⚠️  Gap analysis failed: {e}")

    def performance_test(self):
        """Test performance query"""
        print("\n⚡ Performance testing...")
        
        queries = [
            {
                "name": "Simple sensor query",
                "query": '''
                from(bucket:"industrial_data")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "sensor_data")
                |> filter(fn: (r) => r.machine == "Milling1")
                |> limit(n: 100)
                '''
            },
            {
                "name": "Aggregation query", 
                "query": '''
                from(bucket:"industrial_data")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "sensor_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> group(columns: ["machine"])
                |> mean()
                '''
            }
        ]
        
        performance_results = {}
        
        for test in queries:
            try:
                start_time = time.time()
                result = self.query_api.query(test["query"])
                # Consume result to measure full execution time
                list(result)
                end_time = time.time()
                
                execution_time = (end_time - start_time) * 1000  # ms
                performance_results[test["name"]] = execution_time
                
                if execution_time < 1000:  # < 1 second
                    print(f"✅ {test['name']}: {execution_time:.0f}ms")
                else:
                    print(f"⚠️  {test['name']}: {execution_time:.0f}ms (slow)")
                    
            except Exception as e:
                print(f"❌ {test['name']}: Error - {e}")
                performance_results[test["name"]] = -1
        
        self.results['performance'] = performance_results

    def validate_schema_compliance(self):
        """Verifica conformità schema"""
        print("\n📋 Validating schema compliance...")
        
        # Check required tags for sensor_data
        try:
            query = '''
            from(bucket:"industrial_data")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "sensor_data")
            |> group(columns: ["machine", "machine_type"])
            |> first()
            '''
            
            result = self.query_api.query(query)
            
            required_tags = ["machine", "machine_type"]
            found_combinations = []
            
            for table in result:
                for record in table.records:
                    combo = {
                        "machine": record.values.get("machine"),
                        "machine_type": record.values.get("machine_type")
                    }
                    if combo not in found_combinations:
                        found_combinations.append(combo)
            
            if found_combinations:
                print("✅ Schema compliance check:")
                for combo in found_combinations:
                    print(f"   Machine: {combo['machine']}, Type: {combo['machine_type']}")
            else:
                print("⚠️  No schema-compliant data found")
                
        except Exception as e:
            print(f"❌ Schema compliance error: {e}")

    def generate_report(self):
        """Genera report finale"""
        print("\n" + "="*60)
        print("📋 DATABASE VALIDATION REPORT")
        print("="*60)
        print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Measurements summary
        if 'measurements' in self.results:
            print(f"\n📊 Data Summary:")
            total_records = sum(count for count in self.results['measurements'].values() if count > 0)
            print(f"   Total records (24h): {total_records}")
            
            for measurement, count in self.results['measurements'].items():
                status = "✅" if count > 0 else "❌" if count == 0 else "⚠️"
                print(f"   {status} {measurement}: {count}")
        
        # Performance summary
        if 'performance' in self.results:
            print(f"\n⚡ Performance Summary:")
            times = [t for t in self.results['performance'].values() if t > 0]
            if times:
                avg_time = statistics.mean(times)
                print(f"   Average query time: {avg_time:.0f}ms")
                if avg_time < 500:
                    print("   ✅ Performance: Excellent")
                elif avg_time < 1000:
                    print("   ✅ Performance: Good")
                else:
                    print("   ⚠️  Performance: Needs optimization")
        
        print("\n💡 Recommendations:")
        
        # Recommendations based on results
        if 'measurements' in self.results:
            empty_measurements = [m for m, c in self.results['measurements'].items() if c == 0]
            if empty_measurements:
                print(f"   • Start data ingestion for: {', '.join(empty_measurements)}")
            
            total = sum(c for c in self.results['measurements'].values() if c > 0)
            if total < 1000:
                print("   • Increase data collection frequency")
            elif total > 100000:
                print("   • Consider data retention policies")
        
        if 'performance' in self.results:
            slow_queries = [name for name, time in self.results['performance'].items() if time > 1000]
            if slow_queries:
                print(f"   • Optimize slow queries: {', '.join(slow_queries)}")
        
        print("="*60)

    def run_full_validation(self):
        """Esegue validazione completa"""
        print("🚀 Starting Database Validation...")
        
        # Step 1: Test connection
        if not self.test_connection():
            print("❌ Cannot proceed without database connection")
            return False
        
        # Step 2: Validate buckets
        self.validate_buckets()
        
        # Step 3: Validate measurements
        self.validate_measurements()
        
        # Step 4: Data quality checks
        self.validate_data_quality()
        
        # Step 5: Performance testing
        self.performance_test()
        
        # Step 6: Schema compliance
        self.validate_schema_compliance()
        
        # Step 7: Generate report
        self.generate_report()
        
        return True

def main():
    """Funzione principale"""
    validator = DatabaseValidator()
    
    try:
        success = validator.run_full_validation()
        if success:
            print("\n🎉 Database validation completed!")
            sys.exit(0)
        else:
            print("\n❌ Database validation failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()