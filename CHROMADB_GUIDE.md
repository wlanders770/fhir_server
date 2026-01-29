# ChromaDB Vector Storage Guide

## Overview

The FHIR Chat Agent now uses **ChromaDB** for persistent vector storage. This allows the RAG (Retrieval Augmented Generation) system to:

- **Persist embeddings** across container restarts
- **Efficiently query** similar documents using vector similarity
- **Scale** to larger knowledge bases
- **Update incrementally** when new data is added

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Chat Agent Query                      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  Ollama Embedding      │
         │  (nomic-embed-text)    │
         │  768-dimensional       │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │    ChromaDB Query      │
         │  Cosine Similarity     │
         │  Top-K Retrieval       │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │  Retrieved Context     │
         │  + Source Metadata     │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │   Mistral 7B LLM       │
         │   Final Response       │
         └────────────────────────┘
```

## Storage Location

- **Container Path**: `/app/chroma_db`
- **Docker Volume**: `chroma_data` (persistent across restarts)
- **Format**: DuckDB + Parquet files

## Loading Options

### 1. Automatic (Lazy Loading) - **Default**

The knowledge base is automatically indexed on the **first query** that requires RAG context:

```python
# No manual intervention needed
# First chat query triggers indexing automatically
```

**When to use**: 
- Development environments
- When you want fast startup times
- When data rarely changes

### 2. Manual (On-Demand)

Trigger re-indexing via API endpoint:

```bash
# Re-index all data (clears existing)
curl -X POST http://localhost:5000/api/chat/reindex

# Response:
{
  "success": true,
  "total_documents": 10,
  "measures_indexed": 4,
  "knowledge_indexed": 6
}
```

**When to use**:
- After generating new HEDIS measure data
- After adding new CQL definition files
- When you want to refresh the knowledge base
- When testing RAG improvements

### 3. Startup Indexing

Modify `webapp/app.py` to index on application startup:

```python
# Add at the end of app.py, before if __name__ == '__main__':

# Index on startup
if chat_agent.use_rag and not chat_agent.indexed:
    print("Indexing knowledge base on startup...")
    chat_agent.reindex_all()
```

**When to use**:
- Production environments where consistency is critical
- When you want guarantees about data freshness
- When startup time is less important than immediate accuracy

### 4. Scheduled Background Jobs

For production environments with frequently changing data:

```python
# Add to app.py
import threading
import time

def background_reindex():
    """Re-index every 6 hours."""
    while True:
        time.sleep(6 * 3600)  # 6 hours
        try:
            print("Starting scheduled re-index...")
            chat_agent.reindex_all()
            print("Scheduled re-index complete")
        except Exception as e:
            print(f"Scheduled re-index failed: {e}")

# Start background thread
if chat_agent.use_rag:
    thread = threading.Thread(target=background_reindex, daemon=True)
    thread.start()
```

**When to use**:
- Production with regularly updated patient/claim data
- When you want automatic synchronization
- High-traffic environments

## Updating When New Data Is Created

### Option 1: Call API After Data Generation

Add to your data generation scripts:

```python
# At the end of seed/generate_hedis_claims.py
import requests

def trigger_reindex():
    """Trigger knowledge base re-indexing."""
    try:
        response = requests.post('http://localhost:5000/api/chat/reindex')
        if response.status_code == 200:
            print(f"✅ Knowledge base re-indexed: {response.json()}")
        else:
            print(f"⚠️  Re-index failed: {response.text}")
    except Exception as e:
        print(f"⚠️  Could not trigger re-index: {e}")

if __name__ == '__main__':
    generate_all_claims()
    trigger_reindex()
