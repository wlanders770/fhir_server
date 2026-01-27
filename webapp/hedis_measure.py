"""
HEDIS Breast Cancer Screening (BCS) Measure Calculator

Implements the HEDIS BCS measure logic based on the CQL specification.
Evaluates claims data from FHIR server to determine compliance rates.
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import requests
from typing import Dict, List, Tuple, Any

# Mammography CPT codes
MAMMOGRAPHY_CODES = ['77065', '77066', '77067', '77063', '77061', '77062']

# Exclusion ICD-10 codes
BILATERAL_MASTECTOMY_CODES = ['Z90.13']
UNILATERAL_MASTECTOMY_CODES = ['Z90.11', 'Z90.12']


class HEDISBreastCancerScreening:
    """
    HEDIS Breast Cancer Screening measure calculator.
    
    Measurement Period: 27 months prior to the end date
    Initial Population: Women aged 50-74
    Numerator: At least one mammogram during measurement period
    Denominator: Initial population minus exclusions
    Exclusions: Bilateral mastectomy or two unilateral mastectomies
    """
    
    def __init__(self, fhir_base_url: str = "http://hapi-fhir:8080/fhir"):
        self.fhir_base_url = fhir_base_url
        self.measurement_end = datetime.now()
        self.measurement_start = self.measurement_end - relativedelta(months=27)
        
    def query_fhir(self, resource_type: str, params: dict) -> dict:
        """Query FHIR server and return bundle."""
        try:
            response = requests.get(
                f"{self.fhir_base_url}/{resource_type}",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    def get_patient_age(self, birth_date_str: str) -> int:
        """Calculate patient age at measurement end."""
        try:
            birth_date = datetime.fromisoformat(birth_date_str.replace('Z', '+00:00'))
            age = relativedelta(self.measurement_end, birth_date).years
            return age
        except (ValueError, AttributeError):
            return 0
    
    def is_in_initial_population(self, patient: dict) -> bool:
        """
        Check if patient is in initial population.
        Criteria: Female, age 50-74 at end of measurement period
        """
        # Check gender
        gender = patient.get('gender', '').lower()
        if gender != 'female':
            return False
        
        # Check age
        birth_date = patient.get('birthDate', '')
        if not birth_date:
            return False
        
        age = self.get_patient_age(birth_date)
        return 50 <= age <= 74
    
    def has_exclusion(self, patient_id: str) -> bool:
        """
        Check if patient has exclusion criteria.
        Exclusions: Bilateral mastectomy or two unilateral mastectomies
        """
        # Query conditions for this patient
        params = {
            'patient': patient_id,
            '_count': '100',
            'clinical-status': 'active'
        }
        bundle = self.query_fhir('Condition', params)
        
        if 'error' in bundle or 'entry' not in bundle:
            return False
        
        bilateral_count = 0
        unilateral_count = 0
        
        for entry in bundle.get('entry', []):
            condition = entry.get('resource', {})
            code_obj = condition.get('code', {})
            codings = code_obj.get('coding', [])
            
            for coding in codings:
                code = coding.get('code', '')
                if code in BILATERAL_MASTECTOMY_CODES:
                    bilateral_count += 1
                elif code in UNILATERAL_MASTECTOMY_CODES:
                    unilateral_count += 1
        
        return bilateral_count >= 1 or unilateral_count >= 2
    
    def has_qualifying_mammogram(self, patient_id: str) -> Tuple[bool, List[dict]]:
        """
        Check if patient has at least one mammogram during measurement period.
        Returns: (has_mammogram, list of qualifying claims)
        """
        # Query claims for this patient
        params = {
            'patient': patient_id,
            '_count': '200'
        }
        bundle = self.query_fhir('Claim', params)
        
        if 'error' in bundle or 'entry' not in bundle:
            return False, []
        
        qualifying_claims = []
        
        for entry in bundle.get('entry', []):
            claim = entry.get('resource', {})
            
            # Check if claim has mammography code
            has_mammo_code = False
            items = claim.get('item', [])
            
            for item in items:
                service = item.get('productOrService', {})
                codings = service.get('coding', [])
                
                for coding in codings:
                    code = coding.get('code', '')
                    if code in MAMMOGRAPHY_CODES:
                        has_mammo_code = True
                        break
                
                if has_mammo_code:
                    break
            
            if not has_mammo_code:
                continue
            
            # Check if claim is within measurement period
            created_str = claim.get('created', '')
            if created_str:
                try:
                    # Parse the date and remove timezone for comparison
                    created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    # Remove timezone for comparison with measurement period
                    created_date_naive = created_date.replace(tzinfo=None)
                    if self.measurement_start <= created_date_naive <= self.measurement_end:
                        qualifying_claims.append({
                            'claim_id': claim.get('id'),
                            'date': created_str,
                            'patient': patient_id
                        })
                except (ValueError, AttributeError):
                    pass
        
        return len(qualifying_claims) > 0, qualifying_claims
    
    def evaluate_patients(self, max_patients: int = 1000) -> Dict[str, Any]:
        """
        Evaluate measure for a sample of patients.
        Returns measure results with numerator, denominator, and rate.
        """
        # Query female patients (since we need women 50-74)
        params = {
            'gender': 'female',
            '_count': str(max_patients)
        }
        
        bundle = self.query_fhir('Patient', params)
        
        if 'error' in bundle:
            return {'error': bundle['error']}
        
        if 'entry' not in bundle:
            return {
                'numerator': 0,
                'denominator': 0,
                'exclusions': 0,
                'rate': 0.0,
                'measurement_period': {
                    'start': self.measurement_start.isoformat(),
                    'end': self.measurement_end.isoformat()
                },
                'note': 'No patients found'
            }
        
        patients = [entry.get('resource', {}) for entry in bundle.get('entry', [])]
        
        # Evaluate each patient
        initial_population = []
        denominator = []
        exclusions = []
        numerator = []
        gap_in_care = []
        
        for patient in patients:
            patient_id = patient.get('id', '')
            patient_ref = f"Patient/{patient_id}"
            
            # Check initial population
            if not self.is_in_initial_population(patient):
                continue
            
            initial_population.append(patient_ref)
            
            # Check exclusions
            if self.has_exclusion(patient_ref):
                exclusions.append(patient_ref)
                continue
            
            # Patient is in denominator
            denominator.append(patient_ref)
            
            # Check numerator (has qualifying mammogram)
            has_mammo, qualifying_claims = self.has_qualifying_mammogram(patient_ref)
            
            if has_mammo:
                numerator.append({
                    'patient': patient_ref,
                    'name': f"{patient.get('name', [{}])[0].get('given', [''])[0]} {patient.get('name', [{}])[0].get('family', '')}",
                    'birth_date': patient.get('birthDate', ''),
                    'age': self.get_patient_age(patient.get('birthDate', '')),
                    'qualifying_claims': qualifying_claims
                })
            else:
                gap_in_care.append({
                    'patient': patient_ref,
                    'name': f"{patient.get('name', [{}])[0].get('given', [''])[0]} {patient.get('name', [{}])[0].get('family', '')}",
                    'birth_date': patient.get('birthDate', ''),
                    'age': self.get_patient_age(patient.get('birthDate', ''))
                })
        
        # Calculate rate
        denominator_count = len(denominator)
        numerator_count = len(numerator)
        rate = (numerator_count / denominator_count * 100) if denominator_count > 0 else 0.0
        
        return {
            'measure_name': 'HEDIS Breast Cancer Screening (BCS)',
            'measurement_period': {
                'start': self.measurement_start.strftime('%Y-%m-%d'),
                'end': self.measurement_end.strftime('%Y-%m-%d')
            },
            'initial_population': len(initial_population),
            'denominator': denominator_count,
            'numerator': numerator_count,
            'exclusions': len(exclusions),
            'rate': round(rate, 2),
            'rate_display': f"{round(rate, 2)}%",
            'numerator_patients': numerator[:10],  # Sample of compliant patients
            'gap_in_care': gap_in_care[:20],  # Sample of patients needing screening
            'gap_in_care_count': len(gap_in_care),
            'sample_size': len(patients),
            'note': f'Evaluated {len(patients)} female patients'
        }


def calculate_hedis_bcs_measure(fhir_base_url: str = "http://hapi-fhir:8080/fhir", 
                                 max_patients: int = 1000) -> Dict[str, Any]:
    """
    Calculate HEDIS Breast Cancer Screening measure.
    
    Args:
        fhir_base_url: Base URL of FHIR server
        max_patients: Maximum number of patients to evaluate
    
    Returns:
        Dictionary with measure results
    """
    calculator = HEDISBreastCancerScreening(fhir_base_url)
    return calculator.evaluate_patients(max_patients)
