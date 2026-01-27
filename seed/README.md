# Enhanced Claims Generator and Bulk Loader

## Overview

This directory contains tools for generating and loading large-scale FHIR claims data:

- **`generate_claims.py`**: Generate realistic claims with diverse procedures, diagnoses, and patient demographics
- **`bulk_loader.py`**: High-performance bulk loader supporting parallel processing and delta updates
- **`bulk_seed.py`**: Original simple seeder (kept for compatibility)

## Quick Start

### 1. Generate Claims Data

Generate 10,000 claims for 1,000 patients:

```bash
python3 generate_claims.py --claims 10000 --patients 1000 --output my_claims.json
```

**Options:**
- `--claims N`: Number of claims to generate (default: 10000)
- `--patients N`: Number of unique patients (default: 1000)
- `--output FILE`: Output file path (default: generated_claims.json)
- `--start-date YYYY-MM-DD`: Start date for claim date range (default: 1 year ago)

**Output:**
- `my_claims.json`: Claims data
- `my_claims.stats.json`: Statistics summary

### 2. Bulk Load Claims

Load claims with parallel processing:

```bash
python3 bulk_loader.py my_claims.json --batch-size 100 --workers 4
```

**Options:**
- `--fhir-base URL`: FHIR server base URL (default: http://localhost:8080/fhir)
- `--batch-size N`: Claims per batch (default: 100)
- `--workers N`: Parallel workers (default: 4)
- `--no-wait`: Skip server readiness check
- `--delta`: Load only new/changed claims
- `--hash-file FILE`: Existing hash file for delta mode

## Features

### Enhanced Data Generation

**Diverse Procedures (CPT Codes):**
- Office visits (99201-99215)
- Preventive care (99385-99397)
- Lab tests (80053, 85025, etc.)
- Imaging (71045, 70450, 76700, etc.)
- Procedures (wound repair, debridement, etc.)
- Therapy (physical therapy, psychotherapy, etc.)

**Realistic Diagnoses (ICD-10):**
- Hypertension (I10, I11.0, etc.)
- Diabetes (E11.9, E11.65, etc.)
- Respiratory conditions (J06.9, J45.909, etc.)
- Musculoskeletal (M25.511, M54.5, etc.)
- Mental health (F41.1, F32.9, etc.)
- General symptoms (R51, R50.9, etc.)

**Patient Demographics:**
- Gender: M/F distribution
- Names: Common first/last names
- Locations: 25 major US cities with state codes
- Insurance: 7 different plan types
- Realistic birth dates (18-85 years old)

### High-Performance Loading

**Parallel Processing:**
- Configurable worker threads
- Batch processing for efficiency
- Automatic retry on transient failures
- Rate limiting protection

**Progress Tracking:**
- Real-time progress updates
- Claims/second rate calculation
- Comprehensive statistics
- Error reporting

**Delta/Incremental Updates:**
- SHA-256 hash-based change detection
- Load only new or modified claims
- Persistent hash storage
- Efficient for regular updates

## Usage Examples

### Generate Small Test Set
```bash
python3 generate_claims.py --claims 1000 --patients 100 --output test.json
```

### Generate Large Production Set
```bash
python3 generate_claims.py --claims 100000 --patients 10000 --output production.json
```

### Load with Default Settings
```bash
python3 bulk_loader.py production.json
```

### Load with Optimized Settings for Large Datasets
```bash
python3 bulk_loader.py production.json --batch-size 200 --workers 8
```

### Delta Update Workflow

**Initial load:**
```bash
python3 bulk_loader.py claims_v1.json
# Creates claims_v1.hashes.json automatically
```

**Generate new claims:**
```bash
python3 generate_claims.py --claims 5000 --patients 500 --output claims_v2.json
```

**Load only changes:**
```bash
python3 bulk_loader.py claims_v2.json --delta --hash-file claims_v1.hashes.json
```

## Performance Guidelines

### Recommended Settings by Dataset Size

| Claims | Batch Size | Workers | Expected Time* |
|--------|------------|---------|----------------|
| 1,000  | 50         | 2       | ~15 seconds    |
| 10,000 | 100        | 4       | ~2 minutes     |
| 50,000 | 150        | 6       | ~8 minutes     |
| 100,000| 200        | 8       | ~15 minutes    |
| 500,000| 250        | 10      | ~60 minutes    |

*Approximate times on typical hardware with local FHIR server

### Tuning Tips

**For faster loading:**
- Increase `--workers` (up to CPU cores)
- Increase `--batch-size` (diminishing returns >300)
- Use local FHIR server (avoid network latency)
- Use SSD storage for FHIR database

**For stability:**
- Decrease `--workers` if seeing timeouts
- Decrease `--batch-size` if seeing memory issues
- Monitor FHIR server logs for errors

## Data Structure

### Generated Claim Format

Each claim includes:
- **Patient reference** with demographics
- **Practitioner reference**
- **Insurance/Coverage reference**
- **Diagnosis** (ICD-10 code)
- **Procedure** (CPT code with description)
- **Service location** (city, state)
- **Cost information** (unit price, total)
- **Status** (active 85%, cancelled 10%, draft 5%)
- **Metadata** (for analytics and delta tracking)

Example:
```json
{
  "resourceType": "Claim",
  "status": "active",
  "patient": {
    "reference": "Patient/patient-000123",
    "display": "John Smith"
  },
  "diagnosis": [{
    "sequence": 1,
    "diagnosisCodeableConcept": {
      "coding": [{
        "system": "http://hl7.org/fhir/sid/icd-10",
        "code": "I10"
      }]
    }
  }],
  "item": [{
    "productOrService": {
      "coding": [{
        "system": "http://www.ama-assn.org/go/cpt",
        "code": "99213",
        "display": "Office visit, established patient"
      }]
    },
    "locationCodeableConcept": {
      "text": "New York, NY"
    },
    "unitPrice": {
      "value": 125.50,
      "currency": "USD"
    }
  }],
  "_metadata": {
    "patient_id": "patient-000123",
    "gender": "M",
    "city": "New York",
    "state": "NY",
    "cpt_code": "99213",
    "diagnosis": "I10"
  }
}
```

## Statistics Output

Generated statistics include:
- Total claims/patients
- Date range
- Status distribution
- Gender distribution
- Top procedures (by frequency)
- Top diagnoses (by frequency)

## Troubleshooting

### "Connection refused" errors
- Ensure FHIR server is running: `docker ps`
- Check server URL matches `--fhir-base`
- Wait for server startup (use without `--no-wait`)

### Slow loading
- Reduce `--workers` if seeing timeouts
- Check FHIR server CPU/memory usage
- Monitor network latency
- Consider increasing batch size

### Out of memory
- Reduce `--batch-size`
- Reduce `--workers`
- Process claims in smaller files
- Increase Docker container memory limits

### Duplicate claims
- Use delta mode for incremental updates
- Check claim metadata for uniqueness
- Verify patient IDs are consistent

## Integration with Web App

After loading claims, view them in the web dashboard:

```bash
# Access the web app
open http://localhost:5000

# Or check claim count
curl "http://localhost:8080/fhir/Claim?_summary=count"
```

The web app will automatically display:
- Claims timeline charts
- Procedure distribution
- Cost analysis
- Geographic distribution
- Gender-based analytics

## Advanced: Continuous Data Pipeline

For ongoing data generation and loading:

```bash
#!/bin/bash
# daily_claims_update.sh

DATE=$(date +%Y-%m-%d)
CLAIMS_FILE="claims_$DATE.json"

# Generate daily claims
python3 generate_claims.py \
  --claims 1000 \
  --patients 200 \
  --output "$CLAIMS_FILE" \
  --start-date "$DATE"

# Load with delta mode
python3 bulk_loader.py \
  "$CLAIMS_FILE" \
  --delta \
  --hash-file previous_claims.hashes.json \
  --workers 4

# Archive
mv "$CLAIMS_FILE" archive/
```

## See Also

- [Main README](../README.md) - Overall project documentation
- [SOLUTION_SUMMARY](../SOLUTION_SUMMARY.md) - Complete architecture guide
- FHIR R4 Specification: https://hl7.org/fhir/R4/
- CPT Code Reference: https://www.ama-assn.org/practice-management/cpt
- ICD-10 Code Reference: https://www.cdc.gov/nchs/icd/icd-10-cm.htm
