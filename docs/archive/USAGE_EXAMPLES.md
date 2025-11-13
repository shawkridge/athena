# Usage Examples & Tutorials

## Multi-Language Code Search System

**Date**: November 7, 2025
**Status**: ✅ Complete

---

## Quick Start Guide

### Installation & Setup

```bash
# Install in development mode
pip install -e .

# Verify installation
python -c "from athena.code_search.tree_sitter_search import TreeSitterCodeSearch; print('✅ Code search ready')"
```

### Basic Usage (All Languages)

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

# Create search engine for any language
search = TreeSitterCodeSearch("/path/to/python/repo", language="python")
search = TreeSitterCodeSearch("/path/to/js/repo", language="javascript")
search = TreeSitterCodeSearch("/path/to/java/repo", language="java")
search = TreeSitterCodeSearch("/path/to/go/repo", language="go")

# Build index
search.build_index()

# Search semantically
results = search.search("authenticate user", limit=10)
for result in results:
    print(f"Found: {result.unit.name} in {result.unit.file_path} (score: {result.score:.2f})")

# Search by type
functions = search.search_by_type("function")
classes = search.search_by_type("class")

# Search by name
auth_func = search.search_by_name("authenticate", exact=False)

# Analyze a file
analysis = search.analyze_file("src/auth/authentication.py")
print(f"File has {len(analysis.functions)} functions")
print(f"File has {len(analysis.classes)} classes")

# Find dependencies
deps = search.find_dependencies("src/auth/handler.py", "authenticate")
print(f"authenticate() depends on: {deps}")

# Get statistics
stats = search.get_code_statistics()
print(f"Indexed {stats.total_units} units in {stats.total_files} files")
```

---

## Tutorial 1: Searching a Python Codebase

### Example: Finding Authentication Logic

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

# Index your Python project
search = TreeSitterCodeSearch("./my_python_project", language="python")
print("Building index...")
search.build_index()

# Find all authentication-related functions
auth_results = search.search("authenticate", limit=20)
print(f"Found {len(auth_results)} authentication functions:")
for result in auth_results:
    print(f"  - {result.unit.name} ({result.unit.type})")
    print(f"    Score: {result.score:.2f}")
    print(f"    Location: {result.unit.file_path}:{result.unit.start_line}")
    if result.unit.docstring:
        print(f"    Doc: {result.unit.docstring[:100]}...")
    print()

# Find all classes that extend a base class
class_results = search.search("Handler", query_type="class")
print(f"Found {len(class_results)} handler classes:")
for result in class_results:
    print(f"  - {result.unit.name} in {result.unit.file_path}")
    if result.unit.dependencies:
        print(f"    Dependencies: {result.unit.dependencies}")

# Analyze a specific file
file_analysis = search.analyze_file("src/auth/handlers.py")
print(f"\nAnalyzing src/auth/handlers.py:")
print(f"  Functions: {[f.name for f in file_analysis.functions]}")
print(f"  Classes: {[c.name for c in file_analysis.classes]}")
print(f"  Imports: {[i.name for i in file_analysis.imports]}")

# Find what calls a function
dependencies = search.find_dependencies("src/auth/handlers.py", "validate_token")
print(f"\nFunctions that call validate_token:")
for dep in dependencies:
    print(f"  - {dep}")
```

**Output Example:**
```
Found 5 authentication functions:
  - authenticate (function)
    Score: 0.95
    Location: src/auth/handlers.py:42
    Doc: Authenticate a user with username and password...

  - login (function)
    Score: 0.87
    Location: src/auth/routes.py:15
    Doc: Login endpoint that calls authenticate...

Found 3 handler classes:
  - AuthHandler in src/auth/handlers.py
    Dependencies: ['BaseHandler']

  - JWTHandler in src/auth/jwt_handler.py
    Dependencies: ['Handler', 'AuthMixin']

Analyzing src/auth/handlers.py:
  Functions: ['authenticate', 'validate_token', 'refresh_token']
  Classes: ['AuthHandler', 'TokenValidator']
  Imports: ['jwt', 'datetime', 'typing']

Functions that call validate_token:
  - authenticate
  - refresh_token
```

---

