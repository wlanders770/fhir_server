"""
Example scripts for using the FHIR Chat Agent programmatically

These examples demonstrate how to interact with the chat agent
via Python code instead of the web UI.
"""

import requests
import json
from datetime import datetime


# Configuration
CHAT_API_URL = "http://localhost:5000/api/chat"
EXPORT_API_URL = "http://localhost:5000/api/chat/export-csv"
SUGGESTIONS_API_URL = "http://localhost:5000/api/chat/suggestions"


def send_chat_message(message: str, print_response: bool = True) -> dict:
    """
    Send a message to the chat agent and get a response.
    
    Args:
        message: The question or query to ask the agent
        print_response: Whether to print the response (default: True)
    
    Returns:
        Response dictionary with type, data, and message
    """
    response = requests.post(
        CHAT_API_URL,
        headers={'Content-Type': 'application/json'},
        json={'message': message}
    )
    
    response.raise_for_status()
    data = response.json()
    
    if print_response:
        print(f"\n{'='*60}")
        print(f"Query: {message}")
        print(f"{'='*60}")
        print(f"Response: {data['response']}")
        print(f"Type: {data['type']}")
        
        if 'data' in data and data['data']:
            print(f"\nData Preview:")
            print(json.dumps(data['data'], indent=2)[:500] + "...")
    
    return data


def export_to_csv(data_type: str = 'claims', output_file: str = None) -> str:
    """
    Export data to CSV file.
    
    Args:
        data_type: 'claims' or 'summary'
        output_file: Optional custom output filename
    
    Returns:
        Path to saved file
    """
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{data_type}_export_{timestamp}.csv"
    
    response = requests.post(
        EXPORT_API_URL,
        headers={'Content-Type': 'application/json'},
        json={'data_type': data_type}
    )
    
    response.raise_for_status()
    
    with open(output_file, 'wb') as f:
        f.write(response.content)
    
    print(f"✓ Exported to {output_file}")
    return output_file


def get_suggestions() -> list:
    """Get available query suggestions."""
    response = requests.get(SUGGESTIONS_API_URL)
    response.raise_for_status()
    return response.json()['suggestions']


def example_1_basic_statistics():
    """Example 1: Get basic claim statistics"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Statistics")
    print("="*60)
    
    result = send_chat_message("Show me claim statistics")
    
    # Access specific data fields
    if result['type'] == 'statistics':
        stats = result['data']
        print(f"\n📊 Key Metrics:")
        print(f"   Total Claims: {stats['total_claims']:,}")
        print(f"   Average Cost: ${stats['average_cost']:.2f}")
        print(f"   Sample Size: {stats['sample_size']}")
        print(f"\n📋 Status Distribution:")
        for status, count in stats['status_distribution'].items():
            print(f"   {status}: {count}")


def example_2_top_procedures():
    """Example 2: Analyze top procedures"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Top Procedures Analysis")
    print("="*60)
    
    result = send_chat_message("What are the top 10 procedures?")
    
    if result['type'] == 'top_procedures':
        procedures = result['data']['top_procedures']
        print(f"\n🏥 Top {len(procedures)} Procedures:")
        for i, proc in enumerate(procedures, 1):
            print(f"   {i:2d}. {proc['procedure']:50s} ({proc['count']} claims)")


def example_3_monthly_trends():
    """Example 3: Analyze monthly trends"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Monthly Trends")
    print("="*60)
    
    result = send_chat_message("Show monthly trends")
    
    if result['type'] == 'trends':
        trends = result['data']['trends']
        print(f"\n📈 Monthly Trends ({len(trends)} months):\n")
        print(f"{'Month':<10} {'Claims':>8} {'Total Cost':>15} {'Avg Cost':>12}")
        print("-" * 50)
        for trend in trends:
            print(f"{trend['month']:<10} {trend['claim_count']:>8} "
                  f"${trend['total_cost']:>14,.2f} ${trend['avg_cost']:>11,.2f}")


def example_4_search_procedures():
    """Example 4: Search for specific procedures"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Procedure Search")
    print("="*60)
    
    queries = [
        "Find mammogram claims",
        "Search for physical exam claims",
        "Show X-ray claims"
    ]
    
    for query in queries:
        result = send_chat_message(query, print_response=False)
        if result['type'] == 'search_results':
            count = result['data']['count']
            print(f"\n'{query}' → Found {count} claims")


