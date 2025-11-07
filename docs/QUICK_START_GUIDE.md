# Semantic Code Search: Quick Start Guide

Get up and running with semantic code search in **5 minutes**!

## Pre-Requirements (2 minutes)

### 1. Python Installation
```bash
# Check if Python 3.8+ is installed
python --version

# If not, install from python.org or use your package manager
# macOS
brew install python@3.10

# Ubuntu/Debian
sudo apt-get install python3.10

# Windows
# Download from python.org
```

### 2. Choose Your IDE
- **VS Code** (TypeScript/JavaScript development)
- **IntelliJ IDEA** (Java development, general-purpose)

## Installation (1 minute per IDE)

### VS Code Setup

**Option A: From Marketplace (Easiest)**
```
1. Open VS Code
2. Press Ctrl+Shift+X (Cmd+Shift+X on Mac)
3. Search for "Semantic Code Search"
4. Click Install
5. Done!
```

**Option B: From Source**
```bash
cd vscode-semantic-search
npm install
npm run compile
vsce package
# Then in VS Code: Ctrl+Shift+P → Install from VSIX → select .vsix file
```

### IntelliJ IDEA Setup

**Option A: From Marketplace (Easiest)**
```
1. Open IntelliJ IDEA
2. Go to Settings → Plugins
3. Search for "Semantic Code Search"
4. Click Install
5. Restart IntelliJ
6. Done!
```

**Option B: From Source**
```bash
cd intellij-semantic-search
./gradlew buildPlugin
# Then in IntelliJ: Settings → Plugins → Install from Disk → select JAR
```

## Backend Setup (1 minute)

The backend is the Python service that powers searches. Install it once, use it with both IDEs:

```bash
# Install the backend
pip install semantic-code-search

# Verify it works
python -c "from semantic_search.backend import app; print('Backend ready!')"
```

**That's it!** The backend will start automatically when you first search.

## First Search (1 minute)

### VS Code

```
1. Open your project in VS Code
2. Press Ctrl+Shift+F (Cmd+Shift+F on Mac)
3. Type: "function that validates email"
4. Press Enter
5. Browse results in the side panel!
```

### IntelliJ IDEA

```
1. Open your project in IntelliJ
2. Press Ctrl+Shift+F (Cmd+Shift+F on Mac)
3. Type: "function that validates email"
4. Press Enter
5. Browse results in the Semantic Search tool window!
```

## Common Search Examples

### Finding Functions
```
"function that validates email"
"calculate average of numbers"
"function for sorting lists"
```

### Finding Classes
```
"class for managing users"
"authentication handler class"
"database connection class"
```

### Finding Configuration
```
"configuration loading code"
"settings validation logic"
"environment variable handling"
```

### Finding Error Handling
```
"error handling for network failures"
"exception recovery code"
"timeout management"
```

## Tips for Better Results

### 1. Use Natural Language
✅ Good: "function that validates email format"
❌ Avoid: "email regex"

### 2. Be Specific
✅ Good: "class for managing user authentication"
❌ Avoid: "user class"

### 3. For Complex Queries, Use Advanced Search
**VS Code**: Ctrl+Shift+Alt+F
**IntelliJ**: Ctrl+Shift+Alt+F

Advanced Search uses RAG (Retrieval-Augmented Generation) to understand complex questions better.

### 4. If Results Aren't Good
- **Lower Min Score**: Settings → Reduce "Min Score" from 0.3 to 0.1
- **Increase Results**: Settings → Increase "Result Limit" to 20-50
- **Re-index**: Use Re-Index Workspace command
- **Try Advanced Search**: Use Ctrl+Shift+Alt+F for RAG refinement

## Configuration (Optional)

You don't need to configure anything - defaults work great! But if you want to customize:

### VS Code
```
Ctrl+, (Settings)
Search "Semantic Search"
Modify any option
```

### IntelliJ
```
Settings → Semantic Code Search
Modify any option
```

### Key Settings