## Tutorial 2: Searching a JavaScript/TypeScript Codebase

### Example: Finding React Components and Hooks

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

# Index JavaScript/TypeScript project
search = TreeSitterCodeSearch("./my_react_app", language="javascript")
search.build_index()

# Find all React components (functions/classes that import React)
print("React Components:")
functions = search.search_by_type("function")
for result in functions:
    if "Component" in result.unit.name or "Page" in result.unit.name:
        print(f"  - {result.unit.name}")
        print(f"    Dependencies: {result.unit.dependencies}")

# Find custom hooks
print("\nCustom Hooks:")
hooks = search.search("use", limit=30)
for result in hooks:
    if result.unit.name.startswith("use"):
        print(f"  - {result.unit.name} ({result.unit.file_path})")

# Find state management (useState, useContext, etc.)
state_results = search.search("useState", limit=50)
print(f"\nComponents using useState: {len(state_results)}")

# Find imports from specific packages
react_imports = []
for result in search.search_by_type("import_es6"):
    if "react" in result.unit.name.lower():
        react_imports.append(result.unit)

print(f"\nReact imports found: {len(react_imports)}")
for imp in react_imports[:5]:
    print(f"  - {imp.signature}")

# Analyze a component file
component_analysis = search.analyze_file("src/components/UserProfile.tsx")
print(f"\nUserProfile.tsx contains:")
print(f"  Functions: {[f.name for f in component_analysis.functions]}")
print(f"  Classes: {[c.name for c in component_analysis.classes]}")
for func in component_analysis.functions:
    if func.docstring:
        print(f"    - {func.name}: {func.docstring}")
```

**Output Example:**
```
React Components:
  - UserProfile
    Dependencies: ['useState', 'useEffect', 'fetchUser']

  - Dashboard
    Dependencies: ['useContext', 'AppContext']

Custom Hooks:
  - useAuth (src/hooks/useAuth.ts)
  - useLocalStorage (src/hooks/useLocalStorage.ts)
  - useApi (src/hooks/useApi.ts)

Components using useState: 27

React imports found: 12
  - import React from 'react'
  - import { useState, useEffect } from 'react'
  - import { useContext } from 'react'

UserProfile.tsx contains:
  Functions: ['UserProfile', 'loadUser', 'handleUpdate']
  Classes: []
    - UserProfile: Displays user profile with edit capability
    - loadUser: Fetches user data from API
    - handleUpdate: Updates user profile on server
```

---

## Tutorial 3: Searching a Java Codebase

### Example: Finding REST Endpoints and Database Operations

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

# Index Java project
search = TreeSitterCodeSearch("./my_java_app", language="java")
search.build_index()

# Find all classes that implement interfaces (likely service/handler classes)
print("Service Classes:")
classes = search.search_by_type("class")
for result in classes:
    if result.unit.dependencies:
        print(f"  - {result.unit.name}")
        print(f"    Implements: {result.unit.dependencies}")
        print(f"    Location: {result.unit.file_path}")

# Find REST endpoints (methods with RequestMapping/GetMapping annotations)
print("\nREST Endpoints (methods containing 'get', 'post', 'put', 'delete'):")
for action in ["get", "post", "put", "delete"]:
    results = search.search(action, query_type="method", limit=20)
    if results:
        print(f"\n  {action.upper()} endpoints:")
        for result in results[:5]:
            print(f"    - {result.unit.name} in {result.unit.file_path}")

# Find database operations
print("\nDatabase Operations:")
db_operations = search.search("save delete update query", limit=30)
for result in db_operations:
    if any(keyword in result.unit.name.lower() for keyword in ["save", "delete", "find", "query"]):
        print(f"  - {result.unit.name} ({result.unit.type})")

# Find classes that extend a specific base class
print("\nRepository Classes:")
repos = search.search("Repository", limit=20)
for result in repos:
    if "Repository" in result.unit.name:
        print(f"  - {result.unit.name}")
        if result.unit.dependencies:
            print(f"    Base: {result.unit.dependencies}")

# Analyze imports to understand dependencies
print("\nKey Dependencies:")
imports = search.search_by_type("import")
important_packages = ["springframework", "hibernate", "junit", "lombok"]
for imp in imports:
    for pkg in important_packages:
        if pkg in imp.unit.name.lower():
            print(f"  - {imp.unit.name}")
```

