# Configuration Management Analysis Report

## Executive Summary
The CLAUDE.md documentation claims a 3-tier configuration precedence system, but the implementation is **fundamentally broken**. Critical issues include:

1. **Undocumented environment variable names** - Docs claim `DB_*` but code uses `ATHENA_POSTGRES_*`
2. **No settings file implementation** - Docs claim `~/.claude/settings.local.json` but no code reads this file
3. **Missing configuration precedence** - No code implements "Env vars > local settings file > defaults"
4. **Hardcoded values scattered everywhere** - Default database credentials inconsistent across modules
5. **No validation or error handling** - Invalid environment variables crash at runtime

---

## Issue #1: Database Configuration - Environment Variable Name Mismatch

### Documentation Claims (CLAUDE.md):
```
Database Configuration (PostgreSQL):
DB_HOST=localhost
DB_PORT=5432
DB_NAME=athena
DB_USER=postgres
DB_PASSWORD=postgres
```

### Actual Implementation:
**In src/athena/server.py (lines 25-29)**:
```python
db_host = os.getenv("ATHENA_POSTGRES_HOST", "postgres")
db_port = int(os.getenv("ATHENA_POSTGRES_PORT", "5432"))
db_name = os.getenv("ATHENA_POSTGRES_DB", "athena")
db_user = os.getenv("ATHENA_POSTGRES_USER", "athena")
db_password = os.getenv("ATHENA_POSTGRES_PASSWORD", "athena_dev")
```

### Impact:
- Users following CLAUDE.md documentation will set `DB_HOST`, `DB_PORT`, etc.
- Their values will be silently ignored
- Defaults will be used instead (`postgres` host, `athena_dev` password)
- Creates security risk (wrong credentials in production)

### Severity: **CRITICAL**

---

## Issue #2: Settings File Not Implemented

### Documentation Claims (CLAUDE.md):
```
Configuration Precedence: Env vars > local settings file > hardcoded defaults
Config file location: ~/.claude/settings.local.json
```

### Actual Implementation:
- **No code reads `~/.claude/settings.local.json`**
- **No code reads any settings JSON file**
- The only YAML configuration file is `.athena.yml` (in CLI module, for analysis profiles only)
- A `config/local.json` file exists in the repo but is not loaded by any Python code

### Files Checked:
- `src/athena/core/config.py` - Only reads environment variables, no file I/O
- `src/athena/server.py` - Only reads environment variables
- `src/athena/core/database_factory.py` - Only reads environment variables
- CLI configuration: `src/athena/cli.py` - Reads `.athena.yml` for analysis config only, not memory system config

### Impact:
- Users cannot configure Athena via JSON files
- No way to override environment variables locally
- Configuration must be set via environment variables only
- No development configuration isolation from production

### Severity: **CRITICAL**

---

## Issue #3: Inconsistent Database Defaults Across Modules

### Default Values Found:

**In src/athena/server.py (lines 25-29)**:
```python
db_host = "postgres"           # Docker container name
db_port = 5432
db_name = "athena"
db_user = "athena"
db_password = "athena_dev"    # Development password exposed
```

**In src/athena/core/database.py (lines 21-25)**:
```python
host: str = "localhost"        # Local development
port: int = 5432
dbname: str = "athena"
user: str = "postgres"         # Default Postgres user
password: str = "postgres"     # Default Postgres password
```

**In src/athena/core/database_factory.py (lines 105-110)**:
```python
os.environ.get('ATHENA_POSTGRES_HOST', 'localhost')  # Different default!
os.environ.get('ATHENA_POSTGRES_PORT', '5432')
os.environ.get('ATHENA_POSTGRES_DB', 'athena')
os.environ.get('ATHENA_POSTGRES_USER', 'postgres')
os.environ.get('ATHENA_POSTGRES_PASSWORD', 'postgres')  # Different from server.py
```

**In src/athena/skills/library.py (line 32)**:
```python
db = PostgresDatabase(host="localhost", dbname="athena")  # Hardcoded
```

