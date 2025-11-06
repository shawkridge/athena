---
description: Advanced semantic search with 4 RAG strategies - handles complex domain-specific queries
argument-hint: "Search query (supports complex boolean and semantic queries)"
---

# Retrieve Smart

Advanced semantic search with 4 intelligent RAG strategies for high-precision retrieval.

Usage: `/retrieve-smart "complex search query"`

**4 RAG Strategies** (auto-selected):

1. **HyDE** (Hypothetical Document Embeddings)
   - Use: Ambiguous or short queries (<5 words)
   - Example: `/retrieve-smart "JWT tokens"`

2. **LLM Reranking**
   - Use: Standard searches requiring precision
   - Example: `/retrieve-smart "how do we handle authentication refresh tokens"`

3. **Query Transformation**
   - Use: References to context (it, that, those, which)
   - Example: `/retrieve-smart "what else did we learn from that approach"`

4. **Reflective Retrieval**
   - Use: Temporal patterns and causality
   - Example: `/retrieve-smart "what changed in our auth approach over time"`

Features:
- **Auto-Strategy Selection**: Analyzes query and selects optimal strategy
- **Ranked Results**: Returns findings ranked by relevance and confidence
- **Multi-Layer Search**: Searches episodic, semantic, procedural, graph layers
- **Context Preservation**: Maintains relationship context in results
- **Explanation**: Shows which strategy was selected and why

Returns:
- Top 10 results ranked by relevance
- Confidence score per result (0.0-1.0)
- Selected strategy and reasoning
- Related concepts and connections
- Temporal context (when discovered, relationships)
- Suggested follow-up queries

Example output:
```
Query: "JWT token expiration strategies"
Strategy Selected: LLM Reranking (standard precision query)

Results:
1. Procedure: JWT-Token-Management (0.95)
   - Covers expiration handling, refresh tokens, validation
2. Semantic Memory: "Access token 1h, refresh token 7d" (0.88)
   - From OAuth2 implementation session
3. Knowledge Graph: TokenExpiration → AccessControl (0.82)
   - Related entities: SecurityPolicy, SessionManagement
```

The rag-specialist agent uses this for complex research tasks.
