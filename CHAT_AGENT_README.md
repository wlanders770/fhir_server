# AI Chat Agent for FHIR Claims Data

## Overview

The AI Chat Agent is an intelligent conversational interface that allows you to query, analyze, and export your FHIR claims data using natural language. The agent understands questions about claims statistics, trends, procedures, and can generate reports and spreadsheets on demand.

## Features

### 🤖 Conversational Queries
- Ask questions in plain English about your claims data
- Get instant insights without writing SQL or complex queries
- Natural language understanding for common analytics tasks

### 📊 Analytics Capabilities
- **Claim Statistics**: Get total claims, costs, averages, and distributions
- **Trend Analysis**: View monthly trends for claims volume and costs
- **Top Procedures**: Identify most common procedures by frequency
- **Search & Filter**: Find claims by procedure name, code, or diagnosis
- **Aggregations**: Group claims by month, status, procedure, or cost

### 📄 Data Export
- **CSV Export**: Download claims data in spreadsheet format
- **Summary Reports**: Generate executive summaries with key metrics
- One-click export buttons for immediate downloads

### 💡 Intelligent Features
- **Quick Actions**: Pre-built queries as clickable suggestions
- **Real-time Data**: All queries run against live FHIR server data
- **Formatted Results**: Clean, readable responses with structured data
- **Visual Feedback**: Loading indicators and smooth animations

## Usage

### Web Interface

1. **Access the Dashboard**
   ```
   http://localhost:5000
   ```

2. **Locate the Chat Section**
   - Scroll down to the green "🤖 AI Chat Agent" section
   - The chat interface has two panels:
     - Left: Chat messages and input field
     - Right: Quick actions and export buttons

3. **Ask Questions**
   - Type your question in the input field
   - Press Enter or click "Send"
   - Examples:
     - "Show me claim statistics"
     - "What are the top 10 procedures?"
     - "Show monthly trends"
     - "Find mammogram claims"
     - "Aggregate claims by status"

4. **Use Quick Actions**
   - Click any suggestion button on the right sidebar
   - Pre-built queries execute immediately
   - Suggestions include:
     - Show me claim statistics
     - What are the top 10 procedures?
     - Show monthly trends
     - Export claims to CSV
     - Find mammogram claims
     - Aggregate claims by status
     - Show cost trends by month
     - Generate a summary spreadsheet

5. **Export Data**
   - Click "📄 Export Claims CSV" for full claims export
   - Click "📋 Export Summary Report" for executive summary
   - Files download automatically with timestamp

### REST API

#### Chat Endpoint

**Send a query to the chat agent:**

```bash
curl -X POST "http://localhost:5000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me claim statistics"}'
```

**Response:**
```json
{
  "response": "115,272 total claims, $169.75 avg cost",
  "type": "statistics",
  "data": {
    "total_claims": 115272,
    "average_cost": 169.75,
    "status_distribution": {
      "active": 431,
      "cancelled": 44,
      "draft": 25
    },
    "summary": "115,272 total claims, $169.75 avg cost"
  },
  "timestamp": "2026-01-27T02:16:24.113967"
}
```

#### Export CSV Endpoint

**Export claims to CSV:**

```bash
curl -X POST "http://localhost:5000/api/chat/export-csv" \
  -H "Content-Type: application/json" \
  -d '{"data_type": "claims"}' \
  -o claims_export.csv
```

**Export summary report:**

```bash
curl -X POST "http://localhost:5000/api/chat/export-csv" \
  -H "Content-Type: application/json" \
  -d '{"data_type": "summary"}' \
  -o summary_report.csv
```

#### Get Suggestions Endpoint

**Retrieve available query suggestions:**

```bash
curl "http://localhost:5000/api/chat/suggestions"
```

**Response:**
```json
{
  "suggestions": [
    "Show me claim statistics",
    "What are the top 10 procedures?",
    "Show monthly trends",
    "Export claims to CSV",
    "Find mammogram claims",
    "Aggregate claims by status",
    "Show cost trends by month",
    "Generate a summary spreadsheet"
  ]
}
```

