#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from typing import Dict, Any, Optional

import requests

DEFAULT_FHIR_BASE = os.environ.get("FHIR_BASE", "http://localhost:8080/fhir")
CLAIMS_PATH_DEFAULT = os.environ.get(
    "CLAIMS_PATH",
    "/home/slanders/AI/HealthClaims/embeddings_test/fhir_claims_1000.json",
)

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/fhir+json"})


def wait_for_metadata(base_url: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    md_url = f"{base_url.rstrip('/')}/metadata"
    ping_url = f"{base_url.rstrip('/')}/Patient?_count=1"
    health_url = f"{base_url.rstrip('/')}/actuator/health"
    while time.time() < deadline:
        try:
            r = SESSION.get(md_url, timeout=8)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        try:
            r2 = SESSION.get(ping_url, timeout=8)
            if r2.status_code == 200:
                return True
        except requests.RequestException:
            pass
        try:
            r3 = SESSION.get(health_url, timeout=8)
            if r3.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


def ensure_resource(resource_type: str, resource_id: str, body: Dict[str, Any]) -> str:
    """
    Create or upsert a resource using PUT to allow client-defined IDs.
    Returns the full reference string (e.g., "Patient/patient-123").
    """
    url = f"{DEFAULT_FHIR_BASE.rstrip('/')}/{resource_type}/{resource_id}"
    r = SESSION.put(url, data=json.dumps(body))
    if r.status_code not in (200, 201):
        print(f"WARN: Failed to upsert {resource_type}/{resource_id}: {r.status_code} {r.text[:200]}")
    return f"{resource_type}/{resource_id}"


def upsert_patient_from_name(name: str) -> str:
    # Deterministic ID from name
    safe = name.strip().lower().replace(" ", "-")
    patient_id = f"patient-{safe}"
    body = {
        "resourceType": "Patient",
        "id": patient_id,
        "name": [{"text": name}],
    }
    return ensure_resource("Patient", patient_id, body)


def upsert_practitioner(pract_ref: str) -> str:
    # Expect format "Practitioner/<id>"
    if not pract_ref.startswith("Practitioner/"):
        pract_id = pract_ref.strip().lower().replace(" ", "-")
        pract_ref = f"Practitioner/{pract_id}"
    pract_id = pract_ref.split("/", 1)[1]
    body = {
        "resourceType": "Practitioner",
        "id": pract_id,
        "name": [{"text": pract_id}],
    }
    return ensure_resource("Practitioner", pract_id, body)


def upsert_coverage_for_patient(patient_ref: str, plan_name: str) -> str:
    # Deterministic coverage id from patient + plan name
    safe_plan = plan_name.strip().lower().replace(" ", "-") if plan_name else "unknown"
    cov_id = f"cov-{patient_ref.split('/', 1)[1]}-{safe_plan}"
    body = {
        "resourceType": "Coverage",
        "id": cov_id,
        "status": "active",
        "beneficiary": {"reference": patient_ref},
        "type": {"text": plan_name or "Standard Plan"},
    }
    return ensure_resource("Coverage", cov_id, body)


def transform_claim(raw_claim: Dict[str, Any]) -> Dict[str, Any]:
    claim = dict(raw_claim)  # shallow copy

    # Patient reference
    patient_name = raw_claim.get("patient", {}).get("display") or "Demo Patient"
    patient_ref = upsert_patient_from_name(patient_name)
    claim["patient"] = {"reference": patient_ref, "display": patient_name}

    # Practitioner (provider)
    provider_ref = raw_claim.get("provider", {}).get("reference") or "Practitioner/prov-demo"
    provider_ref = upsert_practitioner(provider_ref)
    claim["provider"] = {"reference": provider_ref}

    # Coverage in insurance
    coverage_display = None
    insurance = raw_claim.get("insurance") or []
    if insurance:
        coverage_display = insurance[0].get("coverage", {}).get("display")
    cov_ref = upsert_coverage_for_patient(patient_ref, coverage_display or "Standard Health Plan")
    if insurance:
        insurance[0]["coverage"] = {"reference": cov_ref, "display": coverage_display or "Standard Health Plan"}
        claim["insurance"] = insurance

    # Ensure resourceType and status
    claim["resourceType"] = "Claim"
    claim.setdefault("status", "active")
    return claim


def post_claim(claim: Dict[str, Any]) -> Optional[str]:
    url = f"{DEFAULT_FHIR_BASE.rstrip('/')}/Claim"
    r = SESSION.post(url, data=json.dumps(claim))
    if r.status_code in (200, 201):
        try:
            created = r.json()
            return created.get("id")
        except Exception:
            return None
    else:
        print(f"ERROR: Failed to create Claim: {r.status_code} {r.text[:300]}")
        return None


def bulk_seed(claims_path: str, limit: Optional[int] = None, start: int = 0) -> None:
    print(f"FHIR base: {DEFAULT_FHIR_BASE}")
    if not wait_for_metadata(DEFAULT_FHIR_BASE, timeout=90):
        print("ERROR: FHIR server not ready (metadata check failed)")
        sys.exit(2)

    with open(claims_path, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("ERROR: Claims file must be a JSON array of Claim resources")
        sys.exit(1)

    total = len(data)
    end = min(total, start + (limit or total))
    count_ok = 0

    for i in range(start, end):
        raw = data[i]
        try:
            claim = transform_claim(raw)
            claim_id = post_claim(claim)
            if claim_id:
                count_ok += 1
                if count_ok % 50 == 0:
                    print(f"Seeded {count_ok} claims...")
            else:
                print(f"WARN: Claim at index {i} failed to create")
        except Exception as e:
            print(f"WARN: Exception seeding claim {i}: {e}")

    print(f"Done. Seeded {count_ok}/{end - start} claims from {claims_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk seed demo health claims into HAPI FHIR")
    parser.add_argument("--fhir-base", dest="fhir_base", default=DEFAULT_FHIR_BASE, help="FHIR base URL, default env FHIR_BASE")
    parser.add_argument("--claims", dest="claims_path", default=CLAIMS_PATH_DEFAULT, help="Path to JSON array of Claim resources")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of claims to import")
    parser.add_argument("--start", type=int, default=0, help="Start index within the array")
    parser.add_argument("--no-wait", action="store_true", help="Skip waiting for server readiness")
    args = parser.parse_args()

    # Allow override at runtime
    if args.fhir_base:
        DEFAULT_FHIR_BASE = args.fhir_base

    # Optionally skip readiness wait by short-circuiting
    if args.no_wait:
        # Proceed without readiness check; set timeout to 0 by temporarily overriding function
        def _no_wait(_base: str, timeout: int = 0) -> bool:
            return True
        wait_for_metadata = _no_wait  # type: ignore

    bulk_seed(args.claims_path, limit=args.limit, start=args.start)
