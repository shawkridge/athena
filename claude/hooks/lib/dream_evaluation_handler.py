"""
Handle Claude's dream evaluation responses.

This module is called by post-response.sh hook when Claude evaluates dreams.
It parses the evaluation response and stores the results in the dream store.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.expanduser("~/.work/athena/src"))

from athena.core.database import Database
from athena.consolidation.dream_store import DreamStore
from athena.consolidation.dream_evaluation_parser import parse_dream_evaluations
from athena.consolidation.dream_models import DreamStatus, DreamTier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def handle_dream_evaluation(response_text: str) -> dict:
    """
    Process a Claude evaluation response for dreams.

    Args:
        response_text: Claude's response text

    Returns:
        Summary dict with results
    """
    logger.info("Processing dream evaluation response...")

    try:
        # Parse evaluations from response
        evaluations = parse_dream_evaluations(response_text)
        logger.info(f"Parsed {len(evaluations)} dream evaluations")

        if not evaluations:
            return {
                "success": False,
                "message": "No evaluations could be parsed from response",
                "dreams_updated": 0
            }

        # Initialize database
        db = Database()
        dream_store = DreamStore(db)

        # Get all pending dreams
        pending_dreams = await dream_store.get_pending_evaluation(limit=1000)
        pending_by_id = {d.id: d for d in pending_dreams}
        pending_by_name = {d.base_procedure_name: d for d in pending_dreams}

        logger.info(f"Found {len(pending_dreams)} pending dreams in database")

        # Update dreams with evaluations
        updated_count = 0

        for eval in evaluations:
            dream = None

            # Try to find dream by ID or name
            try:
                dream_id = int(eval.dream_id_or_name)
                dream = pending_by_id.get(dream_id)
            except ValueError:
                # Not an ID, try by name
                dream = pending_by_name.get(eval.dream_id_or_name)

            if not dream:
                logger.warning(f"Dream not found: {eval.dream_id_or_name}")
                continue

            # Validate evaluation
            valid, error_msg = _validate_evaluation(eval)
            if not valid:
                logger.warning(f"Invalid evaluation for {eval.dream_id_or_name}: {error_msg}")
                continue

            # Update dream with evaluation
            dream.status = DreamStatus.EVALUATED
            dream.tier = DreamTier(eval.tier)
            dream.viability_score = eval.viability_score
            dream.claude_reasoning = eval.reasoning
            dream.evaluated_at = datetime.now()

            # Store update
            await dream_store.update_dream(dream)
            updated_count += 1

            logger.info(
                f"Updated dream {dream.name}: tier {eval.tier}, "
                f"viability {eval.viability_score}"
            )

        logger.info(f"Successfully updated {updated_count} dreams")

        return {
            "success": True,
            "message": f"Updated {updated_count} dreams with evaluations",
            "dreams_updated": updated_count,
            "dreams_parsed": len(evaluations)
        }

    except Exception as e:
        logger.error(f"Error processing dream evaluation: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "dreams_updated": 0
        }


def _validate_evaluation(eval) -> tuple:
    """Validate an evaluation for correctness."""
    if not eval.dream_id_or_name:
        return False, "Missing dream identifier"

    if not (0.0 <= eval.viability_score <= 1.0):
        return False, f"Viability score {eval.viability_score} out of range"

    if eval.tier not in (1, 2, 3):
        return False, f"Tier {eval.tier} not in [1, 2, 3]"

    if not eval.reasoning:
        return False, "Missing reasoning"

    return True, ""


def main():
    """Main entry point for hook."""
    import asyncio

    # Get response from environment or stdin
    response = os.environ.get("CLAUDE_RESPONSE", "")

    if not response:
        # Try reading from stdin
        response = sys.stdin.read()

    if not response:
        logger.warning("No response text provided")
        sys.exit(1)

    # Check if this is a dream evaluation (contains viability scores, tiers, etc.)
    dream_keywords = ["viability", "tier", "viable", "speculative", "archive", "dream"]
    is_dream_eval = any(keyword in response.lower() for keyword in dream_keywords)

    if not is_dream_eval:
        logger.debug("Response does not appear to be a dream evaluation, skipping")
        sys.exit(0)

    # Process the evaluation
    result = asyncio.run(handle_dream_evaluation(response))

    logger.info(f"Result: {result}")

    # Output result for the hook to capture
    print(json.dumps(result))

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
