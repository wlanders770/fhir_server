#!/bin/bash
# Clear all existing FHIR data

echo "⚠️  WARNING: This will delete ALL data from the FHIR server!"
echo "This includes all Claims, Patients, Practitioners, and Coverage resources."
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Stopping containers..."
docker-compose -f /home/slanders/AI/fhir_server/docker-compose.yml down

echo ""
echo "Removing database volume..."
docker volume rm fhir_server_db_data 2>/dev/null || docker volume rm AI_fhir_server_db_data 2>/dev/null || echo "Volume already removed"

echo ""
echo "Starting containers with fresh database..."
docker-compose -f /home/slanders/AI/fhir_server/docker-compose.yml up -d

echo ""
echo "Waiting for FHIR server to be ready (30 seconds)..."
sleep 30

echo ""
echo "✓ Database cleared! Ready for fresh data load."
echo ""
echo "To load realistic claims:"
echo "  cd /home/slanders/AI/fhir_server/seed"
echo "  python3 bulk_loader.py claims_realistic_100k_2.json --batch-size 200 --workers 8"
