"""Prompt library for AI document generation.

Provides specialized prompts for generating different types of documentation
from specifications and architectural artifacts.
"""

from typing import Dict, Any
from ..models import DocumentType


class PromptLibrary:
    """Library of prompts for AI document generation.

    Each prompt is optimized for a specific document type and includes
    instructions for structure, tone, and content requirements.
    """

    @staticmethod
    def get_prompt(doc_type: DocumentType, context: Dict[str, Any]) -> str:
        """Get generation prompt for a document type.

        Args:
            doc_type: Type of document to generate
            context: Context dictionary with specs, ADRs, etc.

        Returns:
            Formatted prompt string

        Example:
            >>> context = {"primary_specs": [...], "target_audience": "technical"}
            >>> prompt = PromptLibrary.get_prompt(DocumentType.API_DOC, context)
        """
        prompt_map = {
            # API Documentation
            DocumentType.API_DOC: PromptLibrary._api_doc_prompt,
            DocumentType.API_GUIDE: PromptLibrary._api_guide_prompt,
            DocumentType.SDK_DOC: PromptLibrary._sdk_doc_prompt,

            # Product Documents
            DocumentType.PRD_LEAN: PromptLibrary._prd_lean_prompt,
            DocumentType.PRD_AGILE: PromptLibrary._prd_agile_prompt,
            DocumentType.PRD_PROBLEM: PromptLibrary._prd_problem_prompt,
            DocumentType.MRD: PromptLibrary._mrd_prompt,

            # Technical Documents
            DocumentType.TDD: PromptLibrary._tdd_prompt,
            DocumentType.HLD: PromptLibrary._hld_prompt,
            DocumentType.LLD: PromptLibrary._lld_prompt,

            # Architecture Documents
            DocumentType.ARC42: PromptLibrary._arc42_prompt,
            DocumentType.C4_CONTEXT: PromptLibrary._c4_context_prompt,
            DocumentType.C4_CONTAINER: PromptLibrary._c4_container_prompt,
            DocumentType.C4_COMPONENT: PromptLibrary._c4_component_prompt,

            # Operational Documents
            DocumentType.RUNBOOK: PromptLibrary._runbook_prompt,
            DocumentType.DEPLOYMENT_GUIDE: PromptLibrary._deployment_prompt,
            DocumentType.TROUBLESHOOTING: PromptLibrary._troubleshooting_prompt,

            # Change Documents
            DocumentType.CHANGELOG: PromptLibrary._changelog_prompt,
            DocumentType.MIGRATION_GUIDE: PromptLibrary._migration_prompt,
            DocumentType.UPGRADE_GUIDE: PromptLibrary._upgrade_prompt,
        }

        prompt_fn = prompt_map.get(doc_type, PromptLibrary._default_prompt)
        return prompt_fn(context)

    # ========================================================================
    # API Documentation Prompts
    # ========================================================================

    @staticmethod
    def _api_doc_prompt(context: Dict[str, Any]) -> str:
        """Generate prompt for API documentation."""
        specs = context.get("primary_specs", [])
        spec_content = "\n\n".join([
            f"### {spec['name']} (v{spec['version']})\n{spec['content']}"
            for spec in specs
        ])

        return f"""Generate comprehensive API documentation based on the following OpenAPI specification(s).

**Target Audience**: {context.get('target_audience', 'developers')}
**Detail Level**: {context.get('detail_level', 'comprehensive')}

# Specifications

{spec_content}

# Requirements

Generate API documentation that includes:

1. **Overview**: Brief description of the API's purpose and capabilities
2. **Authentication**: How to authenticate API requests
3. **Endpoints**: For each endpoint, document:
   - HTTP method and path
   - Description and use case
   - Request parameters (path, query, headers, body)
   - Request examples (curl, Python, JavaScript)
   - Response format and status codes
   - Response examples (success and error cases)
4. **Error Handling**: Common error codes and their meanings
5. **Rate Limiting**: Any rate limits or throttling policies
6. **Versioning**: API versioning strategy
7. **SDKs and Libraries**: Available client libraries
8. **Code Examples**: Real-world usage examples

# Format

- Use Markdown format
- Include code blocks with syntax highlighting
- Add tables for parameters and responses
- Include mermaid diagrams where helpful
- Use clear section headers

Generate the complete API documentation now:
"""

    @staticmethod
    def _api_guide_prompt(context: Dict[str, Any]) -> str:
        """Generate prompt for API integration guide."""
        specs = context.get("primary_specs", [])
        spec_names = ", ".join([spec['name'] for spec in specs])

        return f"""Generate a practical API integration guide for: {spec_names}

**Target Audience**: {context.get('target_audience', 'developers')}
**Focus**: Step-by-step integration instructions

# Context

{PromptLibrary._format_specs(specs)}

# Guide Structure

1. **Getting Started**
   - Prerequisites
   - Obtaining API credentials
   - Installing dependencies

2. **Quick Start**
   - Minimal working example
   - First API call
   - Handling responses

3. **Authentication Setup**
   - Authentication flow
   - Token management
   - Security best practices

4. **Common Use Cases**
   - Real-world scenarios
   - Code examples for each scenario
   - Error handling patterns

5. **Testing**
   - Testing strategies
   - Mock data and sandbox environments
   - Debugging tips

6. **Production Checklist**
   - Performance optimization
   - Monitoring and logging
   - Rate limiting considerations

7. **Troubleshooting**
   - Common issues and solutions
   - Error codes reference
   - Support resources

Generate a practical, hands-on integration guide in Markdown format:
"""

    # ========================================================================
    # Technical Design Document Prompts
    # ========================================================================

    @staticmethod
    def _tdd_prompt(context: Dict[str, Any]) -> str:
        """Generate prompt for Technical Design Document."""
        specs = context.get("primary_specs", [])
        adrs = context.get("adrs", [])
        constraints = context.get("constraints", [])

        return f"""Generate a comprehensive Technical Design Document (TDD) based on the following specifications and architectural context.

**Target Audience**: Engineering team
**Purpose**: Detailed technical design for implementation

# Input Specifications

{PromptLibrary._format_specs(specs)}

# Architecture Decisions

{PromptLibrary._format_adrs(adrs)}

# Constraints

{PromptLibrary._format_constraints(constraints)}

# TDD Structure

Generate a complete TDD with the following sections:

1. **Executive Summary**
   - Problem statement
   - Proposed solution overview
   - Success criteria

2. **Goals and Non-Goals**
   - What this design aims to achieve
   - Explicitly what's out of scope

3. **Proposed Solution**
   - High-level architecture
   - Component breakdown
   - Data models
   - API design
   - Sequence diagrams

4. **Implementation Plan**
   - Phased approach
   - Dependencies
   - Timeline estimates

5. **Technical Considerations**
   - Performance implications
   - Security considerations
   - Scalability strategy
   - Error handling

6. **Testing Strategy**
   - Unit testing approach
   - Integration testing
   - Performance testing

7. **Risks and Mitigations**
   - Technical risks
   - Mitigation strategies

8. **Alternative Approaches**
   - Approaches considered
   - Why they were rejected

9. **Open Questions**
   - Unresolved design decisions
   - Areas needing further research

# Format Requirements

- Use Markdown with clear headers
- Include mermaid diagrams for architecture and sequences
- Add tables for comparisons and data structures
- Use code blocks for examples
- Be specific and detailed

Generate the complete Technical Design Document:
"""

    @staticmethod
    def _hld_prompt(context: Dict[str, Any]) -> str:
        """Generate prompt for High-Level Design."""
        specs = context.get("primary_specs", [])

        return f"""Generate a High-Level Design (HLD) document that provides a system-level view of the architecture.

**Focus**: System architecture and component interactions
**Abstraction Level**: High-level, suitable for architects and senior engineers

# Input

{PromptLibrary._format_specs(specs)}

# HLD Sections

1. **System Overview**
   - Purpose and scope
   - Key capabilities
   - System boundaries

2. **Architecture Diagram**
   - System context (C4 context diagram)
   - Major components and their responsibilities
   - External dependencies

3. **Component Design**
   - For each major component:
     - Responsibility
     - Key interfaces
     - Technology choices
     - Scaling considerations

4. **Data Flow**
   - How data moves through the system
   - Data transformations
   - Storage strategy

5. **Integration Points**
   - External APIs
   - Third-party services
   - Inter-service communication

6. **Non-Functional Requirements**
   - Performance targets
   - Reliability (SLAs)
   - Security requirements
   - Compliance needs

7. **Deployment Architecture**
   - Infrastructure overview
   - Environments (dev, staging, prod)
   - Deployment strategy

8. **Monitoring and Observability**
   - Logging strategy
   - Metrics and alerting
   - Tracing

Generate the High-Level Design document in Markdown:
"""

    # ========================================================================
    # Product Documents
    # ========================================================================

    @staticmethod
    def _prd_lean_prompt(context: Dict[str, Any]) -> str:
        """Generate prompt for Lean PRD."""
        specs = context.get("primary_specs", [])

        return f"""Generate a Lean Product Requirements Document (PRD) - concise and focused on essential information.

**Format**: Lean PRD (1-2 pages, highly focused)
**Audience**: Product team and stakeholders

# Technical Specifications

{PromptLibrary._format_specs(specs)}

# Lean PRD Structure

1. **Problem Statement** (2-3 sentences)
   - What problem are we solving?
   - Who experiences this problem?

2. **Goals** (bullet points)
   - Primary goals (2-3)
   - Success metrics (1-2 key metrics)

3. **Solution** (1 paragraph + bullet points)
   - High-level approach
   - Key features (3-5 bullet points)

4. **User Stories** (3-5 stories)
   - As a [user], I want [feature] so that [benefit]

5. **Out of Scope** (bullet points)
   - What we're explicitly NOT doing

6. **Success Criteria** (2-3 measurable outcomes)
   - How we'll know we've succeeded

7. **Timeline** (high-level)
   - Key milestones

Keep it concise and actionable. Generate the Lean PRD:
"""

    # ========================================================================
    # Operational Documents
    # ========================================================================

    @staticmethod
    def _runbook_prompt(context: Dict[str, Any]) -> str:
        """Generate prompt for operational runbook."""
        specs = context.get("primary_specs", [])

        return f"""Generate an operational runbook for the system described in these specifications.

**Purpose**: Enable on-call engineers to operate and troubleshoot the system
**Audience**: Operations and SRE teams

# System Specifications

{PromptLibrary._format_specs(specs)}

# Runbook Sections

1. **System Overview**
   - What this system does
   - Architecture diagram
   - Dependencies

2. **Service Inventory**
   - Services and their responsibilities
   - Endpoints and health checks
   - Configuration

3. **Common Operations**
   - Starting/stopping services
   - Deploying updates
   - Rolling back deployments
   - Scaling operations

4. **Monitoring and Alerts**
   - Key metrics to watch
   - Alert conditions
   - Dashboard links

5. **Troubleshooting Guides**
   - For each common issue:
     - Symptoms
     - Diagnosis steps
     - Resolution procedure
     - Prevention

6. **Incident Response**
   - Severity levels
   - Escalation procedures
   - Communication channels

7. **Maintenance Tasks**
   - Regular maintenance activities
   - Backup procedures
   - Log rotation

8. **Emergency Contacts**
   - Team members and roles
   - Escalation paths

Generate a practical, actionable runbook in Markdown:
"""

    # ========================================================================
    # Helper Methods
    # ========================================================================

    @staticmethod
    def _format_specs(specs: list) -> str:
        """Format specifications for prompt inclusion."""
        if not specs:
            return "No specifications provided."

        formatted = []
        for spec in specs:
            formatted.append(f"""
## {spec['name']} (v{spec['version']})

**Type**: {spec['type']}
**Status**: {spec['status']}
{f"**Description**: {spec['description']}" if spec.get('description') else ""}

```
{spec['content'][:2000]}{"..." if len(spec['content']) > 2000 else ""}
```
""")

        return "\n".join(formatted)

    @staticmethod
    def _format_adrs(adrs: list) -> str:
        """Format ADRs for prompt inclusion."""
        if not adrs:
            return "No architecture decisions provided."

        formatted = []
        for adr in adrs:
            formatted.append(f"""
### ADR {adr['id']}: {adr.get('title', 'Untitled')}

**Status**: {adr.get('status', 'unknown')}
**Decision**: {adr.get('decision', 'No decision recorded')}
""")

        return "\n".join(formatted)

    @staticmethod
    def _format_constraints(constraints: list) -> str:
        """Format constraints for prompt inclusion."""
        if not constraints:
            return "No constraints specified."

        formatted = []
        for constraint in constraints:
            formatted.append(f"""
- **{constraint.get('name', 'Unnamed')}** ({constraint.get('type', 'unknown')}):
  {constraint.get('description', 'No description')}
""")

        return "\n".join(formatted)

    @staticmethod
    def _default_prompt(context: Dict[str, Any]) -> str:
        """Default prompt for unknown document types."""
        specs = context.get("primary_specs", [])

        return f"""Generate documentation based on the following specifications.

# Specifications

{PromptLibrary._format_specs(specs)}

# Instructions

Generate comprehensive, well-structured documentation in Markdown format.
Include relevant sections based on the specification content.
"""

    # Placeholders for remaining prompt methods
    # (These follow the same pattern as above)

    @staticmethod
    def _sdk_doc_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _prd_agile_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _prd_problem_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _mrd_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _lld_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _arc42_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _c4_context_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _c4_container_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _c4_component_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _deployment_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _troubleshooting_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _changelog_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _migration_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)

    @staticmethod
    def _upgrade_prompt(context: Dict[str, Any]) -> str:
        return PromptLibrary._default_prompt(context)
