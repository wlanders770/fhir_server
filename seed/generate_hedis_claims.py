"""
Generate claims data to support HEDIS quality measures:
- COL: Colorectal Cancer Screening
- CDC: Comprehensive Diabetes Care
- CBP: Controlling High Blood Pressure
"""

import requests
from datetime import datetime, timedelta
import random
import time
import json

FHIR_BASE_URL = "http://localhost:8080/fhir"

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/fhir+json"})

# CPT Codes for measures
COLONOSCOPY_CODES = [
    ("45378", "Colonoscopy, flexible, diagnostic"),
    ("45380", "Colonoscopy with biopsy"),
    ("45385", "Colonoscopy with lesion removal"),
]

FIT_TEST_CODES = [
    ("82270", "Blood, occult, by fecal hemoglobin determination"),
    ("81528", "Oncology (colorectal) screening, quantitative")
]

HBA1C_CODES = [
    ("83036", "Hemoglobin; glycosylated (A1C)"),
    ("83037", "Hemoglobin; glycosylated (A1C) by device")
]

BP_OFFICE_VISIT_CODES = [
    ("99213", "Office visit, established patient, low complexity"),
    ("99214", "Office visit, established patient, moderate complexity"),
    ("99215", "Office visit, established patient, high complexity"),
    ("99203", "Office visit, new patient, low complexity"),
    ("99204", "Office visit, new patient, moderate complexity")
]

# ICD-10 Diagnosis codes
DIABETES_CODES = [
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("E11.65", "Type 2 diabetes mellitus with hyperglycemia"),
    ("E10.9", "Type 1 diabetes mellitus without complications")
]

HYPERTENSION_CODES = [
    ("I10", "Essential (primary) hypertension"),
    ("I11.9", "Hypertensive heart disease without heart failure"),
    ("I15.9", "Secondary hypertension, unspecified")
]

FIRST_NAMES = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
               'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica']
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


def create_patient(patient_id, gender, age_min, age_max):
    """Create a patient with specified gender and age range using PUT."""
    age = random.randint(age_min, age_max)
    birth_date = datetime.now() - timedelta(days=age*365)
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "gender": gender,
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


def create_condition(condition_id, patient_id, code, display):
    """Create a condition (diagnosis) for a patient using PUT."""
    condition = {
        "resourceType": "Condition",
        "id": condition_id,
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "code": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": code,
                "display": display
            }],
            "text": display
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "onsetDateTime": (datetime.now() - timedelta(days=random.randint(180, 1095))).isoformat()
    }
    
    url = f"{FHIR_BASE_URL}/Condition/{condition_id}"
    response = SESSION.put(url, json=condition)
    if response.status_code in [200, 201]:
        return condition_id
    else:
        print(f"Failed to create condition {condition_id}: {response.status_code} - {response.text[:200]}")
    return None


def create_claim(claim_id, patient_id, cpt_code, cpt_display, days_ago):
    """Create a claim with specified CPT code using PUT."""
    claim_date = datetime.now() - timedelta(days=days_ago)
    price = random.uniform(100, 500)
    
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


def generate_col_claims(num_patients=1000):
    """Generate Colorectal Cancer Screening claims."""
    print(f"\n=== Generating {num_patients} patients for COL measure ===")
    created = 0
    claim_counter = 0
    
    for i in range(num_patients):
        # Create patient aged 45-75
        gender = random.choice(["male", "female"])
        patient_id = f"col-patient-{i+1:06d}"
        
        if not create_patient(patient_id, gender, 45, 75):
            continue
        
        # Create coverage for patient
        create_coverage(f"{patient_id}-coverage", patient_id)
        
        # 70% get colonoscopy (10 year lookback - compliant)
        if random.random() < 0.7:
            days_ago = random.randint(30, 3650)  # Within 10 years
            code, display = random.choice(COLONOSCOPY_CODES)
            claim_counter += 1
            create_claim(f"col-claim-{claim_counter:06d}", patient_id, code, display, days_ago)
        # 20% get FIT test (1 year lookback - compliant)
        elif random.random() < 0.67:  # 20% of remaining 30%
            days_ago = random.randint(30, 365)  # Within 1 year
            code, display = random.choice(FIT_TEST_CODES)
            claim_counter += 1
            create_claim(f"col-claim-{claim_counter:06d}", patient_id, code, display, days_ago)
        # 10% get nothing (gap in care)
        
        created += 1
        if (i + 1) % 100 == 0:
            print(f"  Created {i + 1}/{num_patients} COL patients...")
            time.sleep(0.1)  # Brief pause
    
    print(f"✓ Created {created} COL patients with {claim_counter} screening claims")


