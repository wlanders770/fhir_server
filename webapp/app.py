"""
Flask web app for querying and visualizing FHIR claims data.
Provides REST API endpoints and serves a charting dashboard.
"""
from flask import Flask, render_template, jsonify, request, send_file
import requests
from datetime import datetime
from collections import defaultdict, Counter
import os
import io
from hedis_measure import (
    calculate_hedis_bcs_measure,
    calculate_hedis_col_measure,
    calculate_hedis_cdc_measure,
    calculate_hedis_cbp_measure
)
from chat_agent import create_chat_agent

app = Flask(__name__)

# Initialize chat agent
chat_agent = create_chat_agent()

# FHIR server base URL - configurable via environment
FHIR_BASE = os.getenv('FHIR_BASE_URL', 'http://hapi-fhir:8080/fhir')


@app.after_request
def disable_csp(response):
    """Disable Content Security Policy for development."""
    # Remove any CSP headers
    response.headers.pop('Content-Security-Policy', None)
    response.headers.pop('Content-Security-Policy-Report-Only', None)
    response.headers.pop('X-Content-Security-Policy', None)
    response.headers.pop('X-WebKit-CSP', None)
    return response


def query_fhir(resource_type, params=None):
    """Query FHIR server and return results."""
    url = f"{FHIR_BASE}/{resource_type}"
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


def extract_claims_from_bundle(bundle):
    """Extract claim resources from a FHIR Bundle."""
    if 'entry' not in bundle:
        return []
    return [entry['resource'] for entry in bundle['entry'] if entry.get('resource')]


@app.route('/')
def index():
    """Serve the main dashboard page."""
    return render_template('index.html')


@app.route('/api/claims')
def get_claims():
    """Get claims with optional filters."""
    params = {
        '_count': request.args.get('count', '100'),
        '_sort': request.args.get('sort', '-created')
    }
    
    # Optional filters
    if request.args.get('status'):
        params['status'] = request.args.get('status')
    if request.args.get('patient'):
        params['patient'] = request.args.get('patient')
    if request.args.get('created_from'):
        params['created'] = f"ge{request.args.get('created_from')}"
    if request.args.get('created_to'):
        created_param = params.get('created', '')
        params['created'] = f"{created_param}&le{request.args.get('created_to')}"
    
    bundle = query_fhir('Claim', params)
    if 'error' in bundle:
        return jsonify({'error': bundle['error']}), 500
    
    claims = extract_claims_from_bundle(bundle)
    return jsonify({
        'total': bundle.get('total', len(claims)),
        'claims': claims
    })


