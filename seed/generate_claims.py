"""
Enhanced FHIR claims generator with diverse procedures, diagnoses, and demographics.
Generates realistic claim data at scale for testing and development.
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import argparse


# Comprehensive CPT code pools
CPT_CODES = {
    'office_visits': [
        ('99201', 'Office visit, new patient, level 1', 75.0),
        ('99202', 'Office visit, new patient, level 2', 115.0),
        ('99203', 'Office visit, new patient, level 3', 170.0),
        ('99204', 'Office visit, new patient, level 4', 230.0),
        ('99205', 'Office visit, new patient, level 5', 290.0),
        ('99211', 'Office visit, established, level 1', 45.0),
        ('99212', 'Office visit, established, level 2', 75.0),
        ('99213', 'Office visit, established, level 3', 125.0),
        ('99214', 'Office visit, established, level 4', 185.0),
        ('99215', 'Office visit, established, level 5', 240.0),
    ],
    'preventive': [
        ('99385', 'Annual physical, age 18-39', 175.0),
        ('99386', 'Annual physical, age 40-64', 200.0),
        ('99387', 'Annual physical, age 65+', 225.0),
        ('99395', 'Established annual physical, 18-39', 150.0),
        ('99396', 'Established annual physical, 40-64', 175.0),
        ('99397', 'Established annual physical, 65+', 200.0),
    ],
    'lab': [
        ('80053', 'Comprehensive metabolic panel', 45.0),
        ('80061', 'Lipid panel', 35.0),
        ('85025', 'Complete blood count', 25.0),
        ('84443', 'TSH test', 40.0),
        ('82947', 'Glucose blood test', 15.0),
        ('83036', 'Hemoglobin A1C', 30.0),
    ],
    'imaging': [
        ('71045', 'Chest X-ray, single view', 125.0),
        ('71046', 'Chest X-ray, 2 views', 150.0),
        ('73610', 'Ankle X-ray', 100.0),
        ('70450', 'CT head without contrast', 500.0),
        ('70553', 'MRI brain with contrast', 1200.0),
        ('76700', 'Abdominal ultrasound', 350.0),
    ],
    'procedures': [
        ('12001', 'Simple wound repair, 2.5cm or less', 250.0),
        ('12002', 'Simple wound repair, 2.6-7.5cm', 350.0),
        ('11042', 'Debridement, subcutaneous tissue', 200.0),
        ('17000', 'Destruction of lesion', 150.0),
        ('69210', 'Ear wax removal', 75.0),
        ('90471', 'Immunization administration', 25.0),
        ('90658', 'Influenza vaccine', 35.0),
    ],
    'therapy': [
        ('97110', 'Therapeutic exercise', 85.0),
        ('97112', 'Neuromuscular reeducation', 90.0),
        ('97140', 'Manual therapy', 80.0),
        ('90832', 'Psychotherapy, 30 min', 100.0),
        ('90834', 'Psychotherapy, 45 min', 150.0),
        ('90837', 'Psychotherapy, 60 min', 200.0),
    ]
}

# ICD-10 diagnosis codes
ICD10_CODES = {
    'hypertension': ['I10', 'I11.0', 'I11.9', 'I12.0', 'I13.0'],
    'diabetes': ['E11.9', 'E11.65', 'E11.8', 'E11.21', 'E11.22'],
    'respiratory': ['J06.9', 'J02.9', 'J45.909', 'J44.0', 'J20.9'],
    'musculoskeletal': ['M25.511', 'M25.561', 'M79.3', 'M54.5', 'M17.11'],
    'mental_health': ['F41.1', 'F32.9', 'F33.1', 'F41.9', 'F43.10'],
    'general': ['R51', 'R50.9', 'R07.9', 'R10.9', 'R53.83'],
    'preventive': ['Z00.00', 'Z00.01', 'Z23', 'Z13.220', 'Z79.4'],
}

# Patient demographics
FIRST_NAMES = {
    'M': ['James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph', 'Thomas', 'Charles',
          'Christopher', 'Daniel', 'Matthew', 'Anthony', 'Donald', 'Mark', 'Paul', 'Steven', 'Andrew', 'Kenneth'],
    'F': ['Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen',
          'Nancy', 'Lisa', 'Betty', 'Margaret', 'Sandra', 'Ashley', 'Kimberly', 'Emily', 'Donna', 'Michelle']
}

LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
              'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
              'Lee', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker']

US_CITIES = [
    ('New York', 'NY'), ('Los Angeles', 'CA'), ('Chicago', 'IL'), ('Houston', 'TX'), ('Phoenix', 'AZ'),
    ('Philadelphia', 'PA'), ('San Antonio', 'TX'), ('San Diego', 'CA'), ('Dallas', 'TX'), ('San Jose', 'CA'),
    ('Austin', 'TX'), ('Jacksonville', 'FL'), ('Fort Worth', 'TX'), ('Columbus', 'OH'), ('Charlotte', 'NC'),
    ('San Francisco', 'CA'), ('Indianapolis', 'IN'), ('Seattle', 'WA'), ('Denver', 'CO'), ('Boston', 'MA'),
    ('Nashville', 'TN'), ('Detroit', 'MI'), ('Portland', 'OR'), ('Las Vegas', 'NV'), ('Memphis', 'TN'),
]

INSURANCE_PLANS = [
    'Standard Health Plan',
    'Premium PPO',
    'Basic HMO',
    'Gold Plus Plan',
    'Medicare Advantage',
    'High Deductible Plan',
    'Family Health Plan',
]


def generate_patient(patient_id):
    """Generate a patient with realistic demographics."""
    gender = random.choice(['M', 'F'])
    first_name = random.choice(FIRST_NAMES[gender])
    last_name = random.choice(LAST_NAMES)
    city, state = random.choice(US_CITIES)
    
    birth_date = datetime.now() - timedelta(days=random.randint(18*365, 85*365))
    
    return {
        'id': patient_id,
        'name': f"{first_name} {last_name}",
        'first': first_name,
        'last': last_name,
        'gender': gender,
        'birth_date': birth_date.strftime('%Y-%m-%d'),
        'city': city,
        'state': state,
        'insurance': random.choice(INSURANCE_PLANS)
    }


def select_procedure_and_diagnosis():
    """Select a coherent procedure and diagnosis combination."""
    category = random.choice(list(CPT_CODES.keys()))
    cpt = random.choice(CPT_CODES[category])
    
    # Select diagnosis based on procedure type
    if category == 'preventive':
        dx_category = 'preventive'
    elif category in ['lab', 'imaging']:
        dx_category = random.choice(['diabetes', 'hypertension', 'general'])
    elif category == 'therapy':
        dx_category = random.choice(['mental_health', 'musculoskeletal'])
    else:
        dx_category = random.choice(['respiratory', 'general', 'musculoskeletal'])
    
    diagnosis = random.choice(ICD10_CODES[dx_category])
    
    return cpt, diagnosis


def generate_realistic_date(start_date, claim_num, total_claims):
    """Generate a date with realistic temporal patterns."""
    # Base distribution with slight growth trend
    # Use beta distribution for more natural clustering
    import random as rand
    from random import random as rand_float
    
    # Growth trend: more claims toward end of year
    progress = claim_num / total_claims
    growth_bias = 0.3 * progress  # 30% increase from start to end
    
    # Seasonal patterns (higher in winter/early spring, lower in summer)
    # Generate initial random day
    base_day = rand_float() + growth_bias
    base_day = min(base_day, 1.0)  # Cap at 1.0
    day_of_year = int(base_day * 365)
    
    # Apply seasonal multiplier
    month = (day_of_year // 30) + 1  # Approximate month (1-12)
    seasonal_multipliers = {
        1: 1.3,   # January - flu season, new year benefits
        2: 1.25,  # February - flu/cold season
        3: 1.2,   # March - allergies start
        4: 1.1,   # April - spring allergies
        5: 0.95,  # May - better weather, fewer visits
        6: 0.85,  # June - summer, vacation
        7: 0.8,   # July - vacation season
        8: 0.9,   # August - back to school
        9: 1.0,   # September - normal
        10: 1.05, # October - flu shots
        11: 1.1,  # November - before holidays
        12: 1.4,  # December - use benefits before year end
    }
    
    multiplier = seasonal_multipliers.get(month, 1.0)
    
    # Randomly adjust day based on seasonal multiplier
    # Higher multiplier = more likely to be in that period
    if rand_float() > (1.0 / multiplier):
        # Keep this date
        pass
    else:
        # Regenerate with bias toward high-volume months
        high_months = [1, 2, 3, 12]  # Winter/end of year
        month = random.choice(high_months)
        day_of_year = ((month - 1) * 30) + random.randint(0, 29)
    
    # Avoid weekends (reduce by 60%)
    temp_date = start_date + timedelta(days=day_of_year)
    if temp_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        if rand_float() < 0.6:  # 60% chance to move to weekday
            # Move to Friday
            days_to_subtract = temp_date.weekday() - 4
            day_of_year = max(0, day_of_year - days_to_subtract)
    
    return start_date + timedelta(days=day_of_year)


def generate_claim(claim_num, patient_pool, start_date, total_claims=100000):
    """Generate a single FHIR claim with realistic data."""
    patient = random.choice(patient_pool)
    cpt, diagnosis = select_procedure_and_diagnosis()
    
    # Generate service date with realistic temporal patterns
    service_date = generate_realistic_date(start_date, claim_num, total_claims)
    
    # Add realistic time of day (office hours: 8 AM - 5 PM)
    hour = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])  # Typical appointment times
    service_datetime = service_date.replace(hour=hour, minute=minute, second=0)
    
    # Add some price variance
    base_price = cpt[2]
    price_variance = random.uniform(0.9, 1.1)
    final_price = round(base_price * price_variance, 2)
    
    claim = {
        "resourceType": "Claim",
        "status": random.choice(['active'] * 85 + ['cancelled'] * 10 + ['draft'] * 5),
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
                "code": random.choice(['stat', 'normal', 'deferred'])
            }]
        },
        "insurance": [{
            "sequence": 1,
            "focal": True,
            "coverage": {
                "reference": f"Coverage/cov-{patient['id']}-{patient['insurance'].lower().replace(' ', '-')}",
                "display": patient['insurance']
            }
        }],
        "diagnosis": [{
            "sequence": 1,
            "diagnosisCodeableConcept": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": diagnosis
                }]
            }
        }],
        "item": [{
            "sequence": 1,
            "productOrService": {
                "coding": [{
                    "system": "http://www.ama-assn.org/go/cpt",
                    "code": cpt[0],
                    "display": cpt[1]
                }]
            },
            "servicedDate": service_date.strftime('%Y-%m-%d'),
            "locationCodeableConcept": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/service-place",
                    "code": "11",
                    "display": "Office"
                }],
                "text": f"{patient['city']}, {patient['state']}"
            },
            "unitPrice": {
                "value": final_price,
                "currency": "USD"
            },
            "net": {
                "value": final_price,
                "currency": "USD"
            }
        }],
        "total": {
            "value": final_price,
            "currency": "USD"
        },
        # Add metadata for delta tracking
        "_metadata": {
            "patient_id": patient['id'],
            "gender": patient['gender'],
            "city": patient['city'],
            "state": patient['state'],
            "cpt_code": cpt[0],
            "diagnosis": diagnosis
        }
    }
    
    return claim


def generate_dataset(num_claims, num_patients, output_file, start_date=None):
    """Generate a complete dataset of claims and patients."""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365)
    
    print(f"Generating {num_patients} patients...")
    patients = [generate_patient(f"patient-{i:06d}") for i in range(1, num_patients + 1)]
    
    print(f"Generating {num_claims} claims...")
    claims = []
    for i in range(1, num_claims + 1):
        claim = generate_claim(i, patients, start_date, num_claims)
        claims.append(claim)
        
        if i % 1000 == 0:
            print(f"  Generated {i:,} claims...")
    
    # Save to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(claims, f, indent=2)
    
    print(f"\n✓ Generated {len(claims):,} claims for {len(patients):,} patients")
    print(f"✓ Saved to {output_path}")
    
    # Generate summary stats
    stats = {
        'total_claims': len(claims),
        'total_patients': len(patients),
        'date_range': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': (start_date + timedelta(days=365)).strftime('%Y-%m-%d')
        },
        'status_distribution': {},
        'gender_distribution': {},
        'top_procedures': {},
        'top_diagnoses': {},
    }
    
    for claim in claims:
        stats['status_distribution'][claim['status']] = stats['status_distribution'].get(claim['status'], 0) + 1
        gender = claim['_metadata']['gender']
        stats['gender_distribution'][gender] = stats['gender_distribution'].get(gender, 0) + 1
        cpt = claim['_metadata']['cpt_code']
        stats['top_procedures'][cpt] = stats['top_procedures'].get(cpt, 0) + 1
        dx = claim['_metadata']['diagnosis']
        stats['top_diagnoses'][dx] = stats['top_diagnoses'].get(dx, 0) + 1
    
    # Save stats
    stats_file = output_path.with_suffix('.stats.json')
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"✓ Statistics saved to {stats_file}")
    
    return claims, patients


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate FHIR claims data')
    parser.add_argument('--claims', type=int, default=10000, help='Number of claims to generate')
    parser.add_argument('--patients', type=int, default=1000, help='Number of unique patients')
    parser.add_argument('--output', type=str, default='generated_claims.json', help='Output file path')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    start_date = None
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    
    generate_dataset(args.claims, args.patients, args.output, start_date)