def generate_cdc_claims(num_patients=1000):
    """Generate Comprehensive Diabetes Care claims."""
    print(f"\n=== Generating {num_patients} patients for CDC measure ===")
    created = 0
    claim_counter = 0
    
    for i in range(num_patients):
        # Create patient aged 18-75
        gender = random.choice(["male", "female"])
        patient_id = f"cdc-patient-{i+1:06d}"
        
        if not create_patient(patient_id, gender, 18, 75):
            continue
        
        # Create coverage for patient
        create_coverage(f"{patient_id}-coverage", patient_id)
        
        # Add diabetes diagnosis
        diabetes_code, diabetes_display = random.choice(DIABETES_CODES)
        create_condition(f"cdc-cond-{i+1:06d}", patient_id, diabetes_code, diabetes_display)
        
        # 75% get HbA1c test in last year (compliant)
        if random.random() < 0.75:
            days_ago = random.randint(30, 365)
            code, display = random.choice(HBA1C_CODES)
            claim_counter += 1
            create_claim(f"cdc-claim-{claim_counter:06d}", patient_id, code, display, days_ago)
        # 25% don't get tested (gap in care)
        
        created += 1
        if (i + 1) % 100 == 0:
            print(f"  Created {i + 1}/{num_patients} CDC patients...")
            time.sleep(0.1)
    
    print(f"✓ Created {created} CDC patients with {claim_counter} HbA1c claims")


def generate_cbp_claims(num_patients=1000):
    """Generate Controlling Blood Pressure claims."""
    print(f"\n=== Generating {num_patients} patients for CBP measure ===")
    created = 0
    claim_counter = 0
    
    for i in range(num_patients):
        # Create patient aged 18-85
        gender = random.choice(["male", "female"])
        patient_id = f"cbp-patient-{i+1:06d}"
        
        if not create_patient(patient_id, gender, 18, 85):
            continue
        
        # Create coverage for patient
        create_coverage(f"{patient_id}-coverage", patient_id)
        
        # Add hypertension diagnosis
        htn_code, htn_display = random.choice(HYPERTENSION_CODES)
        create_condition(f"cbp-cond-{i+1:06d}", patient_id, htn_code, htn_display)
        
        # 70% have office visits with BP monitoring (controlled - compliant)
        if random.random() < 0.7:
            # Create 2-3 office visits in the past year
            num_visits = random.randint(2, 3)
            for visit_num in range(num_visits):
                days_ago = random.randint(30, 365)
                code, display = random.choice(BP_OFFICE_VISIT_CODES)
                claim_counter += 1
                create_claim(f"cbp-claim-{claim_counter:06d}", patient_id, code, display, days_ago)
        # 30% don't have recent visits (gap in care)
        
        created += 1
        if (i + 1) % 100 == 0:
            print(f"  Created {i + 1}/{num_patients} CBP patients...")
            time.sleep(0.1)
    
    print(f"✓ Created {created} CBP patients with {claim_counter} office visit claims")


def main():
    print("=" * 60)
    print("HEDIS Quality Measures - Claims Data Generator")
    print("=" * 60)
    print("\nThis will generate 3000 patients and associated claims.")
    print("Estimated time: 15-20 minutes")
    print("=" * 60)
    
    # Create practitioner first
    print("\n=== Creating Practitioner ===")
    if create_practitioner("prov-1", "Sarah", "Johnson"):
        print("✓ Created Dr. Sarah Johnson (Practitioner/prov-1)")
    else:
        print("✗ Failed to create practitioner - continuing anyway")
    
    # Generate claims for each measure
    generate_col_claims(1000)
    generate_cdc_claims(1000)
    generate_cbp_claims(1000)
    
    print("\n" + "=" * 60)
    print("✓ HEDIS claims generation complete!")
    print("=" * 60)
    print("\nSummary:")
    print("  - COL: 1000 patients (ages 45-75) with colonoscopy/FIT claims")
    print("  - CDC: 1000 patients (ages 18-75) with diabetes + HbA1c claims")
    print("  - CBP: 1000 patients (ages 18-85) with hypertension + office visits")
    print("\nExpected compliance rates:")
    print("  - COL: ~70% (colonoscopy) + ~20% (FIT) = 90%")
    print("  - CDC: ~75%")
    print("  - CBP: ~70%")
    print("\nRefresh your dashboard to see the updated HEDIS measures!")


if __name__ == "__main__":
    main()