**In src/athena/filesystem_api/layers/semantic/recall.py (docstring)**:
```python
host="localhost",
port=5432,
dbname="athena",
user="athena",
password="athena_dev",
```

**In src/athena/mcp/server_daemon.py (lines 51-52)**:
```python
host='localhost',
port=5432,
```

### Issue:
- Different files use different default usernames (`postgres` vs `athena`)
- Different files use different default passwords (`postgres` vs `athena_dev`)
- Docker defaults (`postgres` host) vs local development defaults (`localhost`)
- Some files hardcode credentials instead of reading from config

### Impact:
- Connecting to database may fail if correct defaults not used
- Hardcoded examples expose development credentials
- No centralized source of truth for defaults

### Severity: **HIGH**

---

## Issue #4: Missing Configuration Validation

### Current Implementation (src/athena/core/config.py):

No error handling for environment variables. Examples:

```python
LLAMACPP_EMBEDDING_DIM = int(os.environ.get("LLAMACPP_EMBEDDING_DIM", "768"))
# If env var is "invalid", raises ValueError at import time
# No try-except, no fallback, no logging

ENTITY_BASE_SCORE = float(os.environ.get("ENTITY_BASE_SCORE", "0.5"))
# If env var is "abc", raises ValueError
# Could crash the entire application

RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
# No validation that RAG_TOP_K is positive

CONSOLIDATION_BATCH_SIZE = int(os.environ.get("CONSOLIDATION_BATCH_SIZE", "100"))
# No minimum value check, could be 0 or negative

CACHE_SIZE = int(os.environ.get("CACHE_SIZE", "1000"))
# No maximum value check, could cause memory issues
```

### Missing Validations:
- No try-except blocks for type conversion
- No range validation (min/max bounds)
- No semantic validation (e.g., probabilities must be 0-1)
- No null/empty value handling
- No logging of invalid configuration
- No startup health checks

### Impact:
- Invalid configuration crashes at import time with cryptic errors
- No graceful degradation
- Hard to debug configuration issues
- Application fails early in startup

### Severity: **MEDIUM**

---

## Issue #5: Inconsistent Configuration Access Patterns

### Anti-Pattern 1: Direct Environment Variable Access
Many modules access `os.environ` directly instead of using `config` module:

**In src/athena/rag/llm_client.py (line 63)**:
```python
self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
```

**In src/athena/consolidation/openrouter_client.py (line 46)**:
```python
api_key = os.getenv("OPENROUTER_API_KEY")
```

**In src/athena/pii/config.py (lines 52-59)**:
```python
enabled=os.getenv('ATHENA_PII_ENABLED', 'true').lower() == 'true',
detection_mode=os.getenv('ATHENA_PII_DETECTION_MODE', 'strict'),
tokenization_strategy=os.getenv('ATHENA_PII_TOKENIZATION_STRATEGY', 'hash'),
# ... more direct access
```

### Impact:
- Configuration scattered across codebase
- Hard to track all configuration sources
- Difficult to implement settings file precedence (would need to change all files)
- No single place to document all available configurations

### Severity: **MEDIUM**

---

## Issue #6: Hardcoded Localhost URLs

Multiple files have hardcoded development URLs that should be configurable:

**In src/athena/core/embeddings.py (line 68)**:
```python
url_str = str(model_path) if model_path else "http://localhost:8001"
```

**In src/athena/core/llm_client.py (lines 56-57)**:
```python
embedding_url: str = "http://localhost:8001",
reasoning_url: str = "http://localhost:8002",
```

**In src/athena/client/http_client.py (line 63)**:
```python
url: str = "http://localhost:3000",
```

**In src/athena/http/server.py (line 74)**:
```python
allow_origins=["http://localhost:*", "http://127.0.0.1:*", "http://host.docker.internal:*"],
```

### Issue:
- Cannot run against remote services without code changes
- Development URLs hardcoded in library code (should be application-level config)

### Severity: **MEDIUM**

---

## Issue #7: Documentation Gaps in Configuration

### Missing Documentation:
1. Which modules read which environment variables?
2. What are all available environment variables?
3. How to configure for different environments (dev/staging/prod)?
4. How to use `.athena.yml` vs environment variables?
5. What if configuration file should exist at?
6. Migration path from old to new configuration system?

