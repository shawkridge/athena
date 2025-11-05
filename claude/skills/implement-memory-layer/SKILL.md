---
category: skill
name: implement-memory-layer
description: Scaffold and implement complete memory layers with proper architecture and testing
allowed-tools: ["Bash", "Read", "Write", "Glob", "Grep", "Edit", "TodoWrite"]
confidence: 0.90
trigger: User is building a new memory layer, mentions "new layer", "memory layer", "implements layer interface"
---

# Implement Memory Layer Skill

Guides architecture and implementation of new Memory MCP layers following established patterns.

## When I Invoke This

You're:
- Building a new memory layer (e.g., prospective, working-memory)
- Need to implement the full layer stack (models → store → integration → MCP tools)
- Want to follow Memory MCP architectural patterns
- Need comprehensive testing from the start

## What I Do

I guide you through implementing a complete memory layer in these phases:

```
1. DESIGN Phase: Understand the layer requirements
   → What data does it store?
   → What operations are needed (CRUD + queries)?
   → How does it fit into the 8-layer architecture?
   → What existing layers does it interact with?

2. MODELS Phase: Define data structures
   → Create models.py with Pydantic models
   → Define enums for constrained values
   → Add Field descriptions for documentation
   → Design for validation and type safety

3. STORE Phase: Implement storage and queries
   → Create store.py with database schema
   → Implement CRUD operations
   → Add query methods (search, filter, list)
   → Use parameterized queries (SQL injection safe)

4. INTEGRATION Phase: Connect to system
   → Add auto-population hooks
   → Register in UnifiedMemoryManager
   → Link to temporal/spatial systems
   → Implement consolidation rules

5. MCP TOOLS Phase: Expose via API
   → Create @mcp.tool() handlers
   → Implement query and manipulation tools
   → Add error handling and validation
   → Document with examples

6. TESTING Phase: Comprehensive coverage
   → Unit tests for store (CRUD, queries)
   → Integration tests (multi-layer workflows)
   → End-to-end tests (MCP tool invocation)
   → Performance tests if applicable

7. DOCUMENTATION Phase: Make discoverable
   → Update architecture docs
   → Add to layer inventory
   → Document data model
   → Provide usage examples
```

## Memory Layer Architecture Template

### Phase 1: Create Module Structure

```
src/memory_mcp/new_layer/
├── __init__.py          # Empty or exports
├── models.py            # Pydantic models
├── store.py             # Database store
└── integration.py       # (Optional) Integration hooks
```

### Phase 2: Define Models (models.py)

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime

