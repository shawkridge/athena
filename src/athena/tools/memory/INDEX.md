# Memory Tools

## recall
- **Description**: Search and retrieve memories using semantic search
- **Entry Point**: `recall()`
- **Returns**: List[Memory] - Matching memories with scores
- **Example**: `recall('How to authenticate users?', limit=5)`

## remember
- **Description**: Record a new episodic event or semantic memory
- **Entry Point**: `remember()`
- **Returns**: str - Memory ID
- **Example**: `remember('Implemented user auth', tags=['security', 'auth'])`

## forget
- **Description**: Delete a memory by ID
- **Entry Point**: `forget()`
- **Returns**: bool - True if deleted
- **Example**: `forget('mem_12345')`