**Output Example:**
```
Service Classes:
  - UserService
    Implements: ['IUserService']
    Location: src/main/java/com/example/service/UserService.java

  - AuthController
    Implements: ['IAuthController', 'AuthProvider']
    Location: src/main/java/com/example/controller/AuthController.java

REST Endpoints (methods containing 'get', 'post', 'put', 'delete'):

  GET endpoints:
    - getUser in UserController.java
    - getUserById in UserController.java
    - getAllUsers in UserController.java

  POST endpoints:
    - createUser in UserController.java
    - login in AuthController.java

Database Operations:
  - saveUser (method)
  - deleteUser (method)
  - findById (method)
  - queryByEmail (method)

Repository Classes:
  - UserRepository
    Base: ['JpaRepository']

  - OrderRepository
    Base: ['CrudRepository']

Key Dependencies:
  - org.springframework.stereotype
  - org.springframework.web.bind.annotation
  - org.hibernate.annotations
  - org.junit.jupiter.api
  - lombok
```

---

## Tutorial 4: Searching a Go Codebase

### Example: Finding Handlers, Middleware, and Interfaces

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

# Index Go project
search = TreeSitterCodeSearch("./my_go_app", language="go")
search.build_index()

# Find HTTP handlers (functions with *http.Request parameter)
print("HTTP Handlers:")
handlers = search.search("Handler", limit=30)
for result in handlers:
    if "Handler" in result.unit.name or "handler" in result.unit.name.lower():
        print(f"  - {result.unit.name}")
        print(f"    Location: {result.unit.file_path}")
        if result.unit.dependencies:
            print(f"    Calls: {list(result.unit.dependencies)[:3]}")

# Find middleware functions
print("\nMiddleware Functions:")
middleware = search.search("middleware func", limit=20)
for result in middleware:
    if "Middleware" in result.unit.name:
        print(f"  - {result.unit.name}")

# Find interface definitions (common patterns in Go)
print("\nInterfaces:")
interfaces = search.search_by_type("interface")
for result in interfaces[:10]:
    print(f"  - {result.unit.name}")
    if result.unit.dependencies:
        print(f"    Methods: {result.unit.dependencies}")

# Find main function and package structure
print("\nPackage Structure:")
main_funcs = search.search("main", query_type="function")
for result in main_funcs:
    if result.unit.name == "main":
        print(f"  Entry point: {result.unit.file_path}")
        print(f"  Calls: {list(result.unit.dependencies)[:5]}")

# Find error handling patterns
print("\nError Handling:")
error_results = search.search("error", limit=50)
error_functions = [r for r in error_results if "error" in r.unit.name.lower()]
print(f"  Functions handling errors: {len(error_functions)}")
for result in error_functions[:5]:
    print(f"    - {result.unit.name}")

# Find database connection patterns
print("\nDatabase Operations:")
db_ops = search.search("database query connection", limit=30)
for result in db_ops:
    if any(op in result.unit.name.lower() for op in ["query", "insert", "update", "delete"]):
        print(f"  - {result.unit.name} ({result.unit.type})")

# Analyze a handler file
print("\nAnalyzing user_handler.go:")
analysis = search.analyze_file("internal/handler/user_handler.go")
for func in analysis.functions:
    print(f"  - {func.name}")
    if func.docstring:
        print(f"    {func.docstring}")
```

**Output Example:**
```
HTTP Handlers:
  - GetUserHandler
    Location: internal/handler/user_handler.go
    Calls: ['db.Query', 'json.Marshal', 'http.Error']

  - CreateUserHandler
    Location: internal/handler/user_handler.go
    Calls: ['json.Unmarshal', 'db.Insert', 'json.Marshal']

Middleware Functions:
  - AuthMiddleware
  - LoggingMiddleware
  - CORSMiddleware

Interfaces:
  - Reader
    Methods: ['Read']

  - Writer
    Methods: ['Write']

  - Handler
    Methods: ['ServeHTTP']

Package Structure:
  Entry point: cmd/main.go
  Calls: ['internal/app.Run', 'config.Load', 'server.Start']

