# Makefile for Database Operations
# IoT Industrial Project

.PHONY: help setup validate clean reset build test

# Default target
help:
	@echo "🗄️  Database Management Commands"
	@echo "================================"
	@echo "setup      - Initialize InfluxDB with schema"
	@echo "validate   - Validate database integrity"
	@echo "test       - Run database tests"
	@echo "clean      - Clean up database containers"
	@echo "reset      - Reset database (WARNING: deletes all data)"
	@echo "build      - Build setup container"
	@echo "monitor    - Show database statistics"
	@echo "backup     - Backup database"
	@echo "restore    - Restore database from backup"

# Setup database
setup:
	@echo "🚀 Setting up InfluxDB..."
	python setup_database.py

# Validate database
validate:
	@echo "🔍 Validating database..."
	python validate_data.py

# Test database functionality
test: validate
	@echo "✅ Database tests completed"

# Build setup container
build:
	@echo "🔨 Building database setup container..."
	docker build -f Dockerfile.setup -t iot-db-setup .

# Setup using container
setup-docker: build
	@echo "🐳 Setting up database using container..."
	docker run --rm --network iot-industrial-network \
		-e INFLUXDB_URL=http://influxdb:8086 \
		iot-db-setup

# Validate using container  
validate-docker: build
	@echo "🔍 Validating database using container..."
	docker run --rm --network iot-industrial-network \
		-e INFLUXDB_URL=http://influxdb:8086 \
		iot-db-setup python validate_data.py

# Monitor database
monitor:
	@echo "📊 Database Statistics:"
	@echo "======================"
	@docker stats influxdb --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
	@echo ""
	@echo "📦 Container Status:"
	@docker ps --filter name=influxdb --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Clean database containers
clean:
	@echo "🧹 Cleaning database containers..."
	@docker stop influxdb 2>/dev/null || true
	@docker rm influxdb 2>/dev/null || true
	@docker volume rm iot-industrial-project_influxdb_data 2>/dev/null || true
	@docker volume rm iot-industrial-project_influxdb_config 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Reset database (DANGER)
reset: clean
	@echo "⚠️  WARNING: This will DELETE ALL DATABASE DATA!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	@echo "🔄 Recreating database..."
	@cd .. && docker-compose up -d influxdb
	@sleep 10
	@$(MAKE) setup
	@echo "✅ Database reset completed"

# Backup database
backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S) && \
	docker exec influxdb influx backup /tmp/backup_$$TIMESTAMP && \
	docker cp influxdb:/tmp/backup_$$TIMESTAMP ./backups/ && \
	echo "✅ Backup created: backups/backup_$$TIMESTAMP"

# Restore database
restore:
	@echo "📥 Available backups:"
	@ls -la backups/ 2>/dev/null || echo "No backups found"
	@read -p "Enter backup directory name: " backup_dir && \
	docker cp ./backups/$$backup_dir influxdb:/tmp/ && \
	docker exec influxdb influx restore /tmp/$$backup_dir && \
	echo "✅ Database restored from $$backup_dir"

# Show database logs
logs:
	@echo "📋 InfluxDB Logs (last 50 lines):"
	@echo "=================================="
	@docker logs --tail 50 influxdb

# Interactive database shell
shell:
	@echo "🐚 Opening InfluxDB CLI..."
	@docker exec -it influxdb influx

# Development helpers
dev-setup: setup validate
	@echo "🔧 Development environment ready!"
	@echo "📊 InfluxDB UI: http://localhost:8086"
	@echo "📋 Schema file: schema.json"
	@echo "🔍 Sample queries: sample_queries.flux"

# Check database health
health:
	@echo "🏥 Database Health Check:"
	@echo "========================"
	@curl -s http://localhost:8086/health | python -m json.tool || echo "❌ Database not responding"
	@echo ""
	@echo "📊 Quick Stats:"
	@python -c "
import requests
try:
    r = requests.get('http://localhost:8086/api/v2/buckets', headers={'Authorization': 'Token factory-token-2024'})
    if r.status_code == 200:
        buckets = r.json().get('buckets', [])
        print(f'✅ Found {len(buckets)} buckets')
        for bucket in buckets:
            print(f'   📦 {bucket[\"name\"]} (retention: {bucket.get(\"retentionRules\", [{}])[0].get(\"everySeconds\", \"N/A\")}s)')
    else:
        print('❌ Cannot access buckets API')
except Exception as e:
    print(f'❌ Health check failed: {e}')
"

# Install Python dependencies
deps:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Quick start for new developers
quickstart: deps setup validate
	@echo ""
	@echo "🎉 Database setup completed successfully!"
	@echo "======================================="
	@echo "✅ InfluxDB is running and configured"
	@echo "✅ Schema is validated"
	@echo "✅ Sample data is loaded"
	@echo ""
	@echo "🔗 Next steps:"
	@echo "   1. Open InfluxDB UI: http://localhost:8086"
	@echo "   2. Login with admin/admin123"
	@echo "   3. Check the industrial_data bucket"
	@echo "   4. Try sample queries from sample_queries.flux"
	@echo ""
	@echo "📞 Need help? Run: make help"