#!/usr/bin/env python3
"""
Auto-inject relevant memories into conversation context.

Replaces manual /memory-query with automatic context injection.
When a new user prompt arrives, automatically discovers and injects
relevant memories from all layers into the conversation context.
"""

import sys
import json
import argparse
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO if not sys.stderr.isatty() else logging.WARNING,
    format='%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def get_athena_path() -> Path:
    """Get path to Athena memory project."""
    # Check for Athena at new location first
    athena_path = Path.home() / ".work" / "athena"
    if athena_path.exists():
        return athena_path

    # Fallback to old location for backwards compatibility
    old_path = Path.home() / ".work" / "claude" / "memory-mcp"
    if old_path.exists():
        return old_path

    # Fallback to current working directory
    return Path.cwd()


def setup_imports():
    """Add memory-mcp to path for imports."""
    memory_path = get_athena_path()
    src_path = memory_path / "src"

    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


async def inject_memory_context(
    user_prompt: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    cwd: Optional[str] = None,
    project_id: Optional[int] = None,
    token_budget: int = 1000,
    min_usefulness: float = 0.4,
    max_memories: int = 5,
) -> Dict[str, Any]:
    """
    Inject relevant memories into conversation context.

    Args:
        user_prompt: The user's question/request
        conversation_history: Recent conversation for context
        cwd: Current working directory for project detection
        project_id: Project ID for filtering (auto-detected if not provided)
        token_budget: Max tokens for injected context
        min_usefulness: Minimum usefulness score to include
        max_memories: Maximum memories to inject per prompt

    Returns:
        Dict with formatted context and injection details
    """
    try:
        from athena.core.database import Database
        from athena.memory.store import MemoryStore
        from athena.rag.context_injector import ContextInjector
        from athena.rag.manager import RAGManager
        from athena.rag.llm_client import OllamaLLMClient

        # Initialize database
        db_path = Path.home() / ".athena" / "memory.db"
        db = Database(str(db_path))

        # Initialize memory store (required by RAGManager)
        memory_store = MemoryStore(str(db_path))

        # Initialize LLM client for advanced RAG features (HyDE, etc.)
        # Uses Ollama for local inference - optimized for memory-constrained systems
        llm_client = None

        # DEBUGGING: Set to True to disable LLM and test basic search
        DISABLE_LLM_FOR_TESTING = False

        if not DISABLE_LLM_FOR_TESTING:
            try:
                # Try Qwen2.5 1.5B (RAG-optimized, tiny footprint, 2025 release)
                llm_client = OllamaLLMClient(model="qwen2.5:1.5b-instruct-q4_K_M")
                logger.info("Using Qwen2.5 1.5B for HyDE and query expansion")
            except Exception as e:
                try:
                    # Fallback to Llama 3.2 3B
                    llm_client = OllamaLLMClient(model="llama2:3b-instruct-q4_K_M")
                    logger.warning(f"Qwen2.5 not available, using Llama 3.2: {e}")
                except Exception as e2:
                    try:
                        # Last fallback to whatever models we have
                        llm_client = OllamaLLMClient(model="neural-chat")
                        logger.warning(f"No optimized models available, using neural-chat: {e2}")
                    except Exception as e3:
                        logger.warning(f"No LLM client available, using basic RAG: {e3}")
                        llm_client = None
        else:
            logger.warning("LLM disabled for testing - using basic RAG only")

        # Initialize RAG manager with LLM client for advanced features
        rag_manager = RAGManager(
            memory_store=memory_store,
            llm_client=llm_client
        )

        # Create context injector
        injector = ContextInjector(
            db=db,
            rag_manager=rag_manager,
            token_budget=token_budget,
            min_usefulness=min_usefulness,
            max_memories=max_memories,
        )

        # Decide if we should inject context
        recent_injections = 0  # In real scenario, track this
        should_inject = await injector.should_inject_context(
            user_prompt=user_prompt,
            recent_injections=recent_injections,
        )

        if not should_inject:
            return {
                "status": "skipped",
                "reason": "frequency_control",
                "formatted_context": "",
                "memories": [],
                "confidence": 0.0,
            }

        # Inject context
        injection = await injector.inject_context(
            user_prompt=user_prompt,
            conversation_history=conversation_history,
            project_id=project_id,
        )

        # Format for Claude
        formatted = injector.format_injection_for_claude(injection)

        return {
            "status": "success",
            "formatted_context": formatted,
            "memories": [
                {
                    "content": mem.content,
                    "source_layer": mem.source_layer,
                    "usefulness": mem.usefulness,
                    "relevance": mem.relevance,
                    "recency": mem.recency,
                }
                for mem in injection.memories
            ],
            "total_tokens": injection.total_tokens,
            "injection_confidence": injection.injection_confidence,
            "memory_count": len(injection.memories),
        }

    except Exception as e:
        logger.error(f"Context injection failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "formatted_context": "",
            "memories": [],
            "confidence": 0.0,
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Auto-inject relevant memories into conversation context"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="User query/prompt"
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Current working directory"
    )
    parser.add_argument(
        "--project-id",
        type=int,
        help="Project ID for filtering"
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=1000,
        help="Max tokens for injected context"
    )
    parser.add_argument(
        "--min-usefulness",
        type=float,
        default=0.4,
        help="Minimum usefulness score to include"
    )
    parser.add_argument(
        "--max-memories",
        type=int,
        default=5,
        help="Maximum memories to inject"
    )
    parser.add_argument(
        "--conversation-history",
        help="JSON-encoded conversation history"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format"
    )

    args = parser.parse_args()

    # Setup imports
    setup_imports()

    # Parse conversation history if provided
    conversation_history = None
    if args.conversation_history:
        try:
            conversation_history = json.loads(args.conversation_history)
        except json.JSONDecodeError:
            logger.warning("Failed to parse conversation history")

    # Run injection
    result = await inject_memory_context(
        user_prompt=args.query,
        conversation_history=conversation_history,
        cwd=args.cwd,
        project_id=args.project_id,
        token_budget=args.token_budget,
        min_usefulness=args.min_usefulness,
        max_memories=args.max_memories,
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["status"] == "success":
            print(f"Injected {result['memory_count']} memories")
            print(f"Confidence: {result['injection_confidence']:.0%}")
            if result["formatted_context"]:
                print(result["formatted_context"])
        elif result["status"] == "skipped":
            print(f"Skipped: {result['reason']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

    return 0 if result["status"] in ("success", "skipped") else 1


if __name__ == "__main__":
    setup_imports()
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
