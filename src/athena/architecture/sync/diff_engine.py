"""
Document Diff Engine - Phase 4E Component 1.

Provides semantic diff computation for documentation changes, showing what will
change before regeneration and identifying the spec changes that caused drift.
"""

import difflib
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

from ..models import Document, Specification
from ..spec_store import SpecificationStore
from ..doc_store import DocumentStore


class ChangeType(str, Enum):
    """Type of change to a section."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class SectionType(str, Enum):
    """Type of document section."""

    HEADER = "header"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST = "list"
    TABLE = "table"
    BLOCKQUOTE = "blockquote"
    HORIZONTAL_RULE = "hr"


@dataclass
class Section:
    """A semantic section of a document."""

    section_type: SectionType
    content: str
    line_start: int
    line_end: int
    header_level: Optional[int] = None  # For headers (1-6)
    header_text: Optional[str] = None  # Header title
    language: Optional[str] = None  # For code blocks

    def __hash__(self):
        """Hash based on content for diffing."""
        return hash(self.content)

    @property
    def line_count(self) -> int:
        """Number of lines in this section."""
        return self.line_end - self.line_start + 1


@dataclass
class SectionChange:
    """A change to a document section."""

    section_name: str
    section_type: SectionType
    change_type: ChangeType
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    old_lines: Optional[Tuple[int, int]] = None  # (start, end)
    new_lines: Optional[Tuple[int, int]] = None

    @property
    def additions(self) -> int:
        """Number of lines added."""
        if self.change_type == ChangeType.ADDED and self.new_content:
            return len(self.new_content.splitlines())
        elif self.change_type == ChangeType.MODIFIED and self.new_content:
            old_lines = len(self.old_content.splitlines()) if self.old_content else 0
            new_lines = len(self.new_content.splitlines())
            return max(0, new_lines - old_lines)
        return 0

    @property
    def deletions(self) -> int:
        """Number of lines removed."""
        if self.change_type == ChangeType.REMOVED and self.old_content:
            return len(self.old_content.splitlines())
        elif self.change_type == ChangeType.MODIFIED and self.old_content:
            old_lines = len(self.old_content.splitlines())
            new_lines = len(self.new_content.splitlines()) if self.new_content else 0
            return max(0, old_lines - new_lines)
        return 0


@dataclass
class SpecChange:
    """A change to a specification that caused drift."""

    spec_id: int
    spec_name: str
    old_version: str
    new_version: str
    change_description: str
    diff_snippet: str


@dataclass
class DiffResult:
    """Complete diff analysis between two document versions."""

    document_id: int
    document_name: str
    old_hash: str
    new_hash: str
    old_content: str
    new_content: str

    # Section-level changes
    sections_added: List[SectionChange] = field(default_factory=list)
    sections_removed: List[SectionChange] = field(default_factory=list)
    sections_modified: List[SectionChange] = field(default_factory=list)
    sections_unchanged: List[SectionChange] = field(default_factory=list)

    # Root cause analysis
    spec_changes: List[SpecChange] = field(default_factory=list)

    # Metadata
    computed_at: datetime = field(default_factory=datetime.now)

    @property
    def total_additions(self) -> int:
        """Total lines added across all sections."""
        return sum(s.additions for s in self.sections_added + self.sections_modified)

    @property
    def total_deletions(self) -> int:
        """Total lines removed across all sections."""
        return sum(s.deletions for s in self.sections_removed + self.sections_modified)

    @property
    def total_modifications(self) -> int:
        """Number of sections modified."""
        return len(self.sections_modified)

    @property
    def has_changes(self) -> bool:
        """Whether there are any changes."""
        return bool(self.sections_added or self.sections_removed or self.sections_modified)

    def to_text(self, color: bool = True, show_unchanged: bool = False) -> str:
        """
        Rich terminal output with colors.

        Args:
            color: Whether to use ANSI color codes
            show_unchanged: Whether to show unchanged sections

        Returns:
            Formatted text suitable for terminal display
        """
        # ANSI color codes
        if color:
            RED = "\033[91m"
            GREEN = "\033[92m"
            YELLOW = "\033[93m"
            BLUE = "\033[94m"
            MAGENTA = "\033[95m"
            CYAN = "\033[96m"
            RESET = "\033[0m"
            BOLD = "\033[1m"
        else:
            RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = RESET = BOLD = ""

        lines = []

        # Header
        lines.append(f"{BOLD}Diff for Document: {self.document_name}{RESET}")
        lines.append("=" * 60)
        lines.append("")

        # Summary
        lines.append(f"{BOLD}Summary:{RESET}")
        lines.append(f"  Total additions:    {GREEN}+{self.total_additions}{RESET} lines")
        lines.append(f"  Total deletions:    {RED}-{self.total_deletions}{RESET} lines")
        lines.append(f"  Sections modified:  {YELLOW}{self.total_modifications}{RESET}")
        lines.append(f"  Sections added:     {GREEN}+{len(self.sections_added)}{RESET}")
        lines.append(f"  Sections removed:   {RED}-{len(self.sections_removed)}{RESET}")
        lines.append("")

        # Spec changes (root cause)
        if self.spec_changes:
            lines.append(f"{BOLD}Spec Changes (Root Cause):{RESET}")
            for spec_change in self.spec_changes:
                lines.append(f"  {MAGENTA}• {spec_change.spec_name}{RESET}")
                lines.append(f"    Version: {spec_change.old_version} → {spec_change.new_version}")
                lines.append(f"    {spec_change.change_description}")
                if spec_change.diff_snippet:
                    lines.append(f"    {CYAN}{spec_change.diff_snippet}{RESET}")
            lines.append("")

        # Section changes
        lines.append(f"{BOLD}Section Changes:{RESET}")
        lines.append("")

        # Added sections
        if self.sections_added:
            lines.append(f"{GREEN}{BOLD}Added Sections:{RESET}")
            for section in self.sections_added:
                lines.append(f"  {GREEN}+ {section.section_name}{RESET} ({section.additions} lines)")

        # Removed sections
        if self.sections_removed:
            lines.append(f"{RED}{BOLD}Removed Sections:{RESET}")
            for section in self.sections_removed:
                lines.append(f"  {RED}- {section.section_name}{RESET} ({section.deletions} lines)")

        # Modified sections
        if self.sections_modified:
            lines.append(f"{YELLOW}{BOLD}Modified Sections:{RESET}")
            for section in self.sections_modified:
                changes = f"+{section.additions}/-{section.deletions}"
                lines.append(f"  {YELLOW}~ {section.section_name}{RESET} ({changes})")

        # Unchanged sections
        if show_unchanged and self.sections_unchanged:
            lines.append(f"{BOLD}Unchanged Sections:{RESET}")
            for section in self.sections_unchanged:
                lines.append(f"  {section.section_name}")

        return "\n".join(lines)

    def to_json(self) -> dict:
        """Machine-readable JSON format."""
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "summary": {
                "total_additions": self.total_additions,
                "total_deletions": self.total_deletions,
                "sections_added": len(self.sections_added),
                "sections_removed": len(self.sections_removed),
                "sections_modified": len(self.sections_modified),
                "has_changes": self.has_changes,
            },
            "spec_changes": [
                {
                    "spec_id": sc.spec_id,
                    "spec_name": sc.spec_name,
                    "old_version": sc.old_version,
                    "new_version": sc.new_version,
                    "description": sc.change_description,
                }
                for sc in self.spec_changes
            ],
            "sections_added": [
                {
                    "name": s.section_name,
                    "type": s.section_type.value,
                    "additions": s.additions,
                }
                for s in self.sections_added
            ],
            "sections_removed": [
                {
                    "name": s.section_name,
                    "type": s.section_type.value,
                    "deletions": s.deletions,
                }
                for s in self.sections_removed
            ],
            "sections_modified": [
                {
                    "name": s.section_name,
                    "type": s.section_type.value,
                    "additions": s.additions,
                    "deletions": s.deletions,
                }
                for s in self.sections_modified
            ],
            "computed_at": self.computed_at.isoformat(),
        }

    def to_markdown(self) -> str:
        """Human-readable markdown report."""
        lines = []

        lines.append(f"# Diff Report: {self.document_name}")
        lines.append("")
        lines.append(f"**Generated**: {self.computed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Additions**: +{self.total_additions} lines")
        lines.append(f"- **Deletions**: -{self.total_deletions} lines")
        lines.append(f"- **Sections Modified**: {self.total_modifications}")
        lines.append(f"- **Sections Added**: {len(self.sections_added)}")
        lines.append(f"- **Sections Removed**: {len(self.sections_removed)}")
        lines.append("")

        # Spec changes
        if self.spec_changes:
            lines.append("## Spec Changes (Root Cause)")
            lines.append("")
            for sc in self.spec_changes:
                lines.append(f"### {sc.spec_name}")
                lines.append(f"- **Version**: {sc.old_version} → {sc.new_version}")
                lines.append(f"- **Changes**: {sc.change_description}")
                lines.append("")

        # Section changes
        lines.append("## Section Changes")
        lines.append("")

        if self.sections_added:
            lines.append("### Added")
            for s in self.sections_added:
                lines.append(f"- **{s.section_name}** (+{s.additions} lines)")

        if self.sections_removed:
            lines.append("### Removed")
            for s in self.sections_removed:
                lines.append(f"- **{s.section_name}** (-{s.deletions} lines)")

        if self.sections_modified:
            lines.append("### Modified")
            for s in self.sections_modified:
                lines.append(f"- **{s.section_name}** (+{s.additions}/-{s.deletions})")

        return "\n".join(lines)


class SectionParser:
    """Parse markdown content into semantic sections."""

    def parse(self, content: str) -> List[Section]:
        """
        Parse markdown into sections.

        Args:
            content: Markdown content

        Returns:
            List of semantic sections
        """
        sections = []
        lines = content.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]

            # Header
            if line.startswith("#"):
                section, lines_consumed = self._parse_header(lines, i)
                sections.append(section)
                i += lines_consumed

            # Code block
            elif line.startswith("```"):
                section, lines_consumed = self._parse_code_block(lines, i)
                sections.append(section)
                i += lines_consumed

            # Horizontal rule
            elif re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip()):
                section = Section(
                    section_type=SectionType.HORIZONTAL_RULE,
                    content=line,
                    line_start=i + 1,
                    line_end=i + 1,
                )
                sections.append(section)
                i += 1

            # List (bullet or numbered)
            elif re.match(r"^(\s*[-*+]|\s*\d+\.)\s", line):
                section, lines_consumed = self._parse_list(lines, i)
                sections.append(section)
                i += lines_consumed

            # Table
            elif "|" in line:
                section, lines_consumed = self._parse_table(lines, i)
                sections.append(section)
                i += lines_consumed

            # Blockquote
            elif line.startswith(">"):
                section, lines_consumed = self._parse_blockquote(lines, i)
                sections.append(section)
                i += lines_consumed

            # Paragraph (default)
            else:
                section, lines_consumed = self._parse_paragraph(lines, i)
                if section:  # Skip empty paragraphs
                    sections.append(section)
                i += lines_consumed

        return sections

    def _parse_header(self, lines: List[str], start: int) -> Tuple[Section, int]:
        """Parse a markdown header."""
        line = lines[start]
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2)
            return (
                Section(
                    section_type=SectionType.HEADER,
                    content=line,
                    line_start=start + 1,
                    line_end=start + 1,
                    header_level=level,
                    header_text=text,
                ),
                1,
            )
        return self._parse_paragraph(lines, start)

    def _parse_code_block(self, lines: List[str], start: int) -> Tuple[Section, int]:
        """Parse a code block (```language)."""
        first_line = lines[start]
        language = first_line[3:].strip() or None

        # Find closing ```
        end = start + 1
        while end < len(lines):
            if lines[end].startswith("```"):
                break
            end += 1

        content = "\n".join(lines[start : end + 1])
        return (
            Section(
                section_type=SectionType.CODE_BLOCK,
                content=content,
                line_start=start + 1,
                line_end=end + 1,
                language=language,
            ),
            end - start + 1,
        )

    def _parse_list(self, lines: List[str], start: int) -> Tuple[Section, int]:
        """Parse a list (bullet or numbered)."""
        end = start
        while end < len(lines):
            line = lines[end]
            # Continue if it's a list item or indented continuation
            if re.match(r"^(\s*[-*+]|\s*\d+\.)\s", line) or (
                line.startswith("  ") and line.strip()
            ):
                end += 1
            elif not line.strip():  # Blank line might be part of list
                end += 1
            else:
                break

        content = "\n".join(lines[start:end])
        return (
            Section(
                section_type=SectionType.LIST,
                content=content,
                line_start=start + 1,
                line_end=end,
            ),
            end - start,
        )

    def _parse_table(self, lines: List[str], start: int) -> Tuple[Section, int]:
        """Parse a markdown table."""
        end = start
        while end < len(lines) and "|" in lines[end]:
            end += 1

        content = "\n".join(lines[start:end])
        return (
            Section(
                section_type=SectionType.TABLE,
                content=content,
                line_start=start + 1,
                line_end=end,
            ),
            end - start,
        )

    def _parse_blockquote(self, lines: List[str], start: int) -> Tuple[Section, int]:
        """Parse a blockquote (> text)."""
        end = start
        while end < len(lines) and lines[end].startswith(">"):
            end += 1

        content = "\n".join(lines[start:end])
        return (
            Section(
                section_type=SectionType.BLOCKQUOTE,
                content=content,
                line_start=start + 1,
                line_end=end,
            ),
            end - start,
        )

    def _parse_paragraph(self, lines: List[str], start: int) -> Tuple[Optional[Section], int]:
        """Parse a paragraph (consecutive non-special lines)."""
        if not lines[start].strip():
            return None, 1

        end = start
        while end < len(lines):
            line = lines[end]
            # Stop on special markdown
            if (
                not line.strip()
                or line.startswith("#")
                or line.startswith("```")
                or re.match(r"^(\s*[-*+]|\s*\d+\.)\s", line)
                or line.startswith(">")
                or "|" in line
                or re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip())
            ):
                break
            end += 1

        content = "\n".join(lines[start:end]).strip()
        if not content:
            return None, end - start

        return (
            Section(
                section_type=SectionType.PARAGRAPH,
                content=content,
                line_start=start + 1,
                line_end=end,
            ),
            end - start,
        )


