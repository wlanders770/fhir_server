"""
Generate claims data to support HEDIS Breast Cancer Screening (BCS) measure.
Creates female patients aged 50-74 with mammogram claims.
"""

import requests
from datetime import datetime, timedelta
import random
import time

FHIR_BASE_URL = "http://localhost:8080/fhir"

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/fhir+json"})

# Mammography CPT codes
MAMMOGRAPHY_CODES = [
    ("77065", "Diagnostic mammography, unilateral"),
    ("77066", "Diagnostic mammography bilateral"),
    ("77067", "Screening mammography bilateral"),
    ("77063", "Screening digital breast tomosynthesis, bilateral"),
    ("77061", "Digital breast tomosynthesis, unilateral"),
    ("77062", "Digital breast tomosynthesis, bilateral")
]

FIRST_NAMES = ['Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Barbara', 'Susan',
               'Jessica', 'Sarah', 'Karen', 'Nancy', 'Lisa', 'Betty', 'Margaret', 'Sandra']
LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']

INSURANCE_PLANS = ['Blue Cross PPO', 'Aetna HMO', 'Cigna PPO', 'UnitedHealthcare',
                   'Medicare', 'Medicaid', 'Humana']


def create_practitioner(practitioner_id, first_name, last_name):
    """Create a practitioner resource using PUT."""
    practitioner = {
        "resourceType": "Practitioner",
        "id": practitioner_id,
        "active": True,
        "name": [{
            "family": last_name,
            "given": [first_name],
            "text": f"Dr. {first_name} {last_name}"
        }],
        "qualification": [{
            "code": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0360/2.7",
                    "code": "MD",
                    "display": "Doctor of Medicine"
                }]
            }
        }]
    }
    
    url = f"{FHIR_BASE_URL}/Practitioner/{practitioner_id}"
    response = SESSION.put(url, json=practitioner)
    if response.status_code in [200, 201]:
        return practitioner_id
    else:
        print(f"Failed to create practitioner {practitioner_id}: {response.status_code}")
        return None


def create_coverage(coverage_id, patient_id):
    """Create a coverage (insurance) resource for a patient using PUT."""
    plan_name = random.choice(INSURANCE_PLANS)
    
    coverage = {
        "resourceType": "Coverage",
        "id": coverage_id,
        "status": "active",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "HIP",
                "display": "health insurance plan policy"
            }]
        },
        "subscriber": {
            "reference": f"Patient/{patient_id}"
        },
        "beneficiary": {
            "reference": f"Patient/{patient_id}"
        },
        "payor": [{
            "display": plan_name
        }],
        "class": [{
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
                    "code": "plan"
                }]
            },
            "value": plan_name
        }]
    }
    
    url = f"{FHIR_BASE_URL}/Coverage/{coverage_id}"
    response = SESSION.put(url, json=coverage)
    if response.status_code in [200, 201]:
        return coverage_id
    else:
        print(f"Failed to create coverage {coverage_id}: {response.status_code}")
        return None


def create_patient(patient_id, age_min, age_max):
    """Create a female patient with specified age range using PUT."""
    age = random.randint(age_min, age_max)
    birth_date = datetime.now() - timedelta(days=age*365)
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "gender": "female",
        "birthDate": birth_date.strftime("%Y-%m-%d"),
        "name": [{
            "family": last_name,
            "given": [first_name],
            "text": f"{first_name} {last_name}"
        }]
    }
    
    url = f"{FHIR_BASE_URL}/Patient/{patient_id}"
    response = SESSION.put(url, json=patient)
    if response.status_code in [200, 201]:
        return patient_id
    else:
        print(f"Failed to create patient {patient_id}: {response.status_code} - {response.text[:200]}")
        return None


def create_claim(claim_id, patient_id, cpt_code, cpt_display, days_ago):
    """Create a mammogram claim using PUT."""
    claim_date = datetime.now() - timedelta(days=days_ago)
    price = random.uniform(200, 400)
    
    claim = {
        "resourceType": "Claim",
        "id": claim_id,
        "status": "active",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                "code": "professional"
            }]
        },
        "use": "claim",
        "patient": {
            "reference": f"Patient/{patient_id}"
        },
        "created": claim_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "provider": {
            "reference": "Practitioner/prov-1"
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
                "reference": f"Coverage/{patient_id}-coverage"
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
            "servicedDate": claim_date.strftime("%Y-%m-%d"),
            "unitPrice": {
                "value": price,
                "currency": "USD"
            },
            "net": {
                "value": price,
                "currency": "USD"
            }
        }],
        "total": {
            "value": price,
            "currency": "USD"
        }
    }
    
    url = f"{FHIR_BASE_URL}/Claim/{claim_id}"
    response = SESSION.put(url, json=claim)
    if response.status_code in [200, 201]:
        return claim_id
    else:
        print(f"Failed to create claim {claim_id}: {response.status_code} - {response.text[:200]}")
        return None


def generate_bcs_claims(num_patients=1000, compliance_rate=0.75):
    """Generate Breast Cancer Screening claims."""
    print(f"\n=== Generating {num_patients} patients for BCS measure ===")
    print(f"Target compliance rate: {compliance_rate * 100}%")
    created = 0
    claim_counter = 0
    
    for i in range(num_patients):
        # Create female patient aged 50-74
        patient_id = f"bcs-patient-{i+1:06d}"
        
        if not create_patient(patient_id, 50, 74):
            continue
        
        # Create coverage for patient
        create_coverage(f"{patient_id}-coverage", patient_id)
        
        # Generate mammogram claim based on compliance rate
        if random.random() < compliance_rate:
            # Within 27 months (compliant)
            days_ago = random.randint(30, 820)  # 30 days to 27 months
            code, display = random.choice(MAMMOGRAPHY_CODES)
            claim_counter += 1
            create_claim(f"bcs-claim-{claim_counter:06d}", patient_id, code, display, days_ago)
        # else: gap in care (no mammogram)
        
        created += 1
        if (i + 1) % 100 == 0:
            print(f"  Created {i + 1}/{num_patients} BCS patients...")
            time.sleep(0.1)  # Brief pause
    
    print(f"✓ Created {created} BCS patients with {claim_counter} mammogram claims")
    print(f"Expected compliance: ~{compliance_rate * 100}%")


def main():
    print("=" * 60)
    print("HEDIS Breast Cancer Screening (BCS) - Data Generator")
    print("=" * 60)
    print("\nThis will generate 1000 female patients aged 50-74")
    print("with mammogram claims for 75% compliance rate.")
    print("Estimated time: 5-7 minutes")
    print("=" * 60)
    
    # Create practitioner first if needed
    print("\n=== Ensuring Practitioner exists ===")
    if create_practitioner("prov-1", "Sarah", "Johnson"):
        print("✓ Dr. Sarah Johnson (Practitioner/prov-1) ready")
    
    # Generate BCS claims with 75% compliance
    generate_bcs_claims(num_patients=1000, compliance_rate=0.75)
    
    print("\n" + "=" * 60)
    print("✓ BCS claims generation complete!")
    print("=" * 60)
    print("\nSummary:")
    print("  - BCS: 1000 female patients (ages 50-74)")
    print("  - Expected compliance: ~75%")
    print("  - Mammogram lookback: 27 months")
    print("\nRefresh your dashboard to see the BCS measure results!")


if __name__ == "__main__":
    main()
