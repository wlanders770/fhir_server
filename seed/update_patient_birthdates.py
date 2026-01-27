"""
Update patient birthdates to be within HEDIS eligible age range (50-74 years).

This script updates existing FHIR patients to have realistic birthdates that
make them eligible for the HEDIS Breast Cancer Screening measure.
"""

import requests
import random
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

FHIR_BASE = "http://localhost:8080/fhir"


def get_patients(gender='female', max_patients=2000):
    """Fetch patients from FHIR server."""
    all_patients = []
    url = f"{FHIR_BASE}/Patient"
    
    params = {
        'gender': gender,
        '_count': '200'
    }
    
    print(f"Fetching {gender} patients from FHIR server...")
    
    while len(all_patients) < max_patients:
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            bundle = response.json()
            
            if 'entry' not in bundle:
                break
            
            for entry in bundle['entry']:
                patient = entry.get('resource', {})
                all_patients.append(patient)
            
            print(f"  Fetched {len(all_patients)} patients...")
            
            # Check for next page
            links = bundle.get('link', [])
            next_link = None
            for link in links:
                if link.get('relation') == 'next':
                    next_link = link.get('url')
                    break
            
            if not next_link or len(all_patients) >= max_patients:
                break
            
            url = next_link
            params = {}  # Clear params for next page URL
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching patients: {e}")
            break
    
    print(f"Total patients fetched: {len(all_patients)}")
    return all_patients[:max_patients]


def generate_hedis_eligible_birthdate():
    """Generate a birthdate that makes patient 50-74 years old."""
    today = datetime.now()
    
    # Random age between 50 and 74
    age_years = random.randint(50, 74)
    age_days = random.randint(0, 364)  # Random day within the year
    
    total_days = (age_years * 365) + age_days
    birth_date = today - timedelta(days=total_days)
    
    return birth_date.strftime('%Y-%m-%d')


def update_patient_birthdate(patient):
    """Update a single patient's birthdate."""
    patient_id = patient.get('id')
    current_birthdate = patient.get('birthDate', 'N/A')
    
    try:
        # Generate new birthdate
        new_birthdate = generate_hedis_eligible_birthdate()
        
        # Update the patient resource
        patient['birthDate'] = new_birthdate
        
        # PUT request to update patient
        url = f"{FHIR_BASE}/Patient/{patient_id}"
        response = requests.put(url, json=patient, timeout=30)
        response.raise_for_status()
        
        return {
            'success': True,
            'patient_id': patient_id,
            'old_birthdate': current_birthdate,
            'new_birthdate': new_birthdate
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'patient_id': patient_id,
            'error': str(e)
        }


def update_patients_parallel(patients, max_workers=10):
    """Update multiple patients in parallel."""
    print(f"\nUpdating {len(patients)} patient birthdates...")
    print(f"Using {max_workers} parallel workers\n")
    
    successful = 0
    failed = 0
    errors = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all update tasks
        future_to_patient = {
            executor.submit(update_patient_birthdate, patient): patient 
            for patient in patients
        }
        
        # Process completed updates
        for i, future in enumerate(as_completed(future_to_patient), 1):
            result = future.result()
            
            if result['success']:
                successful += 1
                if successful % 50 == 0:
                    print(f"  ✓ Updated {successful}/{len(patients)} patients...")
            else:
                failed += 1
                errors.append(result)
                if failed <= 5:  # Show first 5 errors
                    print(f"  ✗ Failed to update {result['patient_id']}: {result['error']}")
    
    print(f"\n{'='*60}")
    print(f"Update Complete!")
    print(f"{'='*60}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(patients)}")
    print(f"{'='*60}\n")
    
    return successful, failed, errors


def main():
    """Main execution function."""
    print("="*60)
    print("FHIR Patient Birthdate Updater")
    print("="*60)
    print("Purpose: Update patient birthdates to HEDIS-eligible ages (50-74)")
    print()
    
    # Configuration
    max_patients = int(input("How many female patients to update? [default: 2000]: ") or "2000")
    max_workers = int(input("Number of parallel workers? [default: 10]: ") or "10")
    
    print(f"\nConfiguration:")
    print(f"  Max patients: {max_patients}")
    print(f"  Workers: {max_workers}")
    print(f"  Target age range: 50-74 years")
    print()
    
    confirm = input("Proceed with update? (yes/no): ").lower()
    if confirm != 'yes':
        print("Update cancelled.")
        return
    
    # Fetch patients
    patients = get_patients(gender='female', max_patients=max_patients)
    
    if not patients:
        print("No patients found to update.")
        return
    
    # Show sample of current vs new ages
    print("\nSample birthdate changes:")
    print(f"{'Patient ID':<25} {'Old Birthdate':<15} {'New Birthdate':<15} {'New Age':<10}")
    print("-" * 70)
    
    sample_patients = random.sample(patients, min(5, len(patients)))
    for patient in sample_patients:
        patient_id = patient.get('id', 'N/A')
        old_birthdate = patient.get('birthDate', 'N/A')
        new_birthdate = generate_hedis_eligible_birthdate()
        
        # Calculate age from new birthdate
        if new_birthdate != 'N/A':
            birth_year = int(new_birthdate.split('-')[0])
            new_age = datetime.now().year - birth_year
        else:
            new_age = 'N/A'
        
        print(f"{patient_id:<25} {old_birthdate:<15} {new_birthdate:<15} {new_age:<10}")
    
    print()
    
    # Update patients
    successful, failed, errors = update_patients_parallel(patients, max_workers)
    
    # Show summary
    if successful > 0:
        success_rate = (successful / len(patients)) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"\nPatients are now eligible for HEDIS BCS measure!")
        print(f"Test the measure at: http://localhost:5000/api/hedis-bcs")
    
    if failed > 0:
        print(f"\n⚠️  {failed} patients failed to update")
        save_errors = input("Save error log? (yes/no): ").lower()
        if save_errors == 'yes':
            with open('update_errors.log', 'w') as f:
                for error in errors:
                    f.write(f"{error}\n")
            print("Error log saved to: update_errors.log")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nUpdate interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