class DocumentDiffer:
    """Compute diffs between document versions."""

    def __init__(self, spec_store: SpecificationStore, doc_store: DocumentStore):
        self.spec_store = spec_store
        self.doc_store = doc_store
        self.parser = SectionParser()

    def compute_diff(
        self,
        doc_id: int,
        new_content: str,
        show_cause: bool = True,
    ) -> DiffResult:
        """
        Compute comprehensive diff between current and new document content.

        Args:
            doc_id: Document ID to compare
            new_content: Proposed new content
            show_cause: Include spec changes that caused drift

        Returns:
            DiffResult with all changes
        """
        # Get current document
        doc = self.doc_store.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        old_content = doc.content or ""

        # Compute hashes
        old_hash = hashlib.sha256(old_content.encode()).hexdigest()[:16]
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()[:16]

        # Parse into sections
        old_sections = self.parser.parse(old_content)
        new_sections = self.parser.parse(new_content)

        # Compute section-level diff
        added, removed, modified, unchanged = self._diff_sections(
            old_sections, new_sections
        )

        # Optionally analyze spec changes
        spec_changes = []
        if show_cause:
            spec_changes = self._analyze_spec_changes(doc)

        return DiffResult(
            document_id=doc.id,
            document_name=doc.name,
            old_hash=old_hash,
            new_hash=new_hash,
            old_content=old_content,
            new_content=new_content,
            sections_added=added,
            sections_removed=removed,
            sections_modified=modified,
            sections_unchanged=unchanged,
            spec_changes=spec_changes,
        )

    def _diff_sections(
        self, old: List[Section], new: List[Section]
    ) -> Tuple[List[SectionChange], List[SectionChange], List[SectionChange], List[SectionChange]]:
        """
        Compute semantic diff at section level.

        Returns:
            (added, removed, modified, unchanged)
        """
        added = []
        removed = []
        modified = []
        unchanged = []

        # Use sequence matcher for intelligent matching
        matcher = difflib.SequenceMatcher(None, old, new)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                # Unchanged sections
                for idx in range(i1, i2):
                    section = old[idx]
                    unchanged.append(
                        SectionChange(
                            section_name=self._get_section_name(section),
                            section_type=section.section_type,
                            change_type=ChangeType.UNCHANGED,
                            old_content=section.content,
                            new_content=section.content,
                            old_lines=(section.line_start, section.line_end),
                            new_lines=(section.line_start, section.line_end),
                        )
                    )

            elif tag == "delete":
                # Removed sections
                for idx in range(i1, i2):
                    section = old[idx]
                    removed.append(
                        SectionChange(
                            section_name=self._get_section_name(section),
                            section_type=section.section_type,
                            change_type=ChangeType.REMOVED,
                            old_content=section.content,
                            old_lines=(section.line_start, section.line_end),
                        )
                    )

            elif tag == "insert":
                # Added sections
                for idx in range(j1, j2):
                    section = new[idx]
                    added.append(
                        SectionChange(
                            section_name=self._get_section_name(section),
                            section_type=section.section_type,
                            change_type=ChangeType.ADDED,
                            new_content=section.content,
                            new_lines=(section.line_start, section.line_end),
                        )
                    )

            elif tag == "replace":
                # Modified sections (consider them as remove + add for now)
                # Could be smarter here with line-level diff
                for idx in range(i1, i2):
                    section = old[idx]
                    new_section = new[j1] if j1 < j2 else None

                    if new_section:
                        modified.append(
                            SectionChange(
                                section_name=self._get_section_name(section),
                                section_type=section.section_type,
                                change_type=ChangeType.MODIFIED,
                                old_content=section.content,
                                new_content=new_section.content,
                                old_lines=(section.line_start, section.line_end),
                                new_lines=(new_section.line_start, new_section.line_end),
                            )
                        )
                        j1 += 1
                    else:
                        removed.append(
                            SectionChange(
                                section_name=self._get_section_name(section),
                                section_type=section.section_type,
                                change_type=ChangeType.REMOVED,
                                old_content=section.content,
                                old_lines=(section.line_start, section.line_end),
                            )
                        )

                # Handle any remaining new sections
                for idx in range(j1, j2):
                    section = new[idx]
                    added.append(
                        SectionChange(
                            section_name=self._get_section_name(section),
                            section_type=section.section_type,
                            change_type=ChangeType.ADDED,
                            new_content=section.content,
                            new_lines=(section.line_start, section.line_end),
                        )
                    )

        return added, removed, modified, unchanged

    def _get_section_name(self, section: Section) -> str:
        """Get a human-readable name for a section."""
        if section.section_type == SectionType.HEADER and section.header_text:
            return section.header_text
        elif section.section_type == SectionType.CODE_BLOCK:
            lang = section.language or "code"
            return f"Code Block ({lang})"
        else:
            # Use first few words of content
            words = section.content.split()[:5]
            preview = " ".join(words)
            if len(section.content.split()) > 5:
                preview += "..."
            return f"{section.section_type.value.title()}: {preview}"

    def _analyze_spec_changes(self, doc: Document) -> List[SpecChange]:
        """
        Identify which spec changes caused this drift.

        For now, returns a simple description. Future: could diff spec versions.
        """
        spec_changes = []

        if not doc.based_on_spec_ids:
            return spec_changes

        for spec_id in doc.based_on_spec_ids:
            spec = self.spec_store.get(spec_id)
            if spec:
                # TODO: Compare with previous spec version when we have version history
                spec_changes.append(
                    SpecChange(
                        spec_id=spec.id,
                        spec_name=spec.name,
                        old_version=spec.version,
                        new_version=spec.version,
                        change_description="Spec content modified (version history not yet available)",
                        diff_snippet="",
                    )
                )

        return spec_changes
