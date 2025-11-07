# Semantic Code Search REST API Reference

Complete API documentation for the Semantic Code Search backend service.

**Base URL**: `http://localhost:5000` (default)
**Version**: 1.0.0
**Content-Type**: `application/json`

---

## Endpoints Overview

| Method | Endpoint | Purpose | Latency |
|--------|----------|---------|---------|
| GET | `/health` | Backend status check | <5ms |
| POST | `/search` | Semantic code search | 50-250ms |
| POST | `/search/by-type` | Search by code type | 50-200ms |
| POST | `/search/by-name` | Pattern-based search | 30-150ms |
| POST | `/dependencies` | Find code dependencies | 100-500ms |
| POST | `/analyze` | Analyze code file | 200-1000ms |
| POST | `/statistics` | Index statistics | <50ms |
| POST | `/index` | Workspace indexing | 2-10s per 1000 files |

---

## 1. Health Check

Check if backend is running and indexed.

### Request

```http
GET /health
```

### Response

```json
{
  "status": "ready",
  "indexed": true,
  "version": "1.0.0",
  "units_indexed": 12543,
  "files_indexed": 234,
  "cache_size": 1024,
  "uptime_seconds": 3600
}
```

### Example

```bash
curl http://localhost:5000/health
```

---

## 2. Semantic Search

Find code using semantic/natural language queries.

### Request

```http
POST /search
Content-Type: application/json

{
  "query": "function that validates email",
  "strategy": "adaptive",
  "limit": 10,
  "min_score": 0.3,
  "use_rag": false,
  "language": "auto"
}
```

### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| query | string | ✅ | — | Search query in natural language |
| strategy | string | ❌ | "adaptive" | RAG strategy: "adaptive", "self", "corrective", "direct" |
| limit | integer | ❌ | 10 | Max results (1-100) |
| min_score | number | ❌ | 0.3 | Relevance threshold (0.0-1.0) |
| use_rag | boolean | ❌ | false | Enable RAG strategies |
| language | string | ❌ | "auto" | Language hint: "auto", "python", "javascript", "java", "go" |

### Response

```json
{
  "results": [
    {
      "name": "validate_email",
      "type": "function",
      "file": "src/utils/validators.py",
      "line": 42,
      "relevance": 0.87,
      "docstring": "Validates email format using regex"
    }
  ],
  "query": "function that validates email",
  "strategy": "adaptive",
  "total_results": 1,
  "elapsed_time": 0.127
}
```

### Example

```bash
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "function that validates email", "limit": 10}'
```

---

## 3. Search by Type

Search for code by type (function, class, etc.).

### Request

```http
POST /search/by-type
Content-Type: application/json

{
  "type": "function",
  "query": "validate",
  "limit": 20
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | ✅ | "function", "class", "import", "variable", "method" |
| query | string | ❌ | Optional filter query |
| limit | integer | ❌ | Max results (1-100, default 10) |

### Example

```bash
curl -X POST http://localhost:5000/search/by-type \
  -H "Content-Type: application/json" \
  -d '{"type": "function", "query": "validate", "limit": 20}'
```

---

## 4. Semantic Search by Name

Pattern-based search by name/identifier.

### Request

```http
POST /search/by-name
Content-Type: application/json

{
  "pattern": "validate_*",
  "limit": 10,
  "case_sensitive": false
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| pattern | string | ✅ | Name pattern (supports * wildcard) |
| limit | integer | ❌ | Max results (1-100, default 10) |
| case_sensitive | boolean | ❌ | Case-sensitive matching (default false) |

### Example

```bash
curl -X POST http://localhost:5000/search/by-name \
  -H "Content-Type: application/json" \
  -d '{"pattern": "validate_*", "limit": 20}'
```

---

## 5. Find Dependencies

Analyze code dependencies.

### Request

```http
POST /dependencies
Content-Type: application/json

{
  "file": "src/services/user.py",
  "type": "imports"
}
```

### Response

```json
{
  "file": "src/services/user.py",
  "dependencies": [
    {
      "name": "validate_email",
      "file": "src/utils/validators.py",
      "type": "function"
    }
  ],
  "elapsed_time": 0.234
}
```

---

## 6. Analyze Code File

Get detailed analysis of a code file.

### Request

```http
POST /analyze
Content-Type: application/json

{
  "file": "src/utils/validators.py"
}
```

### Response

```json
{
  "file": "src/utils/validators.py",
  "language": "python",
  "size_bytes": 4523,
  "line_count": 145,
  "functions": [
    {"name": "validate_email", "line": 42}
  ],
  "classes": [
    {"name": "Validator", "line": 80}
  ],
  "elapsed_time": 0.562
}
```

---

## 7. Get Statistics

Get workspace index statistics.

### Request

```http
POST /statistics
Content-Type: application/json

{}
```

### Response

```json
{
  "total_files": 234,
  "total_units": 12543,
  "index_size_mb": 45.2,
  "languages": {
    "python": 120,
    "javascript": 80,
    "java": 34
  },
  "unit_types": {
    "function": 8234,
    "class": 3421,
    "import": 765
  },
  "last_indexed": "2024-11-07T15:30:00Z"
}
```

---

## 8. Index Workspace

Trigger workspace re-indexing.

### Request

```http
POST /index
Content-Type: application/json

{
  "path": "/home/user/projects/myapp",
  "recursive": true,
  "languages": ["python", "javascript", "java", "go"]
}
```

### Response

```json
{
  "status": "complete",
  "files": 234,
  "units": 12543,
  "duration_seconds": 3.45,
  "languages_found": {
    "python": 120,
    "javascript": 80,
    "java": 34
  }
}
```

---

## Performance

### Latency by Operation

| Operation | Latency |
|-----------|---------|
| `/health` | <5ms |
| `/search` (direct) | 50-100ms |
| `/search` (with RAG) | 100-250ms |
| `/statistics` | <50ms |
| `/index` | 2-10s per 1000 files |

### Caching

Results cached with LRU strategy:
- **Cache Size**: ~1000 items
- **Hit Rate**: ~70%
- **Speedup**: 22x faster for cached results

---

## Error Handling

All endpoints return errors in standard format:

```json
{
  "error": "Invalid parameters",
  "message": "limit must be between 1 and 100",
  "status": 400
}
```

---

## Code Examples

### Python

```python
import requests

response = requests.post('http://localhost:5000/search', json={
    'query': 'function that validates email',
    'limit': 10,
    'use_rag': True
})
results = response.json()
```

### JavaScript

```javascript
const response = await fetch('http://localhost:5000/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'function that validates email',
    limit: 10,
    use_rag: true
  })
});
```

### cURL

```bash
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "function that validates email", "limit": 10}'
```

---

**Last Updated**: November 7, 2025
**Status**: Production Ready
