# HAPI FHIR Server (R4) - Docker Quickstart

This sets up a production-ready HAPI FHIR JPA Server backed by Postgres.

## Services
- Postgres 16 (mapped: host 5436 -> container 5432)
- HAPI FHIR JPA Server (R4) at http://localhost:8080/fhir

## Start
```bash
cd ~/AI/fhir_server
docker-compose up -d
```
Wait ~30–60s for initialization. Check health:
```bash
curl -s http://localhost:8080/fhir/metadata | head -40
```

## Create a Patient
```bash
curl -s -X POST \
  http://localhost:8080/fhir/Patient \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "Patient",
    "name": [{"use":"official","family":"Doe","given":["Jane"]}],
    "gender": "female",
    "birthDate": "1985-01-01"
  }' | jq .
```

## Search Patients
```bash
curl -s "http://localhost:8080/fhir/Patient?_count=5" | jq '.total, .entry[0].resource.id'
```

## Bulk Import (Demo Health Claims)
Seeds demo Claim resources and minimal linked Patient, Practitioner, and Coverage into HAPI FHIR.

Script: see [seed/bulk_seed.py](seed/bulk_seed.py).

```bash
# Import first 50 demo claims
python3 seed/bulk_seed.py --limit 50

# Import all claims from the default file
python3 seed/bulk_seed.py

# Customize FHIR base or claims path
python3 seed/bulk_seed.py --fhir-base http://localhost:8080/fhir \
  --claims /home/slanders/AI/HealthClaims/embeddings_test/fhir_claims_1000.json --limit 200

# Verify via FHIR searches
curl -s "http://localhost:8080/fhir/Claim?_count=5" | jq '.entry[]?.resource.id'
curl -s "http://localhost:8080/fhir/Patient?name=John%20Johnson&_count=1" | jq '.entry[0].resource.id'
```

Notes:
- The seeder creates deterministic IDs for Patient from the display name and for Coverage from patient+plan name.
- Practitioner references like Practitioner/prov-11 are upserted if missing.
- Claims in the demo file are adjusted to include proper references rather than display-only fields.

## Configuration
- Context path: `/fhir`
- CORS enabled (allow all origins)
- DB: Postgres (user: fhir, pass: fhirpass, db: fhir)
- Auto schema update enabled for convenience (`ddl-auto: update`)

To change DB creds or ports, edit `docker-compose.yml` and `hapi/application.yaml`.

## Stop & Cleanup
```bash
docker-compose down
# remove stored DB data if needed (irreversible)
docker volume rm fhir_server_db_data
```

## Notes
- For external exposure, put HAPI behind a reverse proxy (TLS)
- Consider enabling validation and subscriptions per your needs
- For R5, change `hapi.fhir.version` accordingly