## Available Tools

The chat agent has access to these built-in tools:

### 1. Query Claims
Filter claims by status, date range, or count limit.

**Example queries:**
- "Show me active claims"
- "Get claims from last month"
- "Find recent claims"

### 2. Query Patients
Search and filter patient records.

**Example queries:**
- "Show me female patients"
- "Get patient list"

### 3. Aggregate Claims
Group and summarize claims data.

**Example queries:**
- "Aggregate claims by month"
- "Group claims by status"
- "Show claims by procedure"
- "Aggregate costs by month"

### 4. Claim Statistics
Get comprehensive statistics and metrics.

**Example queries:**
- "Show me claim statistics"
- "What are the stats?"
- "Give me an overview"

### 5. Search by Procedure
Find claims with specific procedures.

**Example queries:**
- "Find mammogram claims"
- "Search for physical exams"
- "Show X-ray claims"

### 6. Top Procedures
Identify most common procedures.

**Example queries:**
- "What are the top procedures?"
- "Show most common procedures"
- "Top 10 procedures"

### 7. Monthly Trends
Analyze claims volume and costs over time.

**Example queries:**
- "Show monthly trends"
- "What are the trends?"
- "Display monthly statistics"

### 8. Export to CSV
Generate spreadsheet exports.

**Example queries:**
- "Export to CSV"
- "Generate spreadsheet"
- "Create summary report"

## Technical Architecture

### Backend Components

**chat_agent.py**
- `FHIRChatAgent` class: Main agent implementation
- Tool functions: Query execution methods
- Natural language processing: Intent detection and routing
- Data formatting: Result transformation for display

**app.py (Flask endpoints)**
- `/api/chat` (POST): Process chat messages
- `/api/chat/export-csv` (POST): Generate CSV exports
- `/api/chat/suggestions` (GET): Get query suggestions

### Frontend Components

**index.html**
- Chat UI: Message display and input interface
- Suggestions sidebar: Quick action buttons
- Export controls: CSV download buttons
- JavaScript functions:
  - `sendChatMessage()`: Send user queries
  - `addChatMessage()`: Display responses
  - `exportChatData()`: Download CSV files
  - `loadChatSuggestions()`: Load quick actions

### Data Flow

```
User Input → Chat UI → Flask API → Chat Agent → FHIR Server
                                        ↓
                                   Process Query
                                        ↓
                                   Format Results
                                        ↓
                              Return to Chat UI
```

## Extending the Chat Agent

### Adding New Tools

1. **Create a new tool method in `chat_agent.py`:**

```python
def my_new_tool(self, param1: str) -> Dict[str, Any]:
    """
    Description of what this tool does.
    
    Args:
        param1: Parameter description
    """
    # Implementation
    return {
        'data': result,
        'summary': 'Human-readable summary'
    }
```

2. **Register the tool in `__init__`:**

```python
self.tools = {
    # ... existing tools ...
    'my_new_tool': self.my_new_tool,
}
```

3. **Add intent detection in `process_user_query()`:**

```python
elif 'keyword' in message:
    result = self.my_new_tool(param)
    return {
        'type': 'my_tool_result',
        'data': result,
        'message': result['summary']
    }
```

### Adding New Suggestions

Edit the `get_chat_suggestions()` function in [app.py](webapp/app.py):

```python
suggestions = [
    # ... existing suggestions ...
    "Your new suggestion here"
]
```

## Example Queries & Responses

### Query: "Show me claim statistics"

**Response:**
```
115,272 total claims, $169.75 avg cost

Data:
{
  "total_claims": 115272,
  "average_cost": 169.75,
  "status_distribution": {
    "active": 431,
    "cancelled": 44,
    "draft": 25
  }
}
```

### Query: "What are the top 10 procedures?"

