---
category: skill
name: refactor-code
description: Guide systematic refactoring to improve code structure, readability, and maintainability
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Edit"]
confidence: 0.88
trigger: User wants to improve code structure, mentions "refactor", "duplication", "complexity", "cleanup"
---

# Refactor Code Skill

Guides systematic refactoring to improve code quality while maintaining correctness.

## When I Invoke This

You want to:
- Reduce code duplication
- Simplify complex functions
- Improve variable/function naming
- Break large files into modules
- Extract common patterns
- Improve readability and maintainability

## What I Do

I guide refactoring in these phases:

```
1. ANALYZE Phase: Identify opportunities
   → Find duplicated code
   → Find overly complex functions (>20 lines, >3 levels nesting)
   → Find poor naming
   → Find code that violates project patterns
   → Find cross-cutting concerns

2. DESIGN Phase: Plan the refactoring
   → Define desired structure
   → Identify intermediate checkpoints
   → List all files that need changes
   → Plan to maintain tests passing at each step

3. IMPLEMENT Phase: Refactor incrementally
   → Make small, safe changes
   → Keep tests passing
   → Commit after each successful change
   → Document rationale

4. VALIDATE Phase: Ensure correctness
   → All tests pass
   → Behavior unchanged
   → Performance not degraded
   → Code is cleaner/simpler
```

## Refactoring Patterns

### Pattern 1: Extract Method
**Problem**: Function doing too many things

```python
# ❌ Before: 50 lines doing multiple things
def process_user_data(user_json):
    # Parse JSON
    data = json.loads(user_json)
    if not data:
        raise ValueError("Invalid JSON")

    # Validate
    if not data.get("name"):
        raise ValueError("Name required")
    if "@" not in data.get("email", ""):
        raise ValueError("Invalid email")

    # Transform
    user = {
        "id": str(uuid.uuid4()),
        "name": data["name"].upper(),
        "email": data["email"].lower(),
        "created_at": int(time.time())
    }

    # Store
    db.insert("users", user)
    return user

# ✓ After: Clear separation of concerns
def process_user_data(user_json):
    data = parse_json(user_json)
    validate_user_data(data)
    user = create_user_object(data)
    store_user(user)
    return user

def parse_json(json_str):
    """Parse and validate JSON"""
    data = json.loads(json_str)
    if not data:
        raise ValueError("Invalid JSON")
    return data

def validate_user_data(data):
    """Validate user data has required fields"""
    if not data.get("name"):
        raise ValueError("Name required")
    if "@" not in data.get("email", ""):
        raise ValueError("Invalid email")

def create_user_object(data):
    """Create user object from data"""
    return {
        "id": str(uuid.uuid4()),
        "name": data["name"].upper(),
        "email": data["email"].lower(),
        "created_at": int(time.time())
    }

def store_user(user):
    """Store user in database"""
    db.insert("users", user)
```

**When to use**: Function >20 lines, multiple responsibilities

---

### Pattern 2: Extract Variable
**Problem**: Complex expression obscuring intent

```python
# ❌ Before: What does this calculation mean?
if user["created_at"] > (int(time.time()) - 86400 * 30) and user["account_type"] == "premium":
    apply_discount(user)

# ✓ After: Intent is clear
thirty_days_ago = int(time.time()) - (86400 * 30)
is_recent_premium = user["created_at"] > thirty_days_ago and user["account_type"] == "premium"
if is_recent_premium:
    apply_discount(user)
```

**When to use**: Complex calculations, magic numbers, unclear conditions

---

### Pattern 3: Consolidate Duplicates
**Problem**: Same code in multiple places

```python
# ❌ Before: Duplicated in 3 places
# In handler1.py
def save_data(data):
    if not data:
        return {"status": "error", "error": "No data"}
    result = db.insert(data)
    return {"status": "success", "data": result}

# In handler2.py (duplicate!)
def save_data(data):
    if not data:
        return {"status": "error", "error": "No data"}
    result = db.insert(data)
    return {"status": "success", "data": result}

# ✓ After: Single location, imported everywhere
# In shared/utils.py
def save_data(data):
    if not data:
        return {"status": "error", "error": "No data"}
    result = db.insert(data)
    return {"status": "success", "data": result}

# In handler1.py
from shared.utils import save_data

# In handler2.py
from shared.utils import save_data
```

**When to use**: Code appears in >2 locations

---

### Pattern 4: Rename for Clarity
**Problem**: Unclear variable or function names

```python
# ❌ Before: What does 'x' represent?
def calc(x, y):
    return x * y * 0.9

result = calc(100, 5)

# ✓ After: Names explain intent
def calculate_discounted_total(base_price, quantity):
    """Calculate total price with 10% discount applied"""
    discount_rate = 0.9  # 10% off
    return base_price * quantity * discount_rate

result = calculate_discounted_total(base_price=100, quantity=5)
```

**When to use**: Single-letter variables, cryptic function names

---

### Pattern 5: Extract Class
**Problem**: Class doing too many things

