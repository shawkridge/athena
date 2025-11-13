# SQLite & Qdrant Removal - Code Examples & Patterns

## PATTERN 1: Replace sqlite3.connect() with PostgreSQL

### Current (SQLite) - WRONG
```python
import sqlite3

def check_health():
    try:
        conn = sqlite3.connect(self.db_path, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return True
    except sqlite3.Error:
        return False
```

### Replacement (PostgreSQL) - CORRECT
```python
async def check_health(self):
    try:
        # Use the PostgreSQL database pool from core
        from ..core.database_postgres import PostgresDatabase
        db = PostgresDatabase()
        await db.execute("SELECT 1")
        return True
    except Exception:
        return False
```

---

## PATTERN 2: Replace sqlite3 Exceptions

### Current (SQLite) - WRONG
```python
try:
    cursor.execute(query)
except sqlite3.IntegrityError as e:
    logger.error(f"Integrity error: {e}")
except sqlite3.OperationalError as e:
    logger.error(f"Operational error: {e}")
except sqlite3.Error as e:
    logger.error(f"Database error: {e}")
```

### Replacement (PostgreSQL) - CORRECT
```python
try:
    await db.execute(query)
except psycopg.errors.IntegrityError as e:
    logger.error(f"Integrity error: {e}")
except psycopg.errors.OperationalError as e:
    logger.error(f"Operational error: {e}")
except psycopg.Error as e:
    logger.error(f"Database error: {e}")
```

### Import Changes
```python
# Remove this:
import sqlite3

# Add this:
import psycopg
from psycopg import errors as pg_errors
```

---

## PATTERN 3: Remove Qdrant Fallback from Search

### Current (With Qdrant Fallback) - WRONG
```python
def recall(self, query: str, project_id: int, k: int = 5):
    query_embedding = self.embedder.embed(query)
    
    # Try PostgreSQL first
    try:
        return self._recall_postgres(query_embedding, project_id, k)
    except Exception as e:
        logger.warning(f"PostgreSQL search failed, trying Qdrant: {e}")
        if self.qdrant:
            return self._recall_qdrant(query_embedding, project_id, k)
        else:
            raise

def _recall_qdrant(self, query_embedding, project_id, k):
    """Search using Qdrant vector database."""
    # ... Qdrant-specific code ...
```

### Replacement (PostgreSQL Only) - CORRECT
```python
async def recall(self, query: str, project_id: int, k: int = 5):
    query_embedding = self.embedder.embed(query)
    
    # Single path to PostgreSQL
    return await self._recall_postgres(query_embedding, project_id, k)

# Remove _recall_qdrant() method entirely
```

### Imports to Remove
```python
# Remove these:
from ..rag.qdrant_adapter import QdrantAdapter
from typing import Optional
```

---

## PATTERN 4: Remove Dual-Write Logic

### Current (Dual-Write to SQLite and Qdrant) - WRONG
```python
async def remember(self, content: str, memory_type: str, project_id: int):
    embedding = self.embedder.embed(content)
    
    # Write to SQLite
    memory_id = await self.db.store_memory(
        project_id=project_id,
        content=content,
        embedding=embedding,
        memory_type=memory_type
    )
    
    # Also write to Qdrant (dual-write)
    if self.qdrant:
        try:
            self.qdrant.add_memory(
                memory_id=memory_id,
                content=content,
                embedding=embedding,
                metadata={"project_id": project_id}
            )
        except Exception as e:
            logger.error(f"Failed to write to Qdrant: {e}")
    
    return memory_id
```

### Replacement (PostgreSQL Only) - CORRECT
```python
async def remember(self, content: str, memory_type: str, project_id: int):
    embedding = self.embedder.embed(content)
    
    # Single write to PostgreSQL
    memory_id = await self.db.store_memory(
        project_id=project_id,
        content=content,
        embedding=embedding,
        memory_type=memory_type
    )
    
    return memory_id
```

### Removals
```python
# Remove these parameter and initialization:
# - use_qdrant: bool = False parameter
# - self.qdrant = qdrant initialization
# - All dual-write logic in remember()
# - All Qdrant deletion logic in forget()
```

---

## PATTERN 5: Remove sqlite3 Type Hints

### Current (SQLite Type Hints) - WRONG
```python
import sqlite3
from typing import Dict

def _row_to_model(self, row: sqlite3.Row) -> Model:
    """Convert database row to Model."""
    # Access row like dict
    return Model(
        id=row['id'],
        name=row['name'],
    )
```

### Replacement (PostgreSQL Dict) - CORRECT
```python
from typing import Dict, Any

def _row_to_model(self, row: Dict[str, Any]) -> Model:
    """Convert database row to Model."""
    # Works with asyncpg dicts
    return Model(
        id=row['id'],
        name=row['name'],
    )
```

### Updated Docstrings
```python
# Remove references like:
"""
Args:
    row: Database row (sqlite3.Row)
"""

# Replace with:
"""
Args:
    row: Database row as dict
"""
```

---

## PATTERN 6: Remove Qdrant Imports

### Files with Qdrant Imports to Update

#### src/athena/memory/search.py
```python
# REMOVE THIS:
if TYPE_CHECKING:
    from ..rag.qdrant_adapter import QdrantAdapter

# REMOVE THIS from __init__:
def __init__(
    self,
    db: "PostgresDatabase",
    embedder: EmbeddingModel,
    qdrant: Optional["QdrantAdapter"] = None  # <-- REMOVE
):
    self.db = db
    self.embedder = embedder
    self.qdrant = qdrant  # <-- REMOVE
```