def example_5_aggregations():
    """Example 5: Different aggregation methods"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Data Aggregations")
    print("="*60)
    
    aggregations = [
        "Aggregate claims by status",
        "Aggregate claims by month", 
        "Show cost trends by month"
    ]
    
    for query in aggregations:
        result = send_chat_message(query, print_response=False)
        if result['type'] == 'aggregation':
            agg_type = result['data']['aggregation']
            data = result['data']['data']
            print(f"\n{query}:")
            print(f"  Type: {agg_type}")
            print(f"  Results: {len(data)} categories")
            # Show first few items
            for key, value in list(data.items())[:5]:
                print(f"    - {key}: {value}")


def example_6_export_data():
    """Example 6: Export data to CSV"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Data Export")
    print("="*60)
    
    # Export claims
    print("\nExporting claims data...")
    claims_file = export_to_csv('claims', 'my_claims_export.csv')
    
    # Export summary
    print("\nExporting summary report...")
    summary_file = export_to_csv('summary', 'my_summary_report.csv')
    
    print(f"\n✓ Exports completed:")
    print(f"  - Claims: {claims_file}")
    print(f"  - Summary: {summary_file}")


def example_7_batch_queries():
    """Example 7: Run multiple queries in batch"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Batch Queries")
    print("="*60)
    
    queries = [
        "Show me claim statistics",
        "What are the top 5 procedures?",
        "Show monthly trends",
        "Aggregate claims by status"
    ]
    
    results = []
    for query in queries:
        print(f"\nProcessing: {query}")
        result = send_chat_message(query, print_response=False)
        results.append({
            'query': query,
            'type': result['type'],
            'summary': result['response']
        })
    
    print(f"\n{'='*60}")
    print("BATCH RESULTS SUMMARY")
    print(f"{'='*60}")
    for i, res in enumerate(results, 1):
        print(f"\n{i}. {res['query']}")
        print(f"   Type: {res['type']}")
        print(f"   Result: {res['summary']}")


def example_8_custom_analysis():
    """Example 8: Build custom analysis from multiple queries"""
    print("\n" + "="*60)
    print("EXAMPLE 8: Custom Analysis Report")
    print("="*60)
    
    # Gather data from multiple sources
    stats = send_chat_message("Show me claim statistics", print_response=False)
    top_procs = send_chat_message("What are the top 5 procedures?", print_response=False)
    trends = send_chat_message("Show monthly trends", print_response=False)
    
    # Build custom report
    print("\n" + "="*60)
    print("CUSTOM CLAIMS ANALYSIS REPORT")
    print("Generated:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*60)
    
    # Overview section
    print("\n1. OVERVIEW")
    print("-" * 60)
    if stats['type'] == 'statistics':
        s = stats['data']
        print(f"Total Claims: {s['total_claims']:,}")
        print(f"Average Cost: ${s['average_cost']:.2f}")
        print(f"Sample Size: {s['sample_size']}")
    
    # Top procedures section
    print("\n2. TOP PROCEDURES")
    print("-" * 60)
    if top_procs['type'] == 'top_procedures':
        for i, proc in enumerate(top_procs['data']['top_procedures'][:5], 1):
            print(f"{i}. {proc['procedure']} - {proc['count']} claims")
    
    # Trends section
    print("\n3. RECENT TRENDS")
    print("-" * 60)
    if trends['type'] == 'trends':
        for trend in trends['data']['trends'][:3]:
            print(f"{trend['month']}: {trend['claim_count']} claims, "
                  f"${trend['total_cost']:,.2f} total")
    
    print("\n" + "="*60)
    print("END OF REPORT")
    print("="*60)


def show_available_suggestions():
    """Show all available query suggestions"""
    print("\n" + "="*60)
    print("AVAILABLE QUERY SUGGESTIONS")
    print("="*60)
    
    suggestions = get_suggestions()
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")


# Main execution
if __name__ == '__main__':
    print("\n" + "="*60)
    print("FHIR CHAT AGENT - PYTHON EXAMPLES")
    print("="*60)
    print("\nThese examples demonstrate programmatic interaction")
    print("with the FHIR Chat Agent API.\n")
    
    # Show available suggestions first
    show_available_suggestions()
    
    # Run examples
    try:
        # Uncomment the examples you want to run:
        
        example_1_basic_statistics()
        # example_2_top_procedures()
        # example_3_monthly_trends()
        # example_4_search_procedures()
        # example_5_aggregations()
        # example_6_export_data()
        # example_7_batch_queries()
        # example_8_custom_analysis()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to chat agent API")
        print("Make sure the FHIR dashboard is running at http://localhost:5000")
    except Exception as e:
        print(f"\n❌ Error: {e}")


# Utility functions for integration

def integrate_with_pandas():
    """
    Example: Convert chat agent results to pandas DataFrame
    """
    import pandas as pd
    
    # Get trends data
    result = send_chat_message("Show monthly trends", print_response=False)
    
    if result['type'] == 'trends':
        # Convert to DataFrame
        df = pd.DataFrame(result['data']['trends'])
        print("\nTrends as DataFrame:")
        print(df)
        
        # Perform pandas operations
        print(f"\nTotal claims: {df['claim_count'].sum()}")
        print(f"Average monthly cost: ${df['total_cost'].mean():,.2f}")
        
        return df


def integrate_with_matplotlib():
    """
    Example: Create charts from chat agent results
    """
    import matplotlib.pyplot as plt
    
    # Get monthly trends
    result = send_chat_message("Show monthly trends", print_response=False)
    
    if result['type'] == 'trends':
        trends = result['data']['trends']
        
        months = [t['month'] for t in trends]
        claims = [t['claim_count'] for t in trends]
        
        plt.figure(figsize=(12, 6))
        plt.bar(months, claims)
        plt.xlabel('Month')
        plt.ylabel('Claim Count')
        plt.title('Monthly Claim Volume')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('monthly_claims.png')
        print("✓ Chart saved to monthly_claims.png")


# Example: Using the chat agent in a larger application

class ClaimsAnalyzer:
    """
    Wrapper class for integrating the chat agent into larger applications
    """
    
    def __init__(self, api_url: str = "http://localhost:5000/api/chat"):
        self.api_url = api_url
    
    def query(self, message: str) -> dict:
        """Send a query and return the result"""
        response = requests.post(
            self.api_url,
            headers={'Content-Type': 'application/json'},
            json={'message': message}
        )
        response.raise_for_status()
        return response.json()
    
    def get_statistics(self) -> dict:
        """Get claim statistics"""
        result = self.query("Show me claim statistics")
        return result['data'] if result['type'] == 'statistics' else {}
    
    def get_top_procedures(self, limit: int = 10) -> list:
        """Get top procedures"""
        result = self.query(f"What are the top {limit} procedures?")
        return result['data']['top_procedures'] if result['type'] == 'top_procedures' else []
    
    def get_monthly_trends(self) -> list:
        """Get monthly trends"""
        result = self.query("Show monthly trends")
        return result['data']['trends'] if result['type'] == 'trends' else []
    
    def search_procedures(self, procedure_name: str) -> dict:
        """Search for specific procedures"""
        result = self.query(f"Find {procedure_name} claims")
        return result['data'] if result['type'] == 'search_results' else {}


# Example usage of wrapper class
def example_wrapper_class():
    """Demonstrate using the wrapper class"""
    print("\n" + "="*60)
    print("WRAPPER CLASS EXAMPLE")
    print("="*60)
    
    analyzer = ClaimsAnalyzer()
    
    # Get statistics
    stats = analyzer.get_statistics()
    print(f"\nTotal Claims: {stats.get('total_claims', 0):,}")
    
    # Get top procedures
    top_procs = analyzer.get_top_procedures(5)
    print(f"\nTop 5 Procedures:")
    for i, proc in enumerate(top_procs, 1):
        print(f"  {i}. {proc['procedure']}")
    
    # Get trends
    trends = analyzer.get_monthly_trends()
    print(f"\nFound trends for {len(trends)} months")
