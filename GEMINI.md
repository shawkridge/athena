
# GEMINI-CLI: The Athena Paradigm

This document serves as the global baseline for the `gemini-cli` agent, outlining the operational philosophy and the technical paradigms for interacting with the Athena memory system. It is the source of truth for how `gemini-cli` achieves the same outcomes as `claude-code` within this environment.

---

## 1. Core Philosophy

The fundamental goal is not just to execute commands, but to be a craftsman. Every action should be planned, elegant, and robust.

- **Think First:** Before executing, understand the goal. Read the context, form a hypothesis, and create a clear plan.
- **Test-Driven Development:** When writing or modifying code, tests are the ground truth. Write tests that define the desired reality, then write the code to match.
- **Simplify Ruthlessly:** The best solution is often the one with the least complexity. When there is nothing left to take away, elegance is achieved.
- **Trust The System:** Athena's memory and hook system are designed to provide context and facilitate learning. Trust that the information they provide is relevant.

---

## 2. Hook Integration with Athena

`gemini-cli` is integrated with Athena's memory system using a global hooks configuration. This is managed by the `/home/user/.gemini/settings.json` file.

This setup was performed by the `install_gemini_hooks.sh` script, which maps `gemini-cli`'s lifecycle events to Athena's memory scripts:

| `gemini-cli` Hook | Athena Script (`claude/hooks/`) | Purpose |
| :--- | :--- | :--- |
| `SessionStart` | `session-start.sh` | Loads working memory at the start of a session. |
| `BeforeModel` | `user-prompt-submit.sh` | Records the user's prompt before it's sent to the model. |
| `AfterTool` | `post-tool-use.sh`| Records the results of a tool call into episodic memory. |
| `SessionEnd` | `session-end.sh` | Consolidates learnings into semantic memory when the session ends. |

This ensures that `gemini-cli`'s activity automatically populates Athena's memory, enabling cross-session learning and context.

---

## 3. The Athena Access Paradigm for `gemini-cli`

This is the most critical section. It details how `gemini-cli` must access Athena's memory.

### The Core Difference

- **`claude-code`:** Operates in an environment with implicit **Dependency Injection**. When its tools call `UnifiedMemoryManager()`, a pre-configured instance is magically provided.
- **`gemini-cli`:** Does not have this magic. It must act as a standard Python application and perform **Manual Dependency Injection**.

### The `gemini-cli` Method: Manual Construction via `run_shell_command`

To access Athena's memory, `gemini-cli` must use the `run_shell_command` tool to execute a Python script that manually constructs the `UnifiedMemoryManager` and all of its dependencies.

**This is the canonical template for accessing Athena memory:**

```python
# Set the PYTHONPATH to ensure the 'athena' module can be imported
export PYTHONPATH=/home/user/.work/athena/src:$PYTHONPATH

# Execute the Python script
python -c '
import asyncio
import json
import logging
from athena.core.database import Database
from athena.semantic.store import SemanticStore
from athena.episodic.store import EpisodicStore
from athena.procedural.store import ProceduralStore
from athena.prospective.store import ProspectiveStore
from athena.graph.store import GraphStore
from athena.meta.store import MetaMemoryStore
from athena.consolidation.system import ConsolidationSystem
from athena.projects.manager import ProjectManager
from athena.manager import UnifiedMemoryManager

# Suppress verbose logging for a clean output
logging.basicConfig(level=logging.WARNING)

async def main():
    try:
        # 1. Initialize the Database connection
        db = Database()
        await db.initialize()

        # 2. Instantiate all stores and managers, providing dependencies as discovered.
        #    - Some stores get the DB via internal factory (e.g., SemanticStore).
        #    - Others require the `db` object to be passed in.
        #    - Some managers require other stores.
        
        semantic_store = SemanticStore()
        project_manager = ProjectManager(store=semantic_store) # Depends on SemanticStore
        
        episodic_store = EpisodicStore(db=db)
        procedural_store = ProceduralStore(db=db)
        prospective_store = ProspectiveStore(db=db)
        graph_store = GraphStore(db=db)
        meta_store = MetaMemoryStore(db=db)
        
        consolidation_system = ConsolidationSystem(
            db=db,
            memory_store=semantic_store, # Requires SemanticStore via `memory_store` arg
            episodic_store=episodic_store,
            procedural_store=procedural_store,
            meta_store=meta_store,
            graph_store=graph_store
        )

        # 3. Instantiate the UnifiedMemoryManager with all its dependencies
        manager = UnifiedMemoryManager(
            semantic=semantic_store,
            episodic=episodic_store,
            procedural=procedural_store,
            prospective=prospective_store,
            graph=graph_store,
            meta=meta_store,
            consolidation=consolidation_system,
            project_manager=project_manager
        )
        
        # 4. Call the desired method on the fully constructed manager
        #    Example: Call the recall() method
        results = manager.recall("your query here", k=5)
        
        # 5. Print the results as JSON to be captured by the tool output
        print(json.dumps(results, indent=2, default=str))

    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "trace": traceback.format_exc()}, default=str))

if __name__ == "__main__":
    asyncio.run(main())
'
```

This template should be used for any interaction with Athena's memory, such as `recall`, `remember`, etc., by modifying step 4.