**Response:**
```
Top 10 procedures from 500 claims

Top procedures:
1. 97110 - Therapeutic exercise: 21 claims
2. 73610 - Ankle X-ray: 20 claims
3. 83036 - Hemoglobin A1C: 20 claims
4. 99396 - Established annual physical, 40-64: 20 claims
5. 11042 - Debridement, subcutaneous tissue: 18 claims
...
```

### Query: "Show monthly trends"

**Response:**
```
Monthly trends for last 7 months

Recent trends:
- 2025-12: 220 claims, $33,193.73 (avg $150.88)
- 2025-11: 43 claims, $6,627.91 (avg $154.14)
- 2025-10: 3 claims, $250.94 (avg $83.65)
...
```

### Query: "Export claims to CSV"

**Response:**
```
✅ Successfully exported claims data to CSV!

[File downloads automatically: claims_20260127_021624.csv]
```

## CSV Export Formats

### Claims Export (claims.csv)
```csv
Claim ID,Patient,Status,Created Date,Procedure Code,Procedure,Total Amount
claim-001,Patient/patient-123,active,2025-12-15,97110,Therapeutic exercise,$150.00
claim-002,Patient/patient-456,active,2025-12-16,73610,Ankle X-ray,$200.00
...
```

### Summary Report (summary.csv)
```csv
Metric,Value
Total Claims,115272
Average Cost,$169.75

Monthly Trends
Month,Claims,Total Cost,Avg Cost
2025-12,220,$33193.73,$150.88
2025-11,43,$6627.91,$154.14
...
```

## Performance Considerations

- **Query Limits**: Most queries sample 200-1000 claims to ensure fast response times
- **Timeout**: Flask configured with 120s timeout for complex queries
- **Caching**: Consider adding Redis for frequently accessed data
- **Pagination**: Large result sets are automatically paginated

## Future Enhancements

### Planned Features
- [ ] Integration with LLM APIs (OpenAI, Anthropic, etc.)
- [ ] Advanced NLP for complex query understanding
- [ ] Chart generation directly from chat queries
- [ ] Multi-turn conversations with context memory
- [ ] User-specific query history and favorites
- [ ] Scheduled reports via email
- [ ] Natural language to SQL translation
- [ ] Voice input support

### LLM Integration (Coming Soon)

To integrate with a real LLM for enhanced natural language understanding:

1. **Add API credentials to environment:**
```bash
export OPENAI_API_KEY="your-api-key"
# or
export ANTHROPIC_API_KEY="your-api-key"
```

2. **Update `chat_agent.py` to use LLM for intent detection:**
```python
import openai

def process_user_query_with_llm(self, user_message: str) -> Dict[str, Any]:
    # Use LLM to determine which tool to call
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a FHIR claims data assistant..."},
            {"role": "user", "content": user_message}
        ],
        functions=[...tool_definitions...]
    )
    # Execute the appropriate tool based on LLM response
```

## Troubleshooting

### Chat not loading
- Check webapp container is running: `docker ps | grep fhir-webapp`
- Check logs: `docker logs fhir-webapp`
- Verify Flask is listening on port 5000

### No data returned
- Verify FHIR server is accessible: `curl http://localhost:8080/fhir/Claim?_count=1`
- Check FHIR_BASE_URL environment variable
- Ensure claims data exists in database

### CSV export fails
- Check disk space
- Verify write permissions
- Check browser download settings
- Try smaller data_type parameter

### Slow responses
- Reduce sample sizes in agent methods
- Add database indexes
- Consider caching layer
- Check FHIR server performance

## Support & Documentation

- **Project README**: [README.md](README.md)
- **HEDIS Measure**: [HEDIS_BCS_README.md](HEDIS_BCS_README.md)
- **FHIR Server**: http://localhost:8080
- **Dashboard**: http://localhost:5000

## License

This chat agent is part of the FHIR Claims Dashboard project.
