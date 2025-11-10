"""Extract and learn from architectural decisions in code and git history."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """A single decision with context and outcomes."""
    title: str
    context: str  # Why this decision was needed
    chosen_option: str  # What was chosen
    rejected_options: List[str]  # What wasn't chosen
    rationale: str  # Why this choice was made
    outcomes: List[str]  # What happened as a result
    timestamp: str
    file_references: List[str]


class DecisionExtractor:
    """Extracts decisions from commits, code, and documentation."""

    def __init__(self):
        """Initialize decision extractor."""
        self.decisions: Dict[str, Decision] = {}

    def extract_from_commit(self, commit_message: str) -> Optional[Decision]:
        """Extract decision from commit message.

        Args:
            commit_message: Git commit message

        Returns:
            Decision object or None
        """
        try:
            lines = commit_message.strip().split("\n")

            # First line is title
            title = lines[0]

            # Look for decision indicators
            if not any(word in title.lower() for word in ["refactor", "migrate", "add", "implement", "change"]):
                return None

            # Extract context and rationale
            body = "\n".join(lines[1:])

            decision = Decision(
                title=title,
                context=self._extract_context(body),
                chosen_option=self._extract_choice(title, body),
                rejected_options=self._extract_rejected(body),
                rationale=self._extract_rationale(body),
                outcomes=self._extract_outcomes(body),
                timestamp="",  # Set by caller
                file_references=[],
            )

            return decision

        except Exception as e:
            logger.debug(f"Error extracting decision: {e}")
            return None

    def extract_pattern_decisions(self) -> List[Decision]:
        """Extract architectural decisions from common patterns."""
        decisions = []

        # Common architectural decisions
        common_patterns = [
            {
                "title": "Async/Await vs Callbacks",
                "context": "How to handle asynchronous operations",
                "options": ["Async/Await", "Callbacks", "Promises", "Generators"],
                "pros": {
                    "Async/Await": ["Cleaner syntax", "Better error handling", "Easier debugging"],
                    "Callbacks": ["Simple", "Lightweight"],
                },
                "cons": {
                    "Async/Await": ["Requires Python 3.5+"],
                    "Callbacks": ["Callback hell", "Hard to debug"],
                },
            },
            {
                "title": "Monolith vs Microservices",
                "context": "How to structure application",
                "options": ["Monolith", "Microservices", "Modular Monolith"],
                "pros": {
                    "Monolith": ["Simple to deploy", "Easy debugging", "Better performance initially"],
                    "Microservices": ["Independent scaling", "Team autonomy", "Technology diversity"],
                },
                "cons": {
                    "Monolith": ["Scaling limits", "Deployment coupling"],
                    "Microservices": ["Complexity", "Network latency"],
                },
            },
            {
                "title": "SQL vs NoSQL",
                "context": "How to store data",
                "options": ["SQL", "NoSQL", "Hybrid"],
                "pros": {
                    "SQL": ["ACID guarantees", "Complex queries", "Data integrity"],
                    "NoSQL": ["Scalability", "Flexibility", "Performance for simple queries"],
                },
                "cons": {
                    "SQL": ["Scaling challenges", "Schema rigidity"],
                    "NoSQL": ["No ACID", "Complex queries hard"],
                },
            },
            {
                "title": "Caching Strategy",
                "context": "How to improve performance",
                "options": ["No cache", "In-memory", "Redis", "CDN"],
                "pros": {
                    "In-memory": ["Fast", "Simple"],
                    "Redis": ["Shared", "Persistent"],
                    "CDN": ["Distributed", "Cheap"],
                },
                "cons": {
                    "In-memory": ["Limited scale", "Process-specific"],
                    "Redis": ["Additional service", "Network latency"],
                },
            },
        ]

        return common_patterns

    def learn_from_decisions(self, decisions: List[Decision]) -> Dict[str, Any]:
        """Learn patterns from a list of decisions.

        Args:
            decisions: List of past decisions

        Returns:
            Learnings and patterns
        """
        learnings = {
            "common_choices": {},
            "successful_patterns": [],
            "failed_patterns": [],
            "decision_frequency": {},
        }

        for decision in decisions:
            # Track which options are chosen
            choice = decision.chosen_option
            learnings["common_choices"][choice] = learnings["common_choices"].get(choice, 0) + 1

            # Track decision types
            decision_type = decision.title.split()[0]
            learnings["decision_frequency"][decision_type] = (
                learnings["decision_frequency"].get(decision_type, 0) + 1
            )

            # Identify successful patterns
            if self._is_successful(decision):
                learnings["successful_patterns"].append(decision.title)

        return learnings

    def _extract_context(self, body: str) -> str:
        """Extract context/problem from commit body."""
        if "Problem:" in body:
            return body.split("Problem:")[1].split("\n")[0].strip()
        return body[:200]

    def _extract_choice(self, title: str, body: str) -> str:
        """Extract what was chosen."""
        if "chose" in body.lower():
            return body.lower().split("chose")[1].split("\n")[0].strip()
        return title

    def _extract_rejected(self, body: str) -> List[str]:
        """Extract what was rejected."""
        if "rejected" in body.lower() or "considered" in body.lower():
            return ["See rationale"]
        return []

    def _extract_rationale(self, body: str) -> str:
        """Extract why this choice was made."""
        if "because" in body.lower():
            return body.lower().split("because")[1].split("\n")[0].strip()
        if "Rationale:" in body:
            return body.split("Rationale:")[1].split("\n")[0].strip()
        return body[:300]

    def _extract_outcomes(self, body: str) -> List[str]:
        """Extract outcomes from decision."""
        outcomes = []
        if "Result:" in body:
            outcomes.append(body.split("Result:")[1].split("\n")[0].strip())
        if "Benefits:" in body:
            outcomes.append(body.split("Benefits:")[1].split("\n")[0].strip())
        return outcomes

    def _is_successful(self, decision: Decision) -> bool:
        """Determine if decision was successful."""
        positive_words = ["works", "success", "good", "great", "improved", "better"]
        negative_words = ["failed", "bad", "broke", "regret", "mistake"]

        outcome_text = " ".join(decision.outcomes).lower()

        positive_count = sum(1 for word in positive_words if word in outcome_text)
        negative_count = sum(1 for word in negative_words if word in outcome_text)

        return positive_count > negative_count


class DecisionLibrary:
    """Library of architectural decisions for reference."""

    def __init__(self):
        """Initialize decision library."""
        self.decisions: Dict[str, Decision] = {}

    def add_decision(self, decision_id: str, decision: Decision) -> None:
        """Add a decision to the library."""
        self.decisions[decision_id] = decision

    def query(self, keywords: List[str]) -> List[Decision]:
        """Query decisions by keywords.

        Args:
            keywords: Keywords to search for

        Returns:
            Matching decisions
        """
        results = []
        for decision in self.decisions.values():
            decision_text = (decision.title + " " + decision.context).lower()
            if any(kw.lower() in decision_text for kw in keywords):
                results.append(decision)
        return results

    def get_similar_decisions(self, decision: Decision) -> List[Decision]:
        """Find similar past decisions.

        Args:
            decision: Decision to find similar ones for

        Returns:
            Similar decisions
        """
        keywords = decision.title.split()[:3]  # First 3 words
        return self.query(keywords)

    def suggest_based_on_context(self, context: str) -> List[Decision]:
        """Suggest relevant decisions based on context.

        Args:
            context: Contextual description

        Returns:
            Suggested decisions
        """
        return self.query(context.split())