Error Handling:
  Functions handling errors: 23
    - parseError
    - handleError
    - errorResponse
    - validateError
    - logError

Database Operations:
  - queryUser (function)
  - insertUser (function)
  - updateUser (function)
  - deleteUser (function)

Analyzing user_handler.go:
  - GetUser
    Get user by ID from database
  - CreateUser
    Create a new user
  - UpdateUser
    Update user information
  - DeleteUser
    Delete user from database
```

---

## Tutorial 5: Multi-Language Codebase Analysis

### Example: Analyzing a Microservices Architecture

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

# Analyze a polyglot microservices project with Python, JavaScript, Java, and Go

print("=== MICROSERVICES ARCHITECTURE ANALYSIS ===\n")

# 1. Python Backend Services
print("Python Services (API Gateway, Data Processing):")
py_search = TreeSitterCodeSearch("./services/python", language="python")
py_search.build_index()
py_stats = py_search.get_code_statistics()
print(f"  Files: {py_stats.total_files}")
print(f"  Functions: {len([u for u in py_stats.units if u.type == 'function'])}")
print(f"  Classes: {len([u for u in py_stats.units if u.type == 'class'])}")

# 2. JavaScript Frontend and Node Services
print("\nJavaScript/TypeScript Services (Frontend, API Server):")
js_search = TreeSitterCodeSearch("./services/javascript", language="javascript")
js_search.build_index()
js_stats = js_search.get_code_statistics()
print(f"  Files: {js_stats.total_files}")
print(f"  Functions: {len([u for u in js_stats.units if u.type == 'function'])}")
print(f"  Imports: {len([u for u in js_stats.units if 'import' in u.type])}")

# 3. Java Microservices
print("\nJava Microservices (Database, Cache Services):")
java_search = TreeSitterCodeSearch("./services/java", language="java")
java_search.build_index()
java_stats = java_search.get_code_statistics()
print(f"  Files: {java_stats.total_files}")
print(f"  Classes: {len([u for u in java_stats.units if u.type == 'class'])}")
print(f"  Service Classes: {len([u for u in java_stats.units if u.type == 'class' and 'Service' in u.name])}")

# 4. Go Services (CLI Tools, Utilities)
print("\nGo Services (CLI Tools, Workers):")
go_search = TreeSitterCodeSearch("./services/go", language="go")
go_search.build_index()
go_stats = go_search.get_code_statistics()
print(f"  Files: {go_stats.total_files}")
print(f"  Functions: {len([u for u in go_stats.units if u.type == 'function'])}")
print(f"  Interfaces: {len([u for u in go_stats.units if u.type == 'interface'])}")

# 5. Cross-Service Dependencies
print("\n=== CROSS-SERVICE DEPENDENCIES ===\n")

# Find authentication patterns across services
print("Authentication Implementation:")
for name, searcher in [("Python", py_search), ("JavaScript", js_search), ("Java", java_search), ("Go", go_search)]:
    auth_results = searcher.search("authenticate", limit=5)
    if auth_results:
        print(f"\n  {name}:")
        for result in auth_results[:2]:
            print(f"    - {result.unit.name} in {result.unit.file_path}")

# Find API endpoints across services
print("\n\nAPI Endpoints by Service:")
print("  Python API routes:", len(py_search.search("route", limit=50)))
print("  JavaScript API routes:", len(js_search.search("router", limit=50)))
print("  Java REST endpoints:", len(java_search.search("mapping", limit=50)))
print("  Go HTTP handlers:", len(go_search.search("handler", limit=50)))

# Find error handling patterns
print("\n\nError Handling Patterns:")
for name, searcher in [("Python", py_search), ("JavaScript", js_search), ("Java", java_search), ("Go", go_search)]:
    error_results = searcher.search("error exception", limit=10)
    print(f"  {name}: {len(error_results)} error handling functions")

# Summary
print("\n=== SYSTEM SUMMARY ===")
total_files = py_stats.total_files + js_stats.total_files + java_stats.total_files + go_stats.total_files
print(f"Total Files Analyzed: {total_files}")
print(f"Languages: Python, JavaScript/TypeScript, Java, Go")
print(f"Architecture: Microservices with polyglot implementation")
```