```python
# ❌ Before: 200+ lines mixing data and validation
class User:
    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = self._hash_password(password)

    def _hash_password(self, pwd):
        # 30 lines of password hashing logic
        ...

    def validate(self):
        # 40 lines of validation logic
        ...

    def save_to_db(self):
        # 20 lines of database logic
        ...

    def send_email(self):
        # 30 lines of email logic
        ...

# ✓ After: Clear separation of concerns
class User:
    def __init__(self, name, email, password_hash):
        self.name = name
        self.email = email
        self.password_hash = password_hash

class UserValidator:
    @staticmethod
    def validate(name, email, password):
        # Validation logic only
        ...

class UserRepository:
    @staticmethod
    def save(user):
        # Database logic only
        ...

class UserNotifier:
    @staticmethod
    def send_welcome_email(user):
        # Email logic only
        ...
```

**When to use**: Class >100 lines, multiple distinct responsibilities

---

### Pattern 6: Consolidate Conditionals
**Problem**: Complex nested if statements

```python
# ❌ Before: Hard to follow the logic
def can_purchase(user):
    if user.is_active:
        if user.account_type == "premium":
            if user.balance > 100:
                if not user.is_banned:
                    return True
    return False

# ✓ After: Intent is clear
def can_purchase(user):
    is_active = user.is_active
    is_premium = user.account_type == "premium"
    has_funds = user.balance > 100
    not_banned = not user.is_banned

    return is_active and is_premium and has_funds and not_banned

# Or even better:
def can_purchase(user):
    return all([
        user.is_active,
        user.account_type == "premium",
        user.balance > 100,
        not user.is_banned
    ])
```

**When to use**: >2 levels of nesting, unclear boolean logic

---

## Refactoring Checklist

### Before Starting
- [ ] All tests pass
- [ ] Code changes are committed
- [ ] Have clear refactoring goal
- [ ] Understand the code you're refactoring

### During Refactoring
- [ ] Make small, focused changes
- [ ] Run tests after each change
- [ ] Keep git history clean (commits at checkpoints)
- [ ] Don't change behavior, only structure
- [ ] Document why you're refactoring

### After Refactoring
- [ ] All tests pass
- [ ] Code is simpler/clearer
- [ ] No performance regression
- [ ] Commit message explains refactoring
- [ ] Consider if documentation needs update

## Anti-Patterns to Avoid

❌ **Mistake**: Over-engineering simple code
```python
# Don't extract if it's not actually duplicated
# Don't create abstractions that aren't needed
# Don't split code that should stay together
```

✓ **Better**: Keep refactoring focused and minimal

---

❌ **Mistake**: Refactoring without tests
```python
# Always have tests passing before refactoring
# Always run tests after each change
# Never refactor untested code
```

✓ **Better**: Green test suite before and after

---

❌ **Mistake**: Large refactors in one commit
```python
# Don't refactor 5 things at once
# Don't mix refactoring with new features
# Don't refactor across multiple files without checkpoints
```

✓ **Better**: Small, focused refactorings

---

❌ **Mistake**: Ignoring performance
```python
# Don't trade performance for cleanliness
# Profile before and after
# Validate refactoring doesn't slow code down
```

✓ **Better**: Clean code that's also fast

---

## Step-by-Step Refactoring Guide

### Step 1: Analyze
```
Read the code and ask:
- What does this function/class do?
- Is it doing multiple things?
- How complex is it (lines, nesting depth)?
- What could be simpler?
- What could be clearer?
```

### Step 2: Plan
```
Create a plan:
1. Extract method X (1-2 hours)
2. Run tests, commit
3. Rename variables Y (30 mins)
4. Run tests, commit
5. Consolidate duplicates Z (1 hour)
6. Run tests, commit
```

### Step 3: Implement
```
For each planned change:
1. Make the change
2. Run tests
3. If tests fail: revert, debug, try again
4. If tests pass: commit with clear message
5. Move to next change
```

### Step 4: Review
```
After refactoring:
- Does code match project patterns?
- Is it more readable?
- Are variable/function names clear?
- Are there any remaining smells?
- Could it be simplified further?
```

## Tools & Commands

```bash
# Find duplicate code
grep -rn "PATTERN" src/

# Analyze complexity
python -m radon cc src/ -a

# Find unused imports
python -m pylint --disable=all --enable=unused-import src/

# Check code style
black --check src/
ruff check src/

# Run tests before refactoring
pytest tests/ -v

# Run tests after each change
pytest tests/ -v

# Profile to ensure performance
python -m cProfile -o profile.stats script.py
```

## Related Skills

- **fix-failing-tests** - When tests fail during refactoring
- **code-review** - To validate refactoring quality
- **add-mcp-tool** - For consistent refactoring of tool patterns

## Success Criteria

✓ Code is simpler and clearer
✓ All tests pass (behavior unchanged)
✓ Complexity reduced (fewer lines, less nesting)
✓ No performance degradation
✓ Naming is clear and consistent
✓ Changes are minimal and focused
✓ History is clean (logical commits)