@app.route('/api/stats')
def get_stats():
    """Get aggregated statistics for charting."""
    try:
        # Get summary count first
        count_bundle = query_fhir('Claim', {'_summary': 'count'})
        total_claims = count_bundle.get('total', 0)
        
        # For large datasets (>10K claims), sample to avoid timeouts
        # Load enough claims to get accurate statistics without timing out
        sample_size = min(total_claims, 10000)  # Sample up to 10K claims
        all_claims = []
        params = {'_count': '1000'}
        max_pages = (sample_size // 1000) + 1  # Only load what we need
        
        for page in range(max_pages):
            bundle = query_fhir('Claim', params)
            if 'error' in bundle:
                return jsonify({'error': bundle['error']}), 500
            
            claims = extract_claims_from_bundle(bundle)
            all_claims.extend(claims)
            
            # Stop if we have enough claims for sampling
            if len(all_claims) >= sample_size:
                break
            
            # Check for next page
            links = bundle.get('link', [])
            next_link = next((l for l in links if l['relation'] == 'next'), None)
            if not next_link:
                break
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # Calculate scaling factor if we're sampling
    scaling_factor = total_claims / len(all_claims) if len(all_claims) > 0 else 1.0
    is_sampled = len(all_claims) < total_claims
    
    # Aggregate data
    stats = {
        'total_claims': len(all_claims),
        'by_status': defaultdict(int),
        'by_month': defaultdict(int),
        'by_patient': defaultdict(int),
        'top_procedures': Counter(),
        'cost_by_month': defaultdict(float),
        'total_cost': 0.0
    }
    
    for claim in all_claims:
        # Status distribution
        status = claim.get('status', 'unknown')
        stats['by_status'][status] += 1
        
        # Claims by month
        created = claim.get('created', '')
        if created:
            try:
                date_obj = datetime.fromisoformat(created.replace('Z', '+00:00'))
                month_key = date_obj.strftime('%Y-%m')
                stats['by_month'][month_key] += 1
                
                # Cost by month
                total = claim.get('total', {})
                if 'value' in total:
                    cost = float(total['value'])
                    stats['cost_by_month'][month_key] += cost
                    stats['total_cost'] += cost
            except (ValueError, AttributeError):
                pass
        
        # Patient distribution
        patient_ref = claim.get('patient', {}).get('reference', 'Unknown')
        stats['by_patient'][patient_ref] += 1
        
        # Procedures/CPT codes
        items = claim.get('item', [])
        for item in items:
            service = item.get('productOrService', {})
            codings = service.get('coding', [])
            for coding in codings:
                code = coding.get('code')
                display = coding.get('display', code)
                if code:
                    stats['top_procedures'][display] += 1
    
    # Scale up counts if we sampled the data
    if is_sampled:
        scaled_by_month = {k: int(v * scaling_factor) for k, v in stats['by_month'].items()}
        scaled_cost_by_month = {k: round(v * scaling_factor, 2) for k, v in stats['cost_by_month'].items()}
        scaled_by_status = {k: int(v * scaling_factor) for k, v in stats['by_status'].items()}
    else:
        scaled_by_month = dict(stats['by_month'])
        scaled_cost_by_month = dict(stats['cost_by_month'])
        scaled_by_status = dict(stats['by_status'])
    
    # Convert to serializable format
    return jsonify({
        'total_claims': total_claims,  # Use actual total from count query
        'total_cost': round(stats['total_cost'] * scaling_factor, 2),
        'by_status': scaled_by_status,
        'by_month': dict(sorted(scaled_by_month.items())),
        'cost_by_month': dict(sorted(scaled_cost_by_month.items())),
        'top_patients': dict(sorted(stats['by_patient'].items(), key=lambda x: x[1], reverse=True)[:10]),
        'unique_patient_count': len(stats['by_patient']),  # Total unique patients
        'top_procedures': dict(stats['top_procedures'].most_common(10)),
        'is_sampled': is_sampled,
        'sample_size': len(all_claims)
    })


@app.route('/api/mammogram-stats')
def get_mammogram_stats():
    """Get statistics specific to mammogram claims using procedure codes."""
    try:
        # Query for mammogram claims by procedure codes (770xx are mammogram CPT codes)
        # We'll sample up to 200 mammogram claims for quick stats
        all_mammo_claims = []
        mammo_patients = set()
        
        # Query recent claims, limit to 200 for fast response
        params = {
            '_count': '200',
            '_sort': '-_lastUpdated'  # Get most recent claims
        }
        
        bundle = query_fhir('Claim', params)
        if 'error' not in bundle:
            claims = extract_claims_from_bundle(bundle)
            
            # Filter for only mammogram claims (codes starting with 770)
            for claim in claims:
                items = claim.get('item', [])
                is_mammogram = False
                for item in items:
                    service = item.get('productOrService', {})
                    codings = service.get('coding', [])
                    for coding in codings:
                        code = coding.get('code', '')
                        if code.startswith('770'):  # Mammogram codes
                            is_mammogram = True
                            break
                    if is_mammogram:
                        break
                
                if is_mammogram:
                    all_mammo_claims.append(claim)
                    patient_ref = claim.get('patient', {}).get('reference', '')
                    if patient_ref:
                        mammo_patients.add(patient_ref)
        
        if not all_mammo_claims:
            return jsonify({
                'total_mammogram_claims': 0,
                'unique_patients': 0,
                'total_cost': 0.0,
                'average_cost': 0,
                'by_procedure': {},
                'by_month': {},
                'cost_by_month': {},
                'note': 'No mammogram claims found in sample'
            })
        
        # Calculate stats from sample
        procedure_counts = Counter()
        by_month = defaultdict(int)
        cost_by_month = defaultdict(float)
        total_cost = 0.0
        
        for claim in all_mammo_claims:
            # Count by procedure
            items = claim.get('item', [])
            for item in items:
                service = item.get('productOrService', {})
                codings = service.get('coding', [])
                for coding in codings:
                    code = coding.get('code')
                    display = coding.get('display', 'Unknown')
                    if code and code.startswith('770'):  # Mammogram codes
                        procedure_counts[f"{code} - {display}"] += 1
            
            # Monthly stats
            created = claim.get('created', '')
            if created:
                try:
                    date_obj = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    month_key = date_obj.strftime('%Y-%m')
                    by_month[month_key] += 1
                    
                    total = claim.get('total', {})
                    if 'value' in total:
                        cost = float(total['value'])
                        cost_by_month[month_key] += cost
                        total_cost += cost
                except (ValueError, AttributeError):
                    pass
        
        return jsonify({
            'total_mammogram_claims': len(all_mammo_claims),
            'unique_patients': len(mammo_patients),
            'total_cost': round(total_cost, 2),
            'average_cost': round(total_cost / len(all_mammo_claims), 2) if all_mammo_claims else 0,
            'by_procedure': dict(procedure_counts),
            'by_month': dict(sorted(by_month.items())),
            'cost_by_month': dict(sorted(cost_by_month.items())),
            'note': f'Sample of {len(all_mammo_claims)} most recent mammogram claims out of ~5,000 total'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/patients')
def get_patients():
    """Get list of patients."""
    params = {'_count': request.args.get('count', '50')}
    bundle = query_fhir('Patient', params)
    
    if 'error' in bundle:
        return jsonify({'error': bundle['error']}), 500
    
    patients = extract_claims_from_bundle(bundle)
    return jsonify({
        'total': bundle.get('total', len(patients)),
        'patients': patients
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        # Check if FHIR server is reachable
        response = requests.get(f"{FHIR_BASE}/metadata", timeout=5)
        fhir_status = "up" if response.status_code == 200 else "down"
    except:
        fhir_status = "down"
    
    return jsonify({
        'status': 'up',
        'fhir_server': fhir_status
    })


@app.route('/api/hedis-bcs')
def get_hedis_bcs_measure():
    """
    Calculate HEDIS Breast Cancer Screening measure.
    
    Query parameters:
    - max_patients: Maximum number of patients to evaluate (default: 500)
    """
    try:
        max_patients = int(request.args.get('max_patients', 500))
        max_patients = min(max_patients, 2000)  # Cap at 2000
        
        results = calculate_hedis_bcs_measure(FHIR_BASE, max_patients)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/hedis-col')
def get_hedis_col_measure():
    """
    Calculate HEDIS Colorectal Cancer Screening measure.
    
    Query parameters:
    - max_patients: Maximum number of patients to evaluate (default: 500)
    """
    try:
        max_patients = int(request.args.get('max_patients', 500))
        max_patients = min(max_patients, 2000)
        
        results = calculate_hedis_col_measure(FHIR_BASE, max_patients)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/hedis-cdc')
def get_hedis_cdc_measure():
    """
    Calculate HEDIS Comprehensive Diabetes Care measure.
    
    Query parameters:
    - max_patients: Maximum number of patients to evaluate (default: 500)
    """
    try:
        max_patients = int(request.args.get('max_patients', 500))
        max_patients = min(max_patients, 2000)
        
        results = calculate_hedis_cdc_measure(FHIR_BASE, max_patients)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/hedis-cbp')
def get_hedis_cbp_measure():
    """
    Calculate HEDIS Controlling High Blood Pressure measure.
    
    Query parameters:
    - max_patients: Maximum number of patients to evaluate (default: 500)
    """
    try:
        max_patients = int(request.args.get('max_patients', 500))
        max_patients = min(max_patients, 2000)
        
        results = calculate_hedis_cbp_measure(FHIR_BASE, max_patients)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/hedis-summary')
def get_hedis_summary():
    """
    Get summary of all HEDIS measures at once.
    
    Query parameters:
    - max_patients: Maximum number of patients per measure (default: 500)
    """
    try:
        max_patients = int(request.args.get('max_patients', 500))
        max_patients = min(max_patients, 2000)
        
        # Calculate all measures
        bcs_results = calculate_hedis_bcs_measure(FHIR_BASE, max_patients)
        col_results = calculate_hedis_col_measure(FHIR_BASE, max_patients)
        cdc_results = calculate_hedis_cdc_measure(FHIR_BASE, max_patients)
        cbp_results = calculate_hedis_cbp_measure(FHIR_BASE, max_patients)
        
        # Calculate overall star rating based on average compliance
        rates = []
        for result in [bcs_results, col_results, cdc_results, cbp_results]:
            if 'rate' in result and result.get('denominator', 0) > 0:
                rates.append(result['rate'])
        
        avg_rate = sum(rates) / len(rates) if rates else 0
        
        if avg_rate >= 90:
            star_rating = '⭐⭐⭐⭐⭐ (5 Stars - Excellent)'
        elif avg_rate >= 80:
            star_rating = '⭐⭐⭐⭐ (4 Stars - Very Good)'
        elif avg_rate >= 70:
            star_rating = '⭐⭐⭐ (3 Stars - Good)'
        elif avg_rate >= 60:
            star_rating = '⭐⭐ (2 Stars - Fair)'
        else:
            star_rating = '⭐ (1 Star - Needs Improvement)'
        
        return jsonify({
            'summary': {
                'average_rate': round(avg_rate, 2),
                'star_rating': star_rating,
                'total_measures': len(rates),
                'timestamp': datetime.now().isoformat()
            },
            'measures': {
                'breast_cancer_screening': bcs_results,
                'colorectal_cancer_screening': col_results,
                'diabetes_care': cdc_results,
                'blood_pressure_control': cbp_results
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat endpoint for conversational queries about claims data.
    
    Request body:
    {
        "message": "User's question about claims data"
    }
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Process the query
        result = chat_agent.process_user_query(user_message)
        
        return jsonify({
            'response': result['message'],
            'type': result['type'],
            'data': result.get('data', {}),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/export-csv', methods=['POST'])
def export_csv():
    """
    Export data to CSV based on chat query.
    
    Request body:
    {
        "data_type": "claims" or "summary",
        "filters": {}  // optional
    }
    """
    try:
        data = request.get_json()
        data_type = data.get('data_type', 'claims')
        filters = data.get('filters', {})
        
        csv_data = chat_agent.generate_csv(data_type, filters)
        
        # Create in-memory file
        output = io.BytesIO()
        output.write(csv_data.encode('utf-8'))
        output.seek(0)
        
        filename = f"{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/suggestions')
def get_chat_suggestions():
    """Get suggested queries for the chat interface."""
    suggestions = [
        "Show me breast cancer screening statistics",
        "What's our HEDIS quality measure score?",
        "Show mammogram trends",
        "What are the top 10 procedures?",
        "Show monthly claim trends",
        "Find mammography claims",
        "Export breast cancer screenings to CSV",
        "Show me cost trends by month",
        "Aggregate claims by status"
    ]
    return jsonify({'suggestions': suggestions})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