**Output Example:**
```
=== MICROSERVICES ARCHITECTURE ANALYSIS ===

Python Services (API Gateway, Data Processing):
  Files: 42
  Functions: 128
  Classes: 31

JavaScript/TypeScript Services (Frontend, API Server):
  Files: 67
  Functions: 156
  Imports: 89

Java Microservices (Database, Cache Services):
  Files: 35
  Classes: 58
  Service Classes: 14

Go Services (CLI Tools, Workers):
  Files: 18
  Functions: 52
  Interfaces: 8

=== CROSS-SERVICE DEPENDENCIES ===

Authentication Implementation:

  Python:
    - authenticate in auth/handlers.py
    - validate_token in auth/utils.py

  JavaScript:
    - authenticate in auth/service.ts
    - validateToken in auth/middleware.ts

  Java:
    - authenticate in AuthService.java
    - validateJWT in JWTValidator.java

  Go:
    - Authenticate in internal/auth/handler.go
    - ValidateToken in internal/auth/validator.go

API Endpoints by Service:
  Python API routes: 23
  JavaScript API routes: 31
  Java REST endpoints: 19
  Go HTTP handlers: 12

Error Handling Patterns:
  Python: 24 error handling functions
  JavaScript: 31 error handling functions
  Java: 18 error handling functions
  Go: 14 error handling functions

=== SYSTEM SUMMARY ===
Total Files Analyzed: 162
Languages: Python, JavaScript/TypeScript, Java, Go
Architecture: Microservices with polyglot implementation
```

---

## Advanced Usage Patterns

### Pattern 1: Finding Architectural Patterns

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

search = TreeSitterCodeSearch("./repo", language="python")
search.build_index()

# Singleton pattern (classes with getInstance/instance method)
print("Potential Singletons:")
singletons = search.search("getInstance instance", limit=50)
for result in singletons:
    if any(term in result.unit.name.lower() for term in ["manager", "config", "factory"]):
        print(f"  - {result.unit.name}")

# Observer pattern (classes with notify/subscribe methods)
print("\nObserver Pattern:")
observers = search.search("notify subscribe", limit=50)
for result in observers:
    if result.unit.type == "class":
        print(f"  - {result.unit.name}")

# Factory pattern (classes with create methods)
print("\nFactory Pattern:")
factories = search.search("factory create build", limit=50)
for result in factories:
    if "Factory" in result.unit.name or "Builder" in result.unit.name:
        print(f"  - {result.unit.name}")
```

### Pattern 2: Finding Test Coverage Gaps

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

source_search = TreeSitterCodeSearch("./src", language="python")
test_search = TreeSitterCodeSearch("./tests", language="python")

source_search.build_index()
test_search.build_index()

# Find functions without tests
print("Functions Potentially Without Tests:")
source_functions = set(u.name for u in source_search.get_code_statistics().units if u.type == "function")
test_functions = set(u.name for u in test_search.get_code_statistics().units)

untested = source_functions - test_functions
for func in sorted(untested)[:10]:
    print(f"  - {func}")
```

### Pattern 3: Finding Security-Sensitive Operations

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

search = TreeSitterCodeSearch("./src", language="python")
search.build_index()

# Find password operations
print("Password Handling:")
password_results = search.search("password hash encrypt", limit=50)
for result in password_results:
    print(f"  - {result.unit.name} in {result.unit.file_path}")

# Find database queries
print("\nDatabase Operations:")
db_results = search.search("query execute sql", limit=50)
for result in db_results:
    print(f"  - {result.unit.name}")

# Find authentication/authorization
print("\nAuth Operations:")
auth_results = search.search("auth permission role", limit=50)
for result in auth_results:
    print(f"  - {result.unit.name}")
```

### Pattern 4: Finding Performance Bottlenecks

```python
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

search = TreeSitterCodeSearch("./src", language="python")
search.build_index()

# Find loops that might be slow
print("Nested Loops (potential performance issues):")
nested_loop_patterns = search.search("for while loop", limit=100)
for result in nested_loop_patterns:
    if result.score > 0.8:  # High relevance
        print(f"  - {result.unit.name} (score: {result.score:.2f})")