class ItemStatus(str, Enum):
    """Status enum with string values for database storage"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"

class Item(BaseModel):
    """Represents a single item in this memory layer"""
    id: Optional[int] = None
    content: str = Field(..., description="Item content/description")
    status: ItemStatus = ItemStatus.PENDING
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(use_enum_values=True)

class ItemQuery(BaseModel):
    """Query parameters for searching items"""
    status: Optional[ItemStatus] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

### Phase 3: Implement Store (store.py)

```python
from memory_mcp.core.database import Database
from memory_mcp.new_layer.models import Item, ItemStatus

class NewLayerStore:
    """Database store for new memory layer"""

    def __init__(self, db: Database):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create tables on first use"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS new_layer_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        # Add indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_new_layer_status
            ON new_layer_items(status)
        """)
        self.db.conn.commit()

    def create(self, item: Item) -> Item:
        """Create new item and return with ID"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO new_layer_items (content, status, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (item.content, item.status, item.created_at, item.updated_at))
        self.db.conn.commit()

        item.id = cursor.lastrowid
        return item

    def get(self, id: int) -> Optional[Item]:
        """Retrieve item by ID"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, content, status, created_at, updated_at FROM new_layer_items WHERE id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Item(id=row[0], content=row[1], status=row[2], created_at=row[3], updated_at=row[4])

    def list_by_status(self, status: ItemStatus, limit: int = 10) -> list[Item]:
        """Query items by status"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id, content, status, created_at, updated_at
            FROM new_layer_items
            WHERE status = ?
            LIMIT ?
        """, (status, limit))
        return [Item(id=r[0], content=r[1], status=r[2], created_at=r[3], updated_at=r[4]) for r in cursor.fetchall()]

    def update(self, item: Item) -> bool:
        """Update existing item"""
        cursor = self.db.conn.cursor()
        item.updated_at = int(time.time())
        cursor.execute("""
            UPDATE new_layer_items
            SET content = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (item.content, item.status, item.updated_at, item.id))
        self.db.conn.commit()
        return cursor.rowcount > 0

    def delete(self, id: int) -> bool:
        """Delete item by ID"""
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM new_layer_items WHERE id = ?", (id,))
        self.db.conn.commit()
        return cursor.rowcount > 0
```

### Phase 4: Create MCP Tools (in mcp/handlers.py)

```python
@mcp.tool()
async def create_new_layer_item(
    self,
    content: str,
    status: str = "pending"
) -> dict:
    """Create new item in the layer.

    Args:
        content: Item description/content
        status: Status (pending|active|completed), default: pending

    Returns:
        Success: {"status": "success", "data": {"id": 123, "content": "..."}}
        Error: {"status": "error", "error": "description"}
    """
    try:
        if not content or not content.strip():
            return {"status": "error", "error": "content cannot be empty"}

        if status not in ["pending", "active", "completed"]:
            return {"status": "error", "error": f"Invalid status: {status}"}

        item = Item(content=content, status=ItemStatus(status))
        result = self.new_layer_store.create(item)

        return {
            "status": "success",
            "data": {"id": result.id, "content": result.content, "status": result.status}
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

## Testing Template

### Unit Tests (tests/unit/test_new_layer.py)

```python
import pytest
from memory_mcp.core.database import Database
from memory_mcp.new_layer.store import NewLayerStore
from memory_mcp.new_layer.models import Item, ItemStatus

def test_create_item(tmp_path):
    """Test creating an item"""
    db = Database(tmp_path / "test.db")
    store = NewLayerStore(db)

    item = store.create(Item(content="Test item"))

    assert item.id is not None
    assert item.content == "Test item"
    assert item.status == ItemStatus.PENDING

def test_get_item(tmp_path):
    """Test retrieving an item"""
    db = Database(tmp_path / "test.db")
    store = NewLayerStore(db)

    created = store.create(Item(content="Test"))
    retrieved = store.get(created.id)

    assert retrieved is not None
    assert retrieved.content == "Test"

def test_list_by_status(tmp_path):
    """Test filtering items by status"""
    db = Database(tmp_path / "test.db")
    store = NewLayerStore(db)

    store.create(Item(content="Active1", status=ItemStatus.ACTIVE))
    store.create(Item(content="Active2", status=ItemStatus.ACTIVE))
    store.create(Item(content="Pending1", status=ItemStatus.PENDING))

    active = store.list_by_status(ItemStatus.ACTIVE)

    assert len(active) == 2
    assert all(item.status == ItemStatus.ACTIVE for item in active)

def test_update_item(tmp_path):
    """Test updating an item"""
    db = Database(tmp_path / "test.db")
    store = NewLayerStore(db)

    item = store.create(Item(content="Original"))
    item.content = "Updated"
    updated = store.update(item)

    assert updated is True
    retrieved = store.get(item.id)
    assert retrieved.content == "Updated"

def test_delete_item(tmp_path):
    """Test deleting an item"""
    db = Database(tmp_path / "test.db")
    store = NewLayerStore(db)

    item = store.create(Item(content="Temp"))
    deleted = store.delete(item.id)

    assert deleted is True
    assert store.get(item.id) is None
```

### Integration Tests (tests/integration/test_new_layer_integration.py)

```python
@pytest.mark.asyncio
async def test_mcp_tool_integration(mcp_server):
    """Test MCP tool for creating items"""
    result = await mcp_server.create_new_layer_item(
        content="Test via MCP",
        status="active"
    )

    assert result["status"] == "success"
    assert "id" in result["data"]
    assert result["data"]["content"] == "Test via MCP"
```

## Integration Checklist

- [ ] **Models**: Defined with validation and descriptions
- [ ] **Store**: CRUD operations implemented, SQL injection safe
- [ ] **Schema**: Tables created with indexes for common queries
- [ ] **MCP Tools**: @mcp.tool() handlers for all major operations
- [ ] **Error Handling**: Comprehensive try/except with helpful messages
- [ ] **Unit Tests**: All store operations tested (happy + edge + error)
- [ ] **Integration Tests**: MCP tools work end-to-end
- [ ] **Documentation**: Layer documented in architecture docs
- [ ] **Consolidation**: Integration rules defined if applicable
- [ ] **Performance**: Indexes in place, query performance acceptable

## Files to Update

| File | What to Add |
|------|------------|
| `src/memory_mcp/new_layer/__init__.py` | Export store and models |
| `src/memory_mcp/mcp/handlers.py` | Add MCP tools for layer |
| `src/memory_mcp/integration/auto_populate.py` | Add auto-population logic |
| `MEMORY_MCP_ARCHITECTURE.md` | Document new layer |
| `README.md` | Add to layer inventory |

## Related Skills

- **add-mcp-tool** - For creating individual tools
- **refactor-code** - If store code gets complex
- **fix-failing-tests** - If tests need debugging

## Success Criteria

✓ All models validate correctly
✓ Store implements CRUD + queries
✓ SQL is parameterized (safe from injection)
✓ All unit tests pass
✓ All integration tests pass
✓ MCP tools work correctly
✓ Error handling is comprehensive
✓ Architecture documentation updated
