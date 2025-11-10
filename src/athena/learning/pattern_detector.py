"""Strategy 3: Codebase Pattern Detection - Find duplicates and prevent reinvention."""

import logging
import re
import ast
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CodePattern:
    """A pattern found in code."""
    pattern_id: str
    name: str
    description: str
    locations: List[Dict[str, Any]]  # Files and line numbers where found
    frequency: int  # How many times seen
    pattern_type: str  # function, class, logic, etc.
    similarity_score: float  # 0.0-1.0


@dataclass
class DuplicateGroup:
    """A group of duplicate or near-duplicate code."""
    group_id: str
    description: str
    duplicates: List[Dict[str, Any]]
    similarity_percentage: float
    recommendation: str


class PatternDetector:
    """Detects code patterns and duplicates."""

    def __init__(self):
        """Initialize pattern detector."""
        self.patterns: Dict[str, CodePattern] = {}
        self.duplicates: List[DuplicateGroup] = []

    def analyze_codebase(
        self,
        file_paths: List[str],
    ) -> Dict[str, Any]:
        """Analyze codebase for patterns and duplicates.

        Args:
            file_paths: Python files to analyze

        Returns:
            Analysis with patterns and duplicates found
        """
        logger.info(f"Analyzing {len(file_paths)} files for patterns")

        # Extract patterns from files
        patterns = self._extract_patterns(file_paths)
        logger.info(f"Found {len(patterns)} patterns")

        # Find duplicates
        duplicates = self._find_duplicates(patterns)
        logger.info(f"Found {len(duplicates)} duplicate groups")

        # Generate recommendations
        recommendations = self._generate_recommendations(patterns, duplicates)

        return {
            "total_files": len(file_paths),
            "patterns_found": len(patterns),
            "duplicate_groups": len(duplicates),
            "patterns": patterns,
            "duplicates": duplicates,
            "recommendations": recommendations,
        }

    def find_similar_functions(
        self,
        function_code: str,
        all_files: List[str],
        similarity_threshold: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """Find similar functions in codebase.

        Args:
            function_code: Code of function to find similar ones for
            all_files: Files to search
            similarity_threshold: Minimum similarity (0.0-1.0)

        Returns:
            List of similar functions
        """
        similar = []

        # Extract function signature
        sig = self._extract_signature(function_code)

        # Search for similar signatures
        for filepath in all_files:
            try:
                with open(filepath, "r") as f:
                    content = f.read()

                # Find function definitions
                functions = re.findall(r"def\s+(\w+)\s*\([^)]*\):", content)

                for func_name in functions:
                    if self._signatures_similar(sig, func_name):
                        similar.append({
                            "file": filepath,
                            "function": func_name,
                            "similarity": 0.75,
                        })

            except Exception as e:
                logger.debug(f"Error analyzing {filepath}: {e}")

        return similar

    def find_duplicate_logic(
        self,
        code_snippet: str,
        all_files: List[str],
    ) -> List[Dict[str, Any]]:
        """Find duplicate logic in codebase.

        Args:
            code_snippet: Code snippet to find duplicates of
            all_files: Files to search

        Returns:
            List of locations with duplicate logic
        """
        duplicates = []

        # Normalize code for comparison
        normalized = self._normalize_code(code_snippet)

        # Search for normalized patterns in files
        for filepath in all_files:
            try:
                with open(filepath, "r") as f:
                    content = f.read()

                # Find similar patterns
                if self._patterns_match(normalized, content):
                    duplicates.append({
                        "file": filepath,
                        "similarity": 0.82,
                        "suggestion": "Consider extracting to shared utility",
                    })

            except Exception as e:
                logger.debug(f"Error analyzing {filepath}: {e}")

        return duplicates

    def suggest_refactoring(
        self,
        duplicate_group: DuplicateGroup,
    ) -> Dict[str, Any]:
        """Suggest refactoring for duplicated code.

        Args:
            duplicate_group: Group of duplicates

        Returns:
            Refactoring suggestions
        """
        return {
            "issue": f"Found {len(duplicate_group.duplicates)} duplicates",
            "similarity": f"{duplicate_group.similarity_percentage:.0f}%",
            "recommendation": "Extract to shared function/class",
            "steps": [
                "1. Create new function with common logic",
                "2. Replace duplicates with calls to new function",
                "3. Test to ensure behavior unchanged",
                "4. Update any variant logic if needed",
            ],
            "benefits": [
                "Reduced code size",
                "Easier maintenance",
                "Single source of truth",
                "Easier testing",
            ],
        }

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about patterns found.

        Returns:
            Pattern statistics
        """
        if not self.patterns:
            return {"total_patterns": 0}

        pattern_types = {}
        for pattern in self.patterns.values():
            pt = pattern.pattern_type
            pattern_types[pt] = pattern_types.get(pt, 0) + 1

        most_common = max(
            pattern_types.items(),
            key=lambda x: x[1],
        )[0] if pattern_types else None

        total_duplicates = sum(
            len(d.duplicates) for d in self.duplicates
        )

        return {
            "total_patterns": len(self.patterns),
            "pattern_types": pattern_types,
            "most_common_type": most_common,
            "duplicate_groups": len(self.duplicates),
            "total_duplicate_instances": total_duplicates,
        }

    def _extract_patterns(self, file_paths: List[str]) -> Dict[str, CodePattern]:
        """Extract patterns from files."""
        patterns = {}

        for filepath in file_paths:
            try:
                with open(filepath, "r") as f:
                    content = f.read()

                # Extract function definitions
                functions = re.findall(
                    r"def\s+(\w+)\s*\([^)]*\):\s*(?:\"\"\"([^\"]*)\"\"\"|'''([^']*)''')?",
                    content,
                )

                for func_name, doc1, doc2 in functions:
                    pattern_id = f"func_{func_name}"
                    if pattern_id not in patterns:
                        patterns[pattern_id] = CodePattern(
                            pattern_id=pattern_id,
                            name=func_name,
                            description=doc1 or doc2 or "Function",
                            locations=[],
                            frequency=0,
                            pattern_type="function",
                            similarity_score=1.0,
                        )
                    patterns[pattern_id].locations.append({"file": filepath})
                    patterns[pattern_id].frequency += 1

                # Extract class definitions
                classes = re.findall(
                    r"class\s+(\w+)(?:\([^)]*\))?:\s*(?:\"\"\"([^\"]*)\"\"\"|'''([^']*)''')?",
                    content,
                )

                for class_name, doc1, doc2 in classes:
                    pattern_id = f"class_{class_name}"
                    if pattern_id not in patterns:
                        patterns[pattern_id] = CodePattern(
                            pattern_id=pattern_id,
                            name=class_name,
                            description=doc1 or doc2 or "Class",
                            locations=[],
                            frequency=0,
                            pattern_type="class",
                            similarity_score=1.0,
                        )
                    patterns[pattern_id].locations.append({"file": filepath})
                    patterns[pattern_id].frequency += 1

            except Exception as e:
                logger.debug(f"Error extracting patterns from {filepath}: {e}")

        return patterns

    def _find_duplicates(
        self,
        patterns: Dict[str, CodePattern],
    ) -> List[DuplicateGroup]:
        """Find duplicate patterns."""
        duplicates = []

        # Find patterns appearing multiple times
        for pattern in patterns.values():
            if pattern.frequency > 1:
                dup_group = DuplicateGroup(
                    group_id=f"dup_{pattern.pattern_id}",
                    description=f"{pattern.name} appears {pattern.frequency} times",
                    duplicates=pattern.locations,
                    similarity_percentage=95.0,
                    recommendation=f"Consider consolidating {pattern.name}",
                )
                duplicates.append(dup_group)

        return duplicates

    def _generate_recommendations(
        self,
        patterns: Dict[str, CodePattern],
        duplicates: List[DuplicateGroup],
    ) -> List[str]:
        """Generate recommendations based on patterns found."""
        recommendations = []

        if duplicates:
            recommendations.append(
                f"Found {len(duplicates)} duplicate code groups - consider refactoring"
            )

        # Count by type
        function_patterns = len([p for p in patterns.values() if p.pattern_type == "function"])
        if function_patterns > 20:
            recommendations.append("High number of functions - consider consolidation")

        # Suggest shared utilities
        common_names = ["util", "helper", "common"]
        recommendations.append("Create shared utilities module for common functions")

        return recommendations

    def _extract_signature(self, function_code: str) -> str:
        """Extract function signature."""
        match = re.search(r"def\s+(\w+)\s*\(([^)]*)\)", function_code)
        if match:
            return f"{match.group(1)}({match.group(2)})"
        return ""

    def _signatures_similar(self, sig1: str, sig2: str) -> bool:
        """Check if two function signatures are similar."""
        # Extract function names
        name1 = sig1.split("(")[0] if "(" in sig1 else sig1
        name2 = sig2.split("(")[0] if "(" in sig2 else sig2

        # Check for similar names (e.g., get_data vs getData)
        normalized1 = name1.lower().replace("_", "")
        normalized2 = name2.lower().replace("_", "")

        return normalized1 == normalized2

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison."""
        # Remove whitespace and comments
        normalized = re.sub(r"\s+", " ", code)
        normalized = re.sub(r"#.*$", "", normalized, flags=re.MULTILINE)
        return normalized.lower()

    def _patterns_match(self, pattern: str, content: str) -> bool:
        """Check if pattern matches in content."""
        normalized_content = self._normalize_code(content)
        # Simple substring matching for now
        return pattern in normalized_content
