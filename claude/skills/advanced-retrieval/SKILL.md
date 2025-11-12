---
name: advanced-retrieval
description: |
  When standard search is insufficient and you need advanced RAG strategies for complex queries.
  When context enrichment (temporal, spatial, graph) would improve understanding.
  When query refinement through reflection or transformation could improve results.
---

# Advanced Retrieval Skill

Expert-level information retrieval using advanced RAG strategies and context enrichment.

## When to Use

- Standard search doesn't find relevant information
- Complex queries needing multiple strategies
- Abstract queries requiring hypothetical matching
- Need for temporal or spatial context enrichment
- Query needs refinement through reflection
- Combining information from multiple sources

## RAG Strategies Available

### 1. Hybrid Search (Default)
- Combines semantic (vector) + BM25 (lexical) search
- Best overall recall and precision
- Fast performance with good quality

### 2. HyDE (Hypothetical Document Embeddings)
- Generate hypothetical documents for query
- Improve semantic matching
- Good for abstract queries

### 3. Reranking
- Initial retrieval via semantic search
- Rerank results using cross-encoder
- Higher quality results but slower

### 4. Reflective Retrieval
- Iterative query refinement
- Multiple passes with improved queries
- Excellent for complex information needs

### 5. Query Transform
- Decompose query into sub-queries
- Retrieve for each sub-query
- Combine results intelligently

## Context Enrichment

### Temporal Context
- Find temporally related events
- Understand causality chains
- Identify patterns over time
- Weight recent information

### Spatial Context
- Include code location information
- Show file hierarchy
- Link to symbol dependencies
- Provide structural context

### Knowledge Graph Context
- Find related entities
- Traverse relationship paths
- Include expert observations
- Add community insights

## Retrieval Workflow

1. **Query Analysis**
   - Parse query intent
   - Identify key concepts
   - Determine scope

2. **Strategy Selection**
   - Choose appropriate RAG strategy
   - Set result limits
   - Configure filters

3. **Retrieval Execution**
   - Execute search
   - Collect candidates
   - Score results

4. **Enrichment**
   - Add temporal context
   - Include spatial information
   - Enhance with graph data

5. **Synthesis**
   - Combine results
   - Remove duplicates
   - Rank by relevance

## Quality Metrics

- **Relevance** - Results match query intent
- **Completeness** - All relevant results included
- **Precision** - Few irrelevant results
- **Freshness** - Recent information prioritized
- **Context** - Results include helpful context

## Example Use Cases

### Abstract Query
"security approaches"
→ Uses HyDE to generate hypothetical security documents, improves matching

### Complex Query
"How has authentication changed over time?"
→ Uses reflective retrieval with temporal context enrichment

### Multi-faceted Query
"consolidation effectiveness and optimization strategies"
→ Uses query transform to decompose, retrieves for each aspect, combines results

## Best Practices

1. Start with hybrid search for balanced results
2. Use reflective retrieval for complex queries
3. Enrich results with temporal/spatial context
4. Combine information from multiple sources
5. Validate results against knowledge base

Use advanced retrieval to unlock hidden knowledge with sophisticated search strategies.
