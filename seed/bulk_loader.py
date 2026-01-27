"""
High-performance bulk loader for FHIR claims with delta/incremental update support.
Handles hundreds of thousands of claims with batching, parallel processing, and progress tracking.
"""
import json
import requests
import time
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict


class BulkClaimLoader:
    def __init__(self, fhir_base, batch_size=100, workers=4, max_retries=3):
        self.fhir_base = fhir_base.rstrip('/')
        self.batch_size = batch_size
        self.workers = workers
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/fhir+json'})
        
        # Tracking
        self.stats = defaultdict(int)
        self.errors = []
        self.start_time = None
        
    def wait_for_server(self, timeout=60):
        """Wait for FHIR server to be ready."""
        print(f"Waiting for FHIR server at {self.fhir_base}...")
        endpoints = ['/metadata', '/Patient?_count=1']
        
        for attempt in range(timeout // 2):
            try:
                for endpoint in endpoints:
                    resp = self.session.get(f"{self.fhir_base}{endpoint}", timeout=5)
                    if resp.status_code not in [200, 404]:
                        raise Exception(f"Unexpected status: {resp.status_code}")
                print("✓ FHIR server is ready")
                return True
            except Exception as e:
                if attempt % 5 == 0:
                    print(f"  Waiting... ({attempt * 2}s elapsed)")
                time.sleep(2)
        
        raise Exception(f"FHIR server not ready after {timeout}s")
    
    def create_resource(self, resource_type, resource_id, body, retries=0):
        """Create or update a resource using PUT (upsert)."""
        url = f"{self.fhir_base}/{resource_type}/{resource_id}"
        
        try:
            resp = self.session.put(url, json=body, timeout=30)
            
            if resp.status_code in [200, 201]:
                return True
            elif resp.status_code == 429 and retries < self.max_retries:
                # Rate limited, wait and retry
                time.sleep(2 ** retries)
                return self.create_resource(resource_type, resource_id, body, retries + 1)
            else:
                self.errors.append({
                    'resource': f"{resource_type}/{resource_id}",
                    'status': resp.status_code,
                    'error': resp.text[:200]
                })
                return False
        except Exception as e:
            if retries < self.max_retries:
                time.sleep(2 ** retries)
                return self.create_resource(resource_type, resource_id, body, retries + 1)
            else:
                self.errors.append({
                    'resource': f"{resource_type}/{resource_id}",
                    'error': str(e)
                })
                return False
    
    def post_claim(self, claim, retries=0):
        """Post a claim resource."""
        url = f"{self.fhir_base}/Claim"
        
        try:
            resp = self.session.post(url, json=claim, timeout=30)
            
            if resp.status_code in [200, 201]:
                return True
            elif resp.status_code == 429 and retries < self.max_retries:
                time.sleep(2 ** retries)
                return self.post_claim(claim, retries + 1)
            else:
                self.errors.append({
                    'resource': 'Claim',
                    'status': resp.status_code,
                    'error': resp.text[:200]
                })
                return False
        except Exception as e:
            if retries < self.max_retries:
                time.sleep(2 ** retries)
                return self.post_claim(claim, retries + 1)
            else:
                self.errors.append({
                    'resource': 'Claim',
                    'error': str(e)
                })
                return False
    
    def create_patient(self, patient_data):
        """Create a patient resource."""
        patient_id = patient_data['id']
        
        patient = {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [{
                "use": "official",
                "family": patient_data['last'],
                "given": [patient_data['first']]
            }],
            "gender": "male" if patient_data['gender'] == 'M' else "female",
            "birthDate": patient_data['birth_date'],
            "address": [{
                "use": "home",
                "city": patient_data['city'],
                "state": patient_data['state'],
                "country": "USA"
            }]
        }
        
        if self.create_resource("Patient", patient_id, patient):
            self.stats['patients_created'] += 1
            return True
        return False
    
    def create_practitioner(self, prac_id):
        """Create a practitioner resource."""
        practitioner = {
            "resourceType": "Practitioner",
            "id": prac_id,
            "name": [{
                "family": f"Provider-{prac_id.split('-')[1]}",
                "given": ["Dr."]
            }],
            "qualification": [{
                "code": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0360",
                        "code": "MD"
                    }]
                }
            }]
        }
        
        if self.create_resource("Practitioner", prac_id, practitioner):
            self.stats['practitioners_created'] += 1
            return True
        return False
    
    def create_coverage(self, coverage_id, patient_id, plan_name):
        """Create a coverage resource."""
        coverage = {
            "resourceType": "Coverage",
            "id": coverage_id,
            "status": "active",
            "beneficiary": {
                "reference": f"Patient/{patient_id}"
            },
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "HIP",
                    "display": plan_name
                }]
            },
            "subscriber": {
                "reference": f"Patient/{patient_id}"
            }
        }
        
        if self.create_resource("Coverage", coverage_id, coverage):
            self.stats['coverage_created'] += 1
            return True
        return False
    
    def process_claim_batch(self, claims_batch):
        """Process a batch of claims with their dependencies."""
        # Extract unique patients, practitioners, and coverage
        patients_needed = {}
        practitioners_needed = set()
        coverage_needed = {}
        
        for claim in claims_batch:
            metadata = claim.get('_metadata', {})
            patient_id = metadata.get('patient_id')
            
            if patient_id and patient_id not in patients_needed:
                patients_needed[patient_id] = {
                    'id': patient_id,
                    'name': claim['patient']['display'],
                    'first': claim['patient']['display'].split()[0],
                    'last': claim['patient']['display'].split()[-1],
                    'gender': metadata.get('gender', 'M'),
                    'birth_date': '1980-01-01',  # Default
                    'city': metadata.get('city', 'Unknown'),
                    'state': metadata.get('state', 'XX'),
                    'insurance': claim['insurance'][0]['coverage']['display']
                }
            
            # Extract practitioner
            prac_ref = claim.get('provider', {}).get('reference', '')
            if prac_ref:
                prac_id = prac_ref.split('/')[-1]
                practitioners_needed.add(prac_id)
            
            # Extract coverage
            for ins in claim.get('insurance', []):
                cov_ref = ins.get('coverage', {}).get('reference', '')
                if cov_ref:
                    cov_id = cov_ref.split('/')[-1]
                    if cov_id not in coverage_needed:
                        coverage_needed[cov_id] = {
                            'patient_id': patient_id,
                            'plan_name': ins['coverage'].get('display', 'Unknown Plan')
                        }
        
        # Create dependent resources
        for patient_data in patients_needed.values():
            self.create_patient(patient_data)
        
        for prac_id in practitioners_needed:
            self.create_practitioner(prac_id)
        
        for cov_id, cov_data in coverage_needed.items():
            self.create_coverage(cov_id, cov_data['patient_id'], cov_data['plan_name'])
        
        # Post claims
        for claim in claims_batch:
            # Remove metadata before posting
            clean_claim = {k: v for k, v in claim.items() if k != '_metadata'}
            if self.post_claim(clean_claim):
                self.stats['claims_created'] += 1
    
    def load_claims(self, claims, skip_existing=False):
        """Load claims in batches with parallel processing."""
        self.start_time = time.time()
        total_claims = len(claims)
        
        print(f"\nLoading {total_claims:,} claims...")
        print(f"Batch size: {self.batch_size}, Workers: {self.workers}")
        
        # Split into batches
        batches = [claims[i:i + self.batch_size] for i in range(0, len(claims), self.batch_size)]
        
        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self.process_claim_batch, batch): i 
                      for i, batch in enumerate(batches)}
            
            for i, future in enumerate(as_completed(futures)):
                try:
                    future.result()
                except Exception as e:
                    import traceback
                    print(f"Batch error: {e}")
                    if self.workers <= 2:  # Only print traceback in low concurrency mode
                        print(f"  Error details: {traceback.format_exc()}")
                
                # Progress reporting
                processed = (i + 1) * self.batch_size
                if processed % (self.batch_size * 10) == 0 or processed >= total_claims:
                    elapsed = time.time() - self.start_time
                    rate = self.stats['claims_created'] / elapsed if elapsed > 0 else 0
                    print(f"  Processed {min(processed, total_claims):,}/{total_claims:,} claims "
                          f"({rate:.1f} claims/sec)")
        
        self.print_summary()
    
    def load_delta(self, new_claims_file, existing_hash_file=None):
        """Load only new or changed claims (delta update)."""
        print("\n=== Delta Load Mode ===")
        
        # Load new claims
        with open(new_claims_file, 'r') as f:
            new_claims = json.load(f)
        
        # Load existing hashes if available
        existing_hashes = {}
        if existing_hash_file and Path(existing_hash_file).exists():
            with open(existing_hash_file, 'r') as f:
                existing_hashes = json.load(f)
            print(f"Loaded {len(existing_hashes):,} existing claim hashes")
        
        # Compute hashes for new claims
        new_hashes = {}
        claims_to_load = []
        
        for claim in new_claims:
            # Create hash from claim content (excluding metadata)
            claim_content = {k: v for k, v in claim.items() if k != '_metadata'}
            claim_str = json.dumps(claim_content, sort_keys=True)
            claim_hash = hashlib.sha256(claim_str.encode()).hexdigest()
            
            # Use patient + created date as key
            key = f"{claim['patient']['reference']}_{claim['created']}"
            new_hashes[key] = claim_hash
            
            # Include if new or changed
            if key not in existing_hashes or existing_hashes[key] != claim_hash:
                claims_to_load.append(claim)
        
        print(f"New/changed claims: {len(claims_to_load):,} out of {len(new_claims):,}")
        
        if claims_to_load:
            self.load_claims(claims_to_load)
            
            # Save updated hashes
            hash_file = Path(new_claims_file).with_suffix('.hashes.json')
            with open(hash_file, 'w') as f:
                json.dump(new_hashes, f)
            print(f"✓ Updated hashes saved to {hash_file}")
        else:
            print("No new claims to load")
    
    def print_summary(self):
        """Print loading summary."""
        elapsed = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print("LOAD SUMMARY")
        print("=" * 60)
        print(f"Claims created:        {self.stats['claims_created']:,}")
        print(f"Patients created:      {self.stats['patients_created']:,}")
        print(f"Practitioners created: {self.stats['practitioners_created']:,}")
        print(f"Coverage created:      {self.stats['coverage_created']:,}")
        print(f"Errors:                {len(self.errors):,}")
        print(f"Elapsed time:          {elapsed:.1f}s")
        print(f"Average rate:          {self.stats['claims_created'] / elapsed:.1f} claims/sec")
        print("=" * 60)
        
        if self.errors and len(self.errors) <= 10:
            print("\nErrors:")
            for error in self.errors[:10]:
                print(f"  {error}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bulk load FHIR claims')
    parser.add_argument('claims_file', help='Path to claims JSON file')
    parser.add_argument('--fhir-base', default='http://localhost:8080/fhir',
                       help='FHIR server base URL')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of claims per batch')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of parallel workers')
    parser.add_argument('--no-wait', action='store_true',
                       help='Skip waiting for server')
    parser.add_argument('--delta', action='store_true',
                       help='Load only new/changed claims')
    parser.add_argument('--hash-file', help='Existing hash file for delta mode')
    
    args = parser.parse_args()
    
    loader = BulkClaimLoader(
        fhir_base=args.fhir_base,
        batch_size=args.batch_size,
        workers=args.workers
    )
    
    if not args.no_wait:
        loader.wait_for_server()
    
    if args.delta:
        loader.load_delta(args.claims_file, args.hash_file)
    else:
        with open(args.claims_file, 'r') as f:
            claims = json.load(f)
        loader.load_claims(claims)