#### src/athena/memory/store.py
```python
# REMOVE THIS (line 18):
# Qdrant support is deprecated - we use PostgreSQL + pgvector instead
# QdrantAdapter import removed as part of host-based refactor

# REMOVE THIS parameter:
use_qdrant: bool = False,  # <-- REMOVE

# REMOVE THIS initialization:
if use_qdrant:
    logger.warning("Qdrant support is deprecated...")
```

---

## PATTERN 7: Update Exception Handling Patterns

### Pattern A: Try-Except with Multiple Exception Types

#### Before (SQLite)
```python
try:
    cursor.execute("""
        INSERT INTO memories (content, project_id)
        VALUES (?, ?)
    """, (content, project_id))
    self.conn.commit()
except sqlite3.IntegrityError:
    logger.error("Duplicate memory")
except sqlite3.Error as e:
    logger.error(f"Database error: {e}")
    self.conn.rollback()
```

#### After (PostgreSQL)
```python
try:
    await db.execute("""
        INSERT INTO memories (content, project_id)
        VALUES (%s, %s)
    """, (content, project_id))
    # PostgreSQL auto-commits or use transaction
except psycopg.errors.IntegrityError:
    logger.error("Duplicate memory")
except psycopg.Error as e:
    logger.error(f"Database error: {e}")
    # PostgreSQL handles rollback automatically in async
```

### Key Differences:
- `sqlite3.Error` → `psycopg.Error`
- `sqlite3.IntegrityError` → `psycopg.errors.IntegrityError`
- `sqlite3.OperationalError` → `psycopg.errors.OperationalError`
- Query placeholders: `?` → `%s`
- No explicit rollback needed (async PostgreSQL handles it)

---

## PATTERN 8: Remove sqlite3.Row Conversions

### Current (SQLite) - WRONG
```python
def list_events(self, project_id: int):
    results = []
    for row in self.execute("SELECT * FROM events"):
        # Manually convert sqlite3.Row to dict
        row_dict = dict(row)
        results.append(self._row_to_model(row_dict))
    return results
```

### Replacement (PostgreSQL) - CORRECT
```python
async def list_events(self, project_id: int):
    results = []
    rows = await db.execute("SELECT * FROM events WHERE project_id = %s", (project_id,))
    for row in rows:
        # asyncpg returns dicts directly
        results.append(self._row_to_model(row))
    return results
```

---

## PATTERN 9: Remove Qdrant Health Checks

### Current (With Qdrant Check) - WRONG
```python
def health_check(self):
    checks = {
        "postgres": self._check_postgres(),
        "qdrant": self._check_qdrant(),
        "embeddings": self._check_embeddings(),
    }
    return all(checks.values())

def _check_qdrant(self):
    if self.qdrant:
        return self.qdrant.health_check()
    return True
```

### Replacement (PostgreSQL Only) - CORRECT
```python
async def health_check(self):
    checks = {
        "postgres": await self._check_postgres(),
        "embeddings": self._check_embeddings(),
    }
    return all(checks.values())

# Remove _check_qdrant() method entirely
```

---

## PATTERN 10: Direct Database Path Usage

### Files with Direct sqlite3.connect(db_path)

These need to be migrated to use the PostgreSQL factory:

#### Before (sqlite3.connect pattern)
```python
def __init__(self, db_path: str):
    self.db_path = db_path
    self.conn = sqlite3.connect(db_path)

def get_stats(self):
    cursor = self.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM memories")
    return cursor.fetchone()[0]
```

#### After (PostgreSQL pattern)
```python
def __init__(self, db: PostgresDatabase):
    self.db = db

async def get_stats(self):
    result = await self.db.execute("SELECT COUNT(*) FROM memories")
    return result[0][0] if result else 0
```

---

## CHECKLIST FOR EACH FILE

When removing SQLite/Qdrant from a file:

- [ ] Remove `import sqlite3`
- [ ] Remove `import qdrant*`
- [ ] Remove sqlite3 exception handlers (replace with psycopg)
- [ ] Remove Qdrant fallback logic
- [ ] Update type hints (sqlite3.Row → dict)
- [ ] Replace sqlite3.connect() with PostgreSQL pool
- [ ] Update placeholder syntax (? → %s)
- [ ] Make methods async if using await
- [ ] Update docstrings (remove sqlite3 references)
- [ ] Run tests to verify functionality
- [ ] Commit with clear message

---

## VERIFICATION AFTER CHANGES

Run these to verify removals:

```bash
# Verify no sqlite3 imports remain
grep -r "import sqlite3" src/athena/ && echo "FAIL: sqlite3 imports found" || echo "PASS: No sqlite3 imports"

# Verify no qdrant imports remain
grep -r "import qdrant" src/athena/ && echo "FAIL: qdrant imports found" || echo "PASS: No qdrant imports"

# Verify no sqlite3.* references
grep -r "sqlite3\." src/athena/ && echo "FAIL: sqlite3.* references found" || echo "PASS: No sqlite3.* references"

# Verify qdrant_adapter.py deleted
test -f src/athena/rag/qdrant_adapter.py && echo "FAIL: qdrant_adapter.py still exists" || echo "PASS: qdrant_adapter.py deleted"

# Run tests
pytest tests/ -v --tb=short
```