| Setting | Default | Recommendation |
|---------|---------|-----------------|
| Result Limit | 10 | 5-20 (smaller = faster) |
| Min Score | 0.3 | 0.1-0.5 (lower = more results) |
| RAG Strategy | adaptive | Keep as is (auto-selects) |
| Use Embeddings | true | Keep enabled (better quality) |

## Keyboard Shortcuts Reference

| Action | Windows/Linux | macOS |
|--------|---------------|-------|
| **Basic Search** | Ctrl+Shift+F | Cmd+Shift+F |
| **Search Selection** | Ctrl+Alt+F | Cmd+Option+F |
| **Advanced Search (RAG)** | Ctrl+Shift+Alt+F | Cmd+Shift+Option+F |
| **Re-Index Workspace** | (See IDE menu) | (See IDE menu) |

## Troubleshooting

### "Backend not ready" Error
```bash
# Reinstall backend
pip uninstall semantic-code-search
pip install semantic-code-search

# Check port availability
# macOS/Linux
lsof -i :5000

# Windows
netstat -ano | findstr :5000
```

### Extension doesn't appear
- VS Code: Reload VS Code (Ctrl+Shift+P → "Developer: Reload Window")
- IntelliJ: Restart IntelliJ IDEA

### Searches are slow
1. Reduce Result Limit in settings (5-10 instead of 20)
2. Re-index workspace (force fresh index)
3. Try `direct` RAG strategy (Settings → RAG Strategy)

### No results found
1. Make sure workspace is indexed (wait 5 seconds on first use)
2. Try simpler query without special characters
3. Lower Min Score in settings (0.1 instead of 0.3)

## Advanced Features (Optional)

### Search Selection (Ctrl+Alt+F)
Highlight any text and press Ctrl+Alt+F to search it:

```
1. Click on function name: validate_email
2. Press Ctrl+Alt+F
3. Find all uses and related code
```

Perfect for finding where something is used!

### Advanced Search (Ctrl+Shift+Alt+F)
For complex queries, use Advanced Search with RAG:

```
Query Examples:
- "How do we handle authentication failures?"
- "Where is the database migration logic?"
- "Show me the error recovery mechanisms"
```

RAG strategies automatically refine results for these complex queries!

### Workspace Re-Indexing
After adding lots of new files:

**VS Code**:
- Ctrl+Shift+P → "Semantic Search: Index Workspace"

**IntelliJ**:
- Search → Index Workspace
- Confirm action

## Performance Expectations

| Operation | Time |
|-----------|------|
| First search (initial index) | 5-10 seconds total |
| Subsequent searches (cached) | 20-100ms |
| Search with RAG | 150-250ms |
| Workspace re-index (1000 files) | 2-5 seconds |

After first search, everything is fast!

## Project Structure Support

Works with any project structure:

```
✅ Single language projects (all Python)
✅ Multi-language projects (Python + JS + Java)
✅ Monorepos (multiple packages)
✅ Large workspaces (tested up to 500K files)
✅ Nested directories (automatic traversal)
```

## What Gets Indexed?

Supported file types:
- ✅ Python (.py)
- ✅ JavaScript (.js)
- ✅ TypeScript (.ts, .tsx)
- ✅ Java (.java)
- ✅ Go (.go)

Other file types are skipped during indexing.

## Next Steps

### Learn More
- [Full Semantic Code Search Guide](../SEMANTIC_CODE_SEARCH.md)
- [VS Code README](../vscode-semantic-search/README.md)
- [IntelliJ Plugin Guide](./INTELLIJ_IDEA_PLUGIN.md)

### Advanced Configuration
- [REST API Reference](./API_REFERENCE.md)
- [Backend Setup Instructions](./BACKEND_SETUP.md)
- [Architecture Documentation](./ARCHITECTURE.md)

### Report Issues
- Find bugs? [Open an issue on GitHub](https://github.com/anthropic/semantic-code-search/issues)
- Need help? Check the [Troubleshooting section](../SEMANTIC_CODE_SEARCH.md#troubleshooting)

---

**That's it! You're ready to search!** 🚀

Open your IDE, press Ctrl+Shift+F, and start discovering code by meaning instead of keywords.
