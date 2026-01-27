#!/usr/bin/env python3
"""
Link mammogram claims to regular female patients (patient-*)
to populate HEDIS Breast Cancer Screening measure.
"""

import requests
from datetime import datetime, timedelta
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

FHIR_BASE = 'http://localhost:8080/fhir'

# Mammogram CPT codes for HEDIS BCS
MAMMOGRAM_CODES = [
    {'code': '77065', 'display': 'Diagnostic mammography, including CAD; unilateral'},
    {'code': '77066', 'display': 'Diagnostic mammography bilateral, including CAD'},
    {'code': '77067', 'display': 'Screening mammography bilateral, including CAD'},
    {'code': '77063', 'display': 'Screening digital breast tomosynthesis, bilateral'},
]

def get_female_patients():
    """Fetch female patients aged 50-74."""
    print("Fetching female patients aged 50-74...")
    patients = []
    
    response = requests.get(f'{FHIR_BASE}/Patient?gender=female&_count=1000')
    data = response.json()
    
    for entry in data.get('entry', []):
        patient = entry['resource']
        birth_date_str = patient.get('birthDate')
        if birth_date_str:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
            age = (datetime.now() - birth_date).days // 365
            
            # HEDIS BCS eligible: women 50-74
            if 50 <= age <= 74:
                name_parts = patient.get('name', [{}])[0]
                name = f"{name_parts.get('given', [''])[0]} {name_parts.get('family', '')}".strip()
                
                patients.append({
                    'id': patient['id'],
                    'name': name or patient['id'],
                    'age': age
                })
    
    print(f"Found {len(patients)} eligible female patients")
    return patients


def create_mammogram_claim(patient):
    """Create a mammogram claim for a patient."""
    procedure = random.choice(MAMMOGRAM_CODES)
    
    # Random date within last 27 months (HEDIS measurement period)
    days_ago = random.randint(0, 27 * 30)
    claim_date = datetime.now() - timedelta(days=days_ago)
    
    # Realistic cost
    cost = random.uniform(250, 400)
    
    claim = {
        'resourceType': 'Claim',
        'status': 'active',
        'type': {
            'coding': [{
                'system': 'http://terminology.hl7.org/CodeSystem/claim-type',
                'code': 'professional',
                'display': 'Professional'
            }]
        },
        'use': 'claim',
        'patient': {
            'reference': f"Patient/{patient['id']}",
            'display': patient['name']
        },
        'created': claim_date.strftime('%Y-%m-%dT%H:%M:%S+00:00'),
        'provider': {
            'display': 'Women\'s Health Radiology Center'
        },
        'priority': {
            'coding': [{'code': 'normal'}]
        },
        'diagnosis': [{
            'sequence': 1,
            'diagnosisCodeableConcept': {
                'coding': [{
                    'system': 'http://hl7.org/fhir/sid/icd-10',
                    'code': 'Z12.31',
                    'display': 'Encounter for screening mammogram for malignant neoplasm of breast'
                }]
            }
        }],
        'item': [{
            'sequence': 1,
            'productOrService': {
                'coding': [{
                    'system': 'http://www.ama-assn.org/go/cpt',
                    'code': procedure['code'],
                    'display': procedure['display']
                }]
            },
            'servicedDate': claim_date.strftime('%Y-%m-%d'),
            'unitPrice': {
                'value': cost,
                'currency': 'USD'
            },
            'net': {
                'value': cost,
                'currency': 'USD'
            }
        }],
        'total': {
            'value': cost,
            'currency': 'USD'
        }
    }
    
    try:
        response = requests.post(
            f'{FHIR_BASE}/Claim',
            json=claim,
            headers={'Content-Type': 'application/fhir+json'}
        )
        return response.status_code in [200, 201]
    except Exception as e:
        return False


def main():
    print("="*60)
    print("MAMMOGRAM CLAIMS GENERATOR FOR REGULAR PATIENTS")
    print("="*60)
    
    # Get eligible patients
    patients = get_female_patients()
    
    if not patients:
        print("\n❌ No eligible female patients found!")
        print("Make sure you have female patients aged 50-74.")
        return
    
    # Ask for compliance rate
    print(f"\nHow many patients should have mammograms?")
    print(f"  1 = 30% (~{int(len(patients)*0.3)} patients) - Poor")
    print(f"  2 = 50% (~{int(len(patients)*0.5)} patients) - Fair")
    print(f"  3 = 70% (~{int(len(patients)*0.7)} patients) - Good [recommended]")
    print(f"  4 = 85% (~{int(len(patients)*0.85)} patients) - Excellent")
    
    choice = input("\nChoice (1-4) [3]: ").strip() or '3'
    
    rates = {'1': 0.30, '2': 0.50, '3': 0.70, '4': 0.85}
    compliance_rate = rates.get(choice, 0.70)
    
    num_to_create = int(len(patients) * compliance_rate)
    patients_to_screen = random.sample(patients, num_to_create)
    
    print(f"\n⚠️  Creating {num_to_create} mammogram claims ({compliance_rate*100:.0f}% compliance)")
    confirm = input("Continue? (yes/no) [yes]: ").strip().lower() or 'yes'
    
    if confirm not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    print(f"\nGenerating claims...")
    created = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(create_mammogram_claim, p): p for p in patients_to_screen}
        
        for future in as_completed(futures):
            if future.result():
                created += 1
            else:
                failed += 1
            
            if (created + failed) % 50 == 0:
                print(f"  Progress: {created}/{num_to_create}")
    
    print(f"\n{'='*60}")
    print(f"✓ Created {created} mammogram claims")
    if failed > 0:
        print(f"✗ Failed {failed} claims")
    
    print(f"\n📊 Expected HEDIS Results:")
    print(f"   Denominator: {len(patients)} eligible patients")
    print(f"   Numerator: {created} with mammograms")
    print(f"   Compliance: {compliance_rate*100:.0f}%")
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. Refresh dashboard: http://localhost:5000")
    print(f"   2. Check HEDIS section (purple gradient)")
    print(f"   3. Try chat: 'Show me breast cancer screening data'")
    print(f"   4. View compliance chart and gap-in-care list")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