```

### Option 2: Web UI Button

Add a "Refresh Knowledge" button to the UI (already implemented):

```javascript
// In templates/index.html
async function refreshKnowledge() {
    const response = await fetch('/api/chat/reindex', { method: 'POST' });
    const result = await response.json();
    alert(`Indexed ${result.total_documents} documents!`);
}
```

### Option 3: FHIR Server Webhooks (Advanced)

If HAPI FHIR supports webhooks/subscriptions:

```python
# webapp/app.py - add webhook endpoint
@app.route('/api/fhir-webhook', methods=['POST'])
def fhir_webhook():
    """Handle FHIR resource creation events."""
    data = request.json
    
    # Check if it's a relevant resource (Patient, Claim, etc.)
    if data.get('resourceType') in ['Patient', 'Claim', 'Condition']:
        # Trigger incremental index update
        # (For now, we re-index everything; future: incremental)
        chat_agent.reindex_all()
    
    return jsonify({'status': 'ok'})
```

### Option 4: File System Watch (Advanced)

Monitor CQL files for changes:

```python
# Add to app.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CQLFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.cql'):
            print(f"CQL file changed: {event.src_path}")
            chat_agent.reindex_all()

observer = Observer()
observer.schedule(CQLFileHandler(), '/app/', recursive=False)
observer.start()
```

## Checking Index Status

```bash
# Check current status
curl http://localhost:5000/api/chat/index-status

# Response:
{
  "indexed": true,
  "document_count": 10,
  "rag_enabled": true
}
```

## What Gets Indexed

### 1. HEDIS Measure Definitions (4 documents)
- `hedis_bcs.cql` - Breast Cancer Screening
- `hedis_col.cql` - Colorectal Cancer Screening  
- `hedis_cdc.cql` - Comprehensive Diabetes Care
- `hedis_cbp.cql` - Controlling High Blood Pressure

### 2. Clinical Knowledge Base (6 documents)
- BCS screening criteria and CPT codes
- COL screening criteria and lookback periods
- CDC testing requirements
- CBP control targets
- Gap in care definitions
- Compliance rate calculations

## Performance Considerations

### Storage Size
- **Per Document**: ~3-5 KB (768-dim float32 embedding)
- **Current Total**: ~50 KB for 10 documents
- **Scalability**: Can handle 100K+ documents efficiently

### Query Speed
- **Embedding Generation**: ~50-200ms (Ollama)
- **Vector Search**: <10ms (ChromaDB)
- **Total RAG Latency**: ~100-300ms

### Memory Usage
- **ChromaDB**: ~50 MB base + (5 KB × documents)
- **Current**: ~50 MB for 10 documents

## Troubleshooting

### Issue: No documents indexed

```bash
# Check if collection exists
docker exec fhir-webapp python -c "
from chat_agent import create_chat_agent
agent = create_chat_agent()
print(f'Documents: {agent.collection.count()}')
"
```

### Issue: Embeddings fail to generate

```bash
# Verify Ollama embedding model is available
docker exec fhir-ollama ollama list
# Should show: nomic-embed-text

# Re-pull if missing
docker exec fhir-ollama ollama pull nomic-embed-text
```

### Issue: Stale data after updates

```bash
# Force re-index
curl -X POST http://localhost:5000/api/chat/reindex
```

### Issue: ChromaDB database corruption

```bash
# Clear volume and restart
docker compose down -v
docker volume rm fhir_server_chroma_data
docker compose up -d
```

## Best Practices

1. **Re-index after bulk data changes** - Call `/api/chat/reindex` after running seed scripts
2. **Monitor document count** - Check `/api/chat/index-status` regularly
3. **Backup ChromaDB volume** - Include in backup strategy for production
4. **Version CQL files** - Track changes to measure definitions
5. **Test RAG responses** - Verify context relevance after re-indexing

## Migration from In-Memory

If upgrading from the previous in-memory implementation:

1. **Rebuild container** to install ChromaDB
2. **First startup** will create empty collection
3. **First query** OR **manual reindex** will populate data
4. **Data persists** across restarts automatically

No manual data migration needed!

## Future Enhancements

- **Incremental indexing** - Update only changed documents
- **Multiple collections** - Separate collections for measures, patients, claims
- **Metadata filtering** - Filter by measure type, date, etc.
- **Semantic caching** - Cache common query results
- **A/B testing** - Compare embedding models and chunk sizes