# Find recursive functions
print("\nRecursive Functions:")
recursive = search.search("recursive call", limit=50)
for result in recursive:
    print(f"  - {result.unit.name}")

# Find expensive operations
print("\nExpensive Operations:")
expensive = search.search("sleep time wait block", limit=50)
for result in expensive:
    print(f"  - {result.unit.name}")
```

---

## Integration with Development Workflow

### Using with IDEs and Editors

```python
# IDE Integration Example - Find context for current file
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

def get_context_for_file(file_path, search_engine):
    """Get useful context information for a file being edited."""

    # Analyze the file
    analysis = search_engine.analyze_file(file_path)

    # Find related files (files that call functions in this file)
    related_files = set()
    for unit in analysis.functions:
        deps = search_engine.find_dependencies(file_path, unit.name)
        for dep in deps:
            related_files.add(dep)

    return {
        "file": file_path,
        "functions": [f.name for f in analysis.functions],
        "classes": [c.name for c in analysis.classes],
        "imports": [i.name for i in analysis.imports],
        "related_files": list(related_files)
    }

# Usage
search = TreeSitterCodeSearch("./project", language="python")
search.build_index()

context = get_context_for_file("src/auth/handlers.py", search)
print(f"Context for {context['file']}:")
print(f"  Functions: {context['functions']}")
print(f"  Related files: {context['related_files']}")
```

---

## Performance Tips

### 1. Efficient Searching

```python
# ❌ Slow: Many separate searches
results1 = search.search("authenticate")
results2 = search.search("validate")
results3 = search.search("check")

# ✅ Fast: Single combined search
results = search.search("authenticate validate check", limit=30)
```

### 2. Limiting Results

```python
# ❌ Slow: Getting all results
all_functions = search.search_by_type("function")  # Could be thousands

# ✅ Fast: Getting top N results
top_functions = search.search_by_type("function", limit=50)
```

### 3. Caching Results

```python
# The search engine caches results automatically
# Repeated searches are <0.05ms

# First search: ~50-100ms
results = search.search("authenticate")

# Second search (same query): <0.05ms (from cache)
results = search.search("authenticate")
```

### 4. Reusing Indexes

```python
# ❌ Slow: Rebuilding index each time
search1 = TreeSitterCodeSearch("./repo", language="python")
search1.build_index()  # ~100ms

search2 = TreeSitterCodeSearch("./repo", language="python")
search2.build_index()  # ~100ms again

# ✅ Fast: Reuse search engine
search = TreeSitterCodeSearch("./repo", language="python")
search.build_index()  # ~100ms
results1 = search.search("query1")  # <100ms
results2 = search.search("query2")  # <100ms
```

---

## Troubleshooting

### Issue: No results found

**Solution**: Check if the index was built and file patterns match:
```python
stats = search.get_code_statistics()
print(f"Indexed files: {stats.total_files}")
print(f"Total units: {stats.total_units}")

# If 0 files, check file extensions and skip patterns
```

### Issue: Slow search performance

**Solution**: Check cache stats and consider limiting results:
```python
stats = search.get_cache_stats()
print(f"Cache hit rate: {stats.hit_rate:.2%}")

# Use smaller limit for faster results
results = search.search("query", limit=10)
```

### Issue: False positives in results

**Solution**: Use more specific search terms and check scores:
```python
# Less specific
results = search.search("handler")  # Matches many things

# More specific
results = search.search("HTTP request handler authenticate")  # More targeted

# Filter by score
high_confidence = [r for r in results if r.score > 0.7]
```

---

## Summary

The multi-language code search system provides:

- **Unified API** across Python, JavaScript, Java, and Go
- **Fast Performance** (<5ms parsing, <100ms search)
- **Flexible Queries** for semantic, type-based, and name-based search
- **Rich Context** with docstrings, dependencies, and code analysis
- **Production Ready** with comprehensive testing and documentation

For more information, see:
- `docs/PHASE3_COMPLETE.md` - Architecture and design
- `README.md` - Quick start guide
- API Reference in individual parser files

---

**Status**: ✅ Usage Examples Complete
**Version**: 1.0
**Updated**: November 7, 2025
