#!/usr/bin/env python3
"""Generate mammogram claims for female patients."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Mammogram CPT codes
MAMMOGRAM_CODES = [
    ('77065', 'Diagnostic mammography, including CAD; unilateral', 250.00),
    ('77066', 'Diagnostic mammography bilateral, including CAD', 350.00),
    ('77067', 'Screening mammography bilateral, including CAD', 280.00),
]

# Related ICD-10 diagnosis codes for mammograms
MAMMOGRAM_DIAGNOSES = [
    'Z12.31',  # Encounter for screening mammogram for malignant neoplasm of breast
    'N63.0',   # Unspecified lump in unspecified breast
    'R92.8',   # Other abnormal and inconclusive findings on diagnostic imaging of breast
    'Z85.3',   # Personal history of malignant neoplasm of breast
    'Z80.3',   # Family history of malignant neoplasm of breast
]

FIRST_NAMES_FEMALE = ['Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Barbara', 'Susan', 
                      'Jessica', 'Sarah', 'Karen', 'Nancy', 'Lisa', 'Betty', 'Margaret', 'Sandra', 
                      'Ashley', 'Kimberly', 'Emily', 'Donna', 'Michelle', 'Carol', 'Amanda', 'Dorothy',
                      'Melissa', 'Deborah', 'Stephanie', 'Rebecca', 'Sharon', 'Laura', 'Cynthia']

LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 
              'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 
              'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Thompson', 'White', 
              'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker']

US_CITIES = [
    ('New York', 'NY'), ('Los Angeles', 'CA'), ('Chicago', 'IL'), ('Houston', 'TX'), 
    ('Phoenix', 'AZ'), ('Philadelphia', 'PA'), ('San Antonio', 'TX'), ('San Diego', 'CA'), 
    ('Dallas', 'TX'), ('San Jose', 'CA'), ('Austin', 'TX'), ('Jacksonville', 'FL'),
    ('Boston', 'MA'), ('Seattle', 'WA'), ('Denver', 'CO'), ('Atlanta', 'GA'),
]

INSURANCE_PLANS = [
    'Standard Health Plan',
    'Premium PPO',
    'Medicare Advantage',
    'Gold Plus Plan',
]


def generate_female_patient(patient_id):
    """Generate a female patient."""
    first_name = random.choice(FIRST_NAMES_FEMALE)
    last_name = random.choice(LAST_NAMES)
    city, state = random.choice(US_CITIES)
    
    # Age range 40-75 (typical mammogram screening age)
    birth_date = datetime.now() - timedelta(days=random.randint(40*365, 75*365))
    
    return {
        'id': patient_id,
        'name': f"{first_name} {last_name}",
        'first': first_name,
        'last': last_name,
        'gender': 'F',
        'birth_date': birth_date.strftime('%Y-%m-%d'),
        'city': city,
        'state': state,
        'insurance': random.choice(INSURANCE_PLANS)
    }


def generate_realistic_date(start_date, claim_num, total_claims):
    """Generate a date with realistic temporal patterns."""
    import random as rand
    
    # Distribution across 2025
    progress = claim_num / total_claims
    base_day = rand.random() + (progress * 0.3)  # Growth trend
    base_day = min(base_day, 1.0)
    day_of_year = int(base_day * 365)
    
    # Mammograms are often scheduled, so more likely on weekdays
    temp_date = start_date + timedelta(days=day_of_year)
    if temp_date.weekday() >= 5:  # Weekend
        if rand.random() < 0.8:  # 80% chance to move to Friday
            days_to_subtract = temp_date.weekday() - 4
            day_of_year = max(0, day_of_year - days_to_subtract)
    
    return start_date + timedelta(days=day_of_year)


def generate_mammogram_claim(claim_num, patient_pool, start_date, total_claims):
    """Generate a single mammogram FHIR claim."""
    patient = random.choice(patient_pool)
    cpt_code, cpt_display, base_price = random.choice(MAMMOGRAM_CODES)
    diagnosis = random.choice(MAMMOGRAM_DIAGNOSES)
    
    # Generate service date with realistic patterns
    service_date = generate_realistic_date(start_date, claim_num, total_claims)
    
    # Add realistic time (morning appointments common for mammograms)
    hour = random.choice([8, 9, 10, 11, 12, 13, 14])
    minute = random.choice([0, 15, 30, 45])
    service_datetime = service_date.replace(hour=hour, minute=minute, second=0)
    
    # Price variance
    price_variance = random.uniform(0.95, 1.05)
    final_price = round(base_price * price_variance, 2)
    
    claim = {
        "resourceType": "Claim",
        "id": f"mammogram-{claim_num:06d}",
        "status": random.choice(['active'] * 90 + ['cancelled'] * 5 + ['draft'] * 5),
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                "code": "professional"
            }]
        },
        "use": "claim",
        "patient": {
            "reference": f"Patient/{patient['id']}",
            "display": patient['name']
        },
        "created": service_datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "provider": {
            "reference": f"Practitioner/prov-{random.randint(1, 50)}"
        },
        "priority": {
            "coding": [{
                "code": "normal"
            }]
        },
        "insurance": [{
            "sequence": 1,
            "focal": True,
            "coverage": {
                "reference": f"Coverage/{patient['id']}-coverage",
                "display": patient['insurance']
            }
        }],
        "item": [{
            "sequence": 1,
            "productOrService": {
                "coding": [{
                    "system": "http://www.ama-assn.org/go/cpt",
                    "code": cpt_code,
                    "display": cpt_display
                }]
            },
            "unitPrice": {
                "value": final_price,
                "currency": "USD"
            }
        }],
        "total": {
            "value": final_price,
            "currency": "USD"
        },
        "diagnosis": [{
            "sequence": 1,
            "diagnosisCodeableConcept": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": diagnosis
                }]
            }
        }]
    }
    
    # Add metadata for loading
    claim['_metadata'] = {
        'patient_id': patient['id'],
        'gender': patient['gender'],
        'city': patient['city'],
        'state': patient['state'],
        'cpt_code': cpt_code,
        'diagnosis': diagnosis
    }
    
    return claim


def main():
    num_claims = 5000
    num_patients = 2000  # Multiple claims per patient
    output_file = 'mammogram_claims_5k.json'
    start_date = datetime(2025, 1, 1)
    
    print(f"Generating {num_patients} female patients...")
    patients = [generate_female_patient(f"mammo-patient-{i:05d}") for i in range(1, num_patients + 1)]
    
    print(f"Generating {num_claims} mammogram claims...")
    claims = []
    for i in range(1, num_claims + 1):
        claim = generate_mammogram_claim(i, patients, start_date, num_claims)
        claims.append(claim)
        if i % 500 == 0:
            print(f"  Generated {i:,} claims...")
    
    print(f"\n✓ Generated {num_claims:,} mammogram claims for {num_patients:,} female patients")
    
    # Save claims
    output_path = Path(__file__).parent / output_file
    with open(output_path, 'w') as f:
        json.dump(claims, f, indent=2)
    print(f"✓ Saved to {output_file}")
    
    # Statistics
    total_cost = sum(claim['total']['value'] for claim in claims)
    avg_cost = total_cost / len(claims)
    
    stats = {
        'total_claims': len(claims),
        'total_patients': len(patients),
        'total_cost': round(total_cost, 2),
        'average_cost': round(avg_cost, 2),
        'procedure_distribution': {
            code: sum(1 for c in claims if c['item'][0]['productOrService']['coding'][0]['code'] == code)
            for code, _, _ in MAMMOGRAM_CODES
        }
    }
    
    stats_file = output_file.replace('.json', '.stats.json')
    with open(Path(__file__).parent / stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"✓ Statistics saved to {stats_file}")
    
    print(f"\nSummary:")
    print(f"  Total cost: ${stats['total_cost']:,.2f}")
    print(f"  Average cost per claim: ${stats['average_cost']:.2f}")
    print(f"  Procedure distribution:")
    for code, count in stats['procedure_distribution'].items():
        print(f"    {code}: {count:,} claims")


if __name__ == '__main__':
    main()