### Severity: **LOW** (but compounds other issues)

---

## Summary Table

| Issue | Location | Severity | Status |
|-------|----------|----------|--------|
| Wrong env var names (DB_*) | CLAUDE.md vs src/athena/server.py | CRITICAL | Not Fixed |
| Settings file not implemented | CLAUDE.md vs entire codebase | CRITICAL | Not Fixed |
| Inconsistent defaults | 6+ files | HIGH | Not Fixed |
| No validation/error handling | src/athena/core/config.py | MEDIUM | Not Fixed |
| Direct environ access scattered | rag/, pii/, consolidation/ | MEDIUM | Not Fixed |
| Hardcoded localhost URLs | 5+ files | MEDIUM | Not Fixed |
| Documentation gaps | CLAUDE.md | LOW | Not Fixed |

---

## Recommended Fix Priority

### Phase 1 - CRITICAL (Blocks production use):
1. **Add settings file support**
   - Implement JSON/YAML file reading in `src/athena/core/config.py`
   - Add precedence: env vars > settings file > defaults
   - File location: `~/.athena/config.json` or `~/.claude/settings.local.json`

2. **Fix database environment variables**
   - Either rename all to `ATHENA_POSTGRES_*` (done in code, not docs)
   - Or rename code to match docs (`DB_*`)
   - Update CLAUDE.md to match actual implementation

### Phase 2 - HIGH (Prevents consistency):
3. **Centralize database defaults**
   - Single source of truth in `src/athena/core/config.py`
   - All modules reference this single definition

4. **Add configuration validation**
   - Try-except blocks with meaningful error messages
   - Range validation for numeric parameters
   - Semantic validation for probabilities, etc.

### Phase 3 - MEDIUM (Code quality):
5. **Consolidate configuration access**
   - Route all env var access through `config` module
   - Remove direct `os.getenv()` calls from business logic

6. **Make service URLs configurable**
   - Move hardcoded `localhost:8001`, `localhost:3000` to config
   - Default to localhost for backward compatibility

### Phase 4 - LOW (Documentation):
7. **Update CLAUDE.md**
   - Document actual environment variable names
   - Document settings file format and location
   - Add examples for different environments
   - Document all 60+ configuration parameters

---

## Code Examples - Current vs Proposed

### Current (Broken):
```python
# src/athena/core/config.py - No validation
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
# Crash if "abc" is set, no validation that it's > 0

# src/athena/rag/llm_client.py - Direct access
api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

# src/athena/server.py - Inconsistent defaults
db_password = os.getenv("ATHENA_POSTGRES_PASSWORD", "athena_dev")
```

### Proposed (Correct):
```python
# src/athena/core/config.py - Validated, with settings file support
import json
from pathlib import Path

def _load_config_file():
    """Load settings from JSON file if it exists."""
    settings_path = Path.home() / ".athena" / "config.json"
    if settings_path.exists():
        with open(settings_path) as f:
            return json.load(f)
    return {}

_file_config = _load_config_file()

def _get_config(key: str, default, type_=str, min_=None, max_=None):
    """Get config value with precedence: env > file > default."""
    # Precedence: env vars > settings file > defaults
    value = os.environ.get(key)
    if value is None:
        value = _file_config.get(key)
    if value is None:
        value = default
    
    # Type conversion with error handling
    try:
        if type_ == int:
            value = int(value)
        elif type_ == float:
            value = float(value)
        # Validation
        if min_ is not None and value < min_:
            raise ValueError(f"{key} must be >= {min_}")
        if max_ is not None and value > max_:
            raise ValueError(f"{key} must be <= {max_}")
        return value
    except (ValueError, TypeError) as e:
        raise ConfigError(f"Invalid value for {key}: {e}")

# Usage
RAG_TOP_K = _get_config("RAG_TOP_K", 5, type_=int, min_=1, max_=100)
CLAUDE_API_KEY = _get_config("ANTHROPIC_API_KEY", None, type_=str)
```

This ensures the documented precedence is actually implemented.

