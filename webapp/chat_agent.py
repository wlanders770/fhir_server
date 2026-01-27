"""
FHIR Chat Agent - AI Assistant for Claims Data Analysis

This module provides a conversational AI agent that can:
- Query FHIR claims data
- Generate charts and visualizations
- Export data to spreadsheets (CSV/Excel)
- Answer questions about claims, patients, and procedures
- Understand medical terminology and synonyms
- Optional LLM integration for better query understanding
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import csv
import io
from collections import defaultdict, Counter
import re
import os


class FHIRChatAgent:
    """
    Chat agent for FHIR claims data with tool-calling capabilities.
    """
    
    def __init__(self, fhir_base_url: str = "http://hapi-fhir:8080/fhir", 
                 ollama_base_url: str = None):
        self.fhir_base_url = fhir_base_url
        self.ollama_base_url = ollama_base_url or os.getenv('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
        self.conversation_history = []
        self.use_llm = True  # Try to use LLM if available
        
        # Medical terminology mappings
        self.medical_synonyms = {
            'breast cancer screening': ['mammogram', 'mammography', '77065', '77066', '77067'],
            'breast cancer': ['mammogram', 'mammography', '77065', '77066', '77067'],
            'mammogram': ['mammography', '77065', '77066', '77067'],
            'mammography': ['mammogram', '77065', '77066', '77067'],
            'screening': ['preventive', 'check', 'test'],
            'hedis': ['quality measure', 'bcs', 'breast cancer screening'],
        }
        
        # Available tools for the agent
        self.tools = {
            'query_claims': self.query_claims,
            'query_patients': self.query_patients,
            'aggregate_claims': self.aggregate_claims,
            'generate_csv': self.generate_csv,
            'get_claim_statistics': self.get_claim_statistics,
            'search_by_procedure': self.search_by_procedure,
            'search_by_diagnosis': self.search_by_diagnosis,
            'get_top_procedures': self.get_top_procedures,
            'get_monthly_trends': self.get_monthly_trends,
            'get_patient_claims': self.get_patient_claims,
            'get_mammogram_stats': self.get_mammogram_stats,
            'get_hedis_measure': self.get_hedis_measure,
        }
    
    def query_fhir(self, resource_type: str, params: dict = None) -> dict:
        """Query FHIR server."""
        try:
            response = requests.get(
                f"{self.fhir_base_url}/{resource_type}",
                params=params or {},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    def extract_resources(self, bundle: dict) -> List[dict]:
        """Extract resources from FHIR bundle."""
        if 'entry' not in bundle:
            return []
        return [entry.get('resource', {}) for entry in bundle['entry']]
    
    # Tool implementations
    
    def query_claims(self, status: str = None, start_date: str = None, 
                     end_date: str = None, max_count: int = 100) -> Dict[str, Any]:
        """
        Query claims with filters.
        
        Args:
            status: Claim status (active, cancelled, etc.)
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            max_count: Maximum number of claims to return
        """
        params = {'_count': str(max_count)}
        
        if status:
            params['status'] = status
        
        bundle = self.query_fhir('Claim', params)
        claims = self.extract_resources(bundle)
        
        # Apply date filtering if needed
        if start_date or end_date:
            filtered = []
            for claim in claims:
                created = claim.get('created', '')
                if created:
                    claim_date = created.split('T')[0]
                    if start_date and claim_date < start_date:
                        continue
                    if end_date and claim_date > end_date:
                        continue
                    filtered.append(claim)
            claims = filtered
        
        return {
            'count': len(claims),
            'claims': claims[:max_count],
            'summary': f"Found {len(claims)} claims"
        }
    
    def query_patients(self, gender: str = None, max_count: int = 100) -> Dict[str, Any]:
        """Query patients with filters."""
        params = {'_count': str(max_count)}
        
        if gender:
            params['gender'] = gender
        
        bundle = self.query_fhir('Patient', params)
        patients = self.extract_resources(bundle)
        
        return {
            'count': len(patients),
            'patients': patients,
            'summary': f"Found {len(patients)} patients"
        }
    
    def aggregate_claims(self, group_by: str = 'month') -> Dict[str, Any]:
        """
        Aggregate claims data.
        
        Args:
            group_by: 'month', 'status', 'procedure', or 'cost'
        """
        params = {'_count': '500'}
        bundle = self.query_fhir('Claim', params)
        claims = self.extract_resources(bundle)
        
        if group_by == 'month':
            by_month = defaultdict(int)
            for claim in claims:
                created = claim.get('created', '')
                if created:
                    month = created[:7]  # YYYY-MM
                    by_month[month] += 1
            return {
                'aggregation': 'by_month',
                'data': dict(sorted(by_month.items())),
                'summary': f"Claims by month ({len(by_month)} months)"
            }
        
        elif group_by == 'status':
            by_status = Counter(claim.get('status', 'unknown') for claim in claims)
            return {
                'aggregation': 'by_status',
                'data': dict(by_status),
                'summary': f"Claims by status ({len(by_status)} statuses)"
            }
        
        elif group_by == 'procedure':
            procedures = Counter()
            for claim in claims:
                for item in claim.get('item', []):
                    service = item.get('productOrService', {})
                    for coding in service.get('coding', []):
                        display = coding.get('display', 'Unknown')
                        procedures[display] += 1
            return {
                'aggregation': 'by_procedure',
                'data': dict(procedures.most_common(20)),
                'summary': f"Top 20 procedures from {len(claims)} claims"
            }
        
        elif group_by == 'cost':
            total = 0
            by_month = defaultdict(float)
            for claim in claims:
                amount = claim.get('total', {}).get('value', 0)
                total += amount
                created = claim.get('created', '')
                if created:
                    month = created[:7]
                    by_month[month] += amount
            return {
                'aggregation': 'cost_by_month',
                'total_cost': total,
                'data': dict(sorted(by_month.items())),
                'summary': f"Total cost: ${total:,.2f} across {len(by_month)} months"
            }
        
        return {'error': f'Unknown aggregation: {group_by}'}
    
    def get_claim_statistics(self) -> Dict[str, Any]:
        """Get overall claim statistics."""
        params = {'_count': '1', '_summary': 'count'}
        bundle = self.query_fhir('Claim', params)
        total_claims = bundle.get('total', 0)
        
        # Get sample for statistics
        sample_bundle = self.query_fhir('Claim', {'_count': '500'})
        claims = self.extract_resources(sample_bundle)
        
        total_cost = sum(c.get('total', {}).get('value', 0) for c in claims)
        avg_cost = total_cost / len(claims) if claims else 0
        
        status_dist = Counter(c.get('status', 'unknown') for c in claims)
        
        return {
            'total_claims': total_claims,
            'sample_size': len(claims),
            'total_cost_sample': total_cost,
            'average_cost': avg_cost,
            'status_distribution': dict(status_dist),
            'summary': f"{total_claims:,} total claims, ${avg_cost:.2f} avg cost"
        }
    
    def search_by_procedure(self, procedure_code: str = None, 
                            procedure_name: str = None) -> Dict[str, Any]:
        """Search claims by procedure code or name."""
        params = {'_count': '200'}
        bundle = self.query_fhir('Claim', params)
        claims = self.extract_resources(bundle)
        
        matching = []
        for claim in claims:
            for item in claim.get('item', []):
                service = item.get('productOrService', {})
                for coding in service.get('coding', []):
                    code = coding.get('code', '')
                    display = coding.get('display', '').lower()
                    
                    if procedure_code and code == procedure_code:
                        matching.append(claim)
                        break
                    elif procedure_name and procedure_name.lower() in display:
                        matching.append(claim)
                        break
        
        return {
            'count': len(matching),
            'claims': matching,
            'summary': f"Found {len(matching)} claims for procedure"
        }
    
    def search_by_diagnosis(self, diagnosis_code: str) -> Dict[str, Any]:
        """Search claims by diagnosis code."""
        params = {'_count': '200'}
        bundle = self.query_fhir('Claim', params)
        claims = self.extract_resources(bundle)
        
        matching = []
        for claim in claims:
            for diagnosis in claim.get('diagnosis', []):
                for coding in diagnosis.get('diagnosisCodeableConcept', {}).get('coding', []):
                    if coding.get('code') == diagnosis_code:
                        matching.append(claim)
                        break
        
        return {
            'count': len(matching),
            'claims': matching,
            'summary': f"Found {len(matching)} claims with diagnosis {diagnosis_code}"
        }
    
    def get_top_procedures(self, limit: int = 10) -> Dict[str, Any]:
        """Get top procedures by frequency."""
        params = {'_count': '500'}
        bundle = self.query_fhir('Claim', params)
        claims = self.extract_resources(bundle)
        
        procedures = Counter()
        for claim in claims:
            for item in claim.get('item', []):
                service = item.get('productOrService', {})
                for coding in service.get('coding', []):
                    code = coding.get('code', '')
                    display = coding.get('display', 'Unknown')
                    procedures[f"{code} - {display}"] += 1
        
        top = procedures.most_common(limit)
        
        return {
            'top_procedures': [{'procedure': p, 'count': c} for p, c in top],
            'summary': f"Top {limit} procedures from {len(claims)} claims"
        }
    
    def get_monthly_trends(self, months: int = 12) -> Dict[str, Any]:
        """Get monthly trends for claims and costs."""
        params = {'_count': '1000'}
        bundle = self.query_fhir('Claim', params)
        claims = self.extract_resources(bundle)
        
        by_month = defaultdict(lambda: {'count': 0, 'cost': 0})
        
        for claim in claims:
            created = claim.get('created', '')
            if created:
                month = created[:7]
                by_month[month]['count'] += 1
                by_month[month]['cost'] += claim.get('total', {}).get('value', 0)
        
        sorted_months = sorted(by_month.items(), reverse=True)[:months]
        
        return {
            'trends': [
                {
                    'month': month,
                    'claim_count': data['count'],
                    'total_cost': data['cost'],
                    'avg_cost': data['cost'] / data['count'] if data['count'] > 0 else 0
                }
                for month, data in sorted_months
            ],
            'summary': f"Monthly trends for last {len(sorted_months)} months"
        }
    
    def get_mammogram_stats(self) -> Dict[str, Any]:
        """Get mammogram-specific statistics."""
        # Define mammogram CPT codes
        mammo_codes = ['77065', '77066', '77067', '77063', '77061', '77062']
        
        # Sort by most recent to get newly created mammogram claims
        params = {
            '_count': '1000',
            '_sort': '-_lastUpdated'
        }
        bundle = self.query_fhir('Claim', params)
        claims = self.extract_resources(bundle)
        
        # Filter for mammogram claims
        mammo_claims = []
        for claim in claims:
            for item in claim.get('item', []):
                service = item.get('productOrService', {})
                for coding in service.get('coding', []):
                    if coding.get('code') in mammo_codes:
                        mammo_claims.append(claim)
                        break
        
        if not mammo_claims:
            return {
                'count': 0,
                'summary': 'No mammogram claims found in sample'
            }
        
        # Calculate statistics
        total_cost = sum(c.get('total', {}).get('value', 0) for c in mammo_claims)
        avg_cost = total_cost / len(mammo_claims) if mammo_claims else 0
        
        # Count by procedure
        by_procedure = Counter()
        for claim in mammo_claims:
            for item in claim.get('item', []):
                service = item.get('productOrService', {})
                for coding in service.get('coding', []):
                    if coding.get('code') in mammo_codes:
                        display = coding.get('display', 'Unknown')
                        by_procedure[display] += 1
        
        # Count by month
        by_month = defaultdict(int)
        for claim in mammo_claims:
            created = claim.get('created', '')
            if created:
                month = created[:7]
                by_month[month] += 1
        
        return {
            'count': len(mammo_claims),
            'total_cost': total_cost,
            'average_cost': avg_cost,
            'by_procedure': dict(by_procedure),
            'by_month': dict(sorted(by_month.items())),
            'summary': f"Found {len(mammo_claims)} mammogram claims, ${avg_cost:.2f} avg cost"
        }
    
    def get_hedis_measure(self, max_patients: int = 100) -> Dict[str, Any]:
        """Get HEDIS Breast Cancer Screening measure results."""
        try:
            # Import here to avoid circular dependency
            from hedis_measure import calculate_hedis_bcs_measure
            
            result = calculate_hedis_bcs_measure(
                fhir_base_url=self.fhir_base_url,
                max_patients=max_patients
            )
            
            return {
                'measure': result,
                'summary': f"HEDIS BCS: {result['rate_display']} compliance ({result['numerator']}/{result['denominator']} eligible patients)"
            }
        except Exception as e:
            return {
                'error': str(e),
                'summary': f"Failed to calculate HEDIS measure: {str(e)}"
            }
    
    def get_patient_claims(self, patient_id: str) -> Dict[str, Any]:
        """Get all claims for a specific patient."""
        params = {
            'patient': f"Patient/{patient_id}",
            '_count': '100'
        }
        bundle = self.query_fhir('Claim', params)
        claims = self.extract_resources(bundle)
        
        total_cost = sum(c.get('total', {}).get('value', 0) for c in claims)
        
        return {
            'patient_id': patient_id,
            'claim_count': len(claims),
            'total_cost': total_cost,
            'claims': claims,
            'summary': f"{len(claims)} claims totaling ${total_cost:,.2f}"
        }
    
    def generate_csv(self, data_type: str = 'claims', filters: dict = None) -> str:
        """
        Generate CSV export of claims data.
        
        Args:
            data_type: 'claims', 'patients', or 'summary'
            filters: Optional filters to apply
        """
        output = io.StringIO()
        
        if data_type == 'claims':
            params = {'_count': '500'}
            bundle = self.query_fhir('Claim', params)
            claims = self.extract_resources(bundle)
            
            writer = csv.writer(output)
            writer.writerow([
                'Claim ID', 'Patient', 'Status', 'Created Date', 
                'Procedure Code', 'Procedure', 'Total Amount'
            ])
            
            for claim in claims:
                claim_id = claim.get('id', '')
                patient = claim.get('patient', {}).get('reference', '')
                status = claim.get('status', '')
                created = claim.get('created', '')
                
                items = claim.get('item', [])
                if items:
                    item = items[0]
                    service = item.get('productOrService', {})
                    coding = service.get('coding', [{}])[0]
                    proc_code = coding.get('code', '')
                    proc_display = coding.get('display', '')
                else:
                    proc_code = ''
                    proc_display = ''
                
                amount = claim.get('total', {}).get('value', 0)
                
                writer.writerow([
                    claim_id, patient, status, created,
                    proc_code, proc_display, f"${amount:.2f}"
                ])
            
            return output.getvalue()
        
        elif data_type == 'summary':
            stats = self.get_claim_statistics()
            trends = self.get_monthly_trends()
            
            writer = csv.writer(output)
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Claims', stats['total_claims']])
            writer.writerow(['Average Cost', f"${stats['average_cost']:.2f}"])
            writer.writerow([''])
            writer.writerow(['Monthly Trends'])
            writer.writerow(['Month', 'Claims', 'Total Cost', 'Avg Cost'])
            
            for trend in trends['trends']:
                writer.writerow([
                    trend['month'],
                    trend['claim_count'],
                    f"${trend['total_cost']:.2f}",
                    f"${trend['avg_cost']:.2f}"
                ])
            
            return output.getvalue()
        
        return "Error: Unknown data type"
    
    def call_ollama_llm(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Use Ollama LLM to interpret user query and determine intent.
        Returns None if LLM is unavailable or fails.
        """
        if not self.use_llm:
            return None
        
        try:
            # Define available tools for the LLM
            tools_description = """
Available tools:
1. get_claim_statistics - Get overall claim statistics
2. get_mammogram_stats - Get mammogram/breast cancer screening statistics  
3. get_hedis_measure - Get HEDIS Breast Cancer Screening quality measure
4. get_top_procedures - Get most common procedures
5. get_monthly_trends - Get monthly claim and cost trends
6. search_by_procedure - Search claims by procedure name
7. aggregate_claims - Aggregate claims by month/status/procedure/cost
8. generate_csv - Export data to CSV
"""
            
            prompt = f"""You are a FHIR healthcare data assistant. Analyze this user query and determine the best tool to use.

User Query: "{user_message}"

{tools_description}

Medical Context:
- "breast cancer screening" = mammogram claims (CPT 77065, 77066, 77067)
- "HEDIS" or "quality measure" = HEDIS Breast Cancer Screening measure
- "mammogram" or "mammography" = breast cancer screening claims

Respond with ONLY a JSON object:
{{
    "tool": "tool_name",
    "reasoning": "brief explanation",
    "parameters": {{}},
    "confidence": 0.9
}}

JSON Response:"""
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    intent = json.loads(json_match.group())
                    return intent
                    
        except Exception as e:
            # LLM failed, fall back to keyword matching
            print(f"LLM unavailable: {e}")
            self.use_llm = False
        
        return None
    
    def expand_medical_terms(self, message: str) -> str:
        """Expand medical terminology to include synonyms."""
        message_lower = message.lower()
        
        for term, synonyms in self.medical_synonyms.items():
            if term in message_lower:
                # Add synonyms to the search
                for synonym in synonyms:
                    if synonym not in message_lower:
                        message_lower += ' ' + synonym
        
        return message_lower
    
    def process_user_query(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user query and determine which tool(s) to use.
        Uses LLM if available, falls back to keyword matching.
        """
        # Try LLM first
        llm_intent = self.call_ollama_llm(user_message)
        
        if llm_intent and llm_intent.get('confidence', 0) > 0.7:
            tool_name = llm_intent.get('tool')
            if tool_name in self.tools:
                try:
                    result = self.tools[tool_name](**llm_intent.get('parameters', {}))
                    return {
                        'type': tool_name,
                        'data': result,
                        'message': result.get('summary', 'Query completed'),
                        'llm_reasoning': llm_intent.get('reasoning')
                    }
                except Exception as e:
                    # Fall through to keyword matching
                    pass
        
        # Fallback to keyword matching with medical term expansion
        message = self.expand_medical_terms(user_message)
        
        # Check for breast cancer screening / mammogram queries
        if any(term in message for term in ['breast cancer', 'mammogram', 'mammography', '77065', '77066', '77067']):
            # Check if asking about gaps in care, compliance, or quality measures
            if any(term in message for term in ['gap', 'need', 'missing', 'hedis', 'quality', 'measure', 'compliance', 'screening rate', 'who needs', 'eligible']):
                result = self.get_hedis_measure(max_patients=200)
                return {
                    'type': 'hedis_measure',
                    'data': result,
                    'message': result['summary']
                }
            elif any(term in message for term in ['chart', 'graph', 'trend', 'statistics', 'stats']):
                result = self.get_mammogram_stats()
                return {
                    'type': 'mammogram_stats',
                    'data': result,
                    'message': result['summary']
                }
            else:
                result = self.get_mammogram_stats()
                return {
                    'type': 'mammogram_stats',
                    'data': result,
                    'message': result['summary']
                }
        
        # CSV export
        if 'csv' in message or 'export' in message or 'spreadsheet' in message:
            if 'summary' in message:
                csv_data = self.generate_csv('summary')
                return {
                    'type': 'csv',
                    'data': csv_data,
                    'message': 'Generated summary CSV export'
                }
            else:
                csv_data = self.generate_csv('claims')
                return {
                    'type': 'csv',
                    'data': csv_data,
                    'message': 'Generated claims CSV export'
                }
        
        elif 'statistics' in message or 'stats' in message or 'overview' in message:
            stats = self.get_claim_statistics()
            return {
                'type': 'statistics',
                'data': stats,
                'message': stats['summary']
            }
        
        elif 'trend' in message or 'monthly' in message or 'by month' in message:
            trends = self.get_monthly_trends()
            return {
                'type': 'trends',
                'data': trends,
                'message': trends['summary']
            }
        
        elif 'top procedure' in message or 'most common' in message:
            top = self.get_top_procedures()
            return {
                'type': 'top_procedures',
                'data': top,
                'message': top['summary']
            }
        
        elif 'aggregate' in message or 'group by' in message:
            if 'status' in message:
                result = self.aggregate_claims('status')
            elif 'cost' in message:
                result = self.aggregate_claims('cost')
            elif 'procedure' in message:
                result = self.aggregate_claims('procedure')
            else:
                result = self.aggregate_claims('month')
            
            return {
                'type': 'aggregation',
                'data': result,
                'message': result['summary']
            }
        
        else:
            # Default: return statistics with helpful suggestions
            stats = self.get_claim_statistics()
            return {
                'type': 'statistics',
                'data': stats,
                'message': f"I found {stats['summary']}. Try asking about:\n• Breast cancer screenings or mammograms\n• HEDIS quality measures\n• Monthly trends\n• Top procedures\n• Export to CSV"
            }


def create_chat_agent(fhir_base_url: str = "http://hapi-fhir:8080/fhir", 
                      ollama_base_url: str = None) -> FHIRChatAgent:
    """Create a new chat agent instance with optional LLM integration."""
    return FHIRChatAgent(fhir_base_url, ollama_base_url)

