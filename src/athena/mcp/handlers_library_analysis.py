"""MCP handlers for library dependency analysis operations."""

import logging

logger = logging.getLogger(__name__)


def register_library_analysis_tools(server):
    """Register library analysis tools with MCP server.

    Args:
        server: MCP server instance
    """

    @server.tool()
    async def analyze_library(
        library_name: str,
        current_version: str = None,
        check_vulnerabilities: bool = True,
        check_updates: bool = True,
    ) -> dict:
        """Analyze a library for capabilities, dependencies, and security issues.

        Grounds decisions in actual library capabilities per "teach AI to think like a senior engineer".
        Checks for version compatibility, breaking changes, and security vulnerabilities.

        Args:
            library_name: Name of library (e.g., "requests", "fastapi", "pytest")
            current_version: Current version in use (optional)
            check_vulnerabilities: Check for security vulnerabilities (default True)
            check_updates: Check for newer versions available (default True)

        Returns:
            {
                "library": str,
                "version": str,
                "latest_version": str or null,
                "is_outdated": bool,
                "capabilities": {
                    "main_features": [str],
                    "undocumented_features": [str],
                    "known_limitations": [str],
                    "performance_characteristics": dict,
                },
                "dependencies": [
                    {
                        "name": str,
                        "current_version": str,
                        "latest_version": str,
                        "is_outdated": bool,
                    }
                ],
                "vulnerabilities": [
                    {
                        "id": str,
                        "severity": str,
                        "description": str,
                        "affected_versions": [str],
                    }
                ],
                "compatibility": {
                    "python": str,
                    "platforms": str,
                },
                "alternatives": [
                    {
                        "name": str,
                        "advantage": str,
                    }
                ],
            }
        """
        try:
            from ..analysis.library_analyzer import get_analyzer

            analyzer = get_analyzer()
            analysis = await analyzer.analyze_library(
                library_name,
                current_version=current_version,
                check_vulnerabilities=check_vulnerabilities,
                check_updates=check_updates,
            )

            if not analysis:
                return {
                    "error": f"Could not analyze library: {library_name}",
                    "library": library_name,
                }

            return {
                "library": analysis.name,
                "version": analysis.version,
                "latest_version": analysis.latest_version,
                "is_outdated": analysis.is_outdated,
                "capabilities": {
                    "description": analysis.capabilities.description,
                    "main_features": analysis.capabilities.main_features,
                    "undocumented_features": analysis.capabilities.undocumented_features,
                    "known_limitations": analysis.capabilities.known_limitations,
                    "performance": analysis.capabilities.performance_characteristics,
                },
                "dependencies": [
                    {
                        "name": dep.name,
                        "current_version": dep.current_version,
                        "latest_version": dep.latest_version,
                        "is_outdated": dep.is_outdated,
                        "breaking_changes": dep.breaking_changes,
                    }
                    for dep in analysis.dependencies
                ],
                "vulnerabilities": analysis.vulnerabilities,
                "compatibility": analysis.compatibility_matrix,
                "alternatives": analysis.alternatives,
                "analysis_timestamp": analysis.analysis_timestamp,
            }

        except Exception as e:
            logger.error(f"Library analysis failed: {e}")
            return {
                "error": f"Analysis failed: {str(e)}",
                "library": library_name,
            }

    @server.tool()
    async def analyze_requirements(
        requirements_file: str,
        check_vulnerabilities: bool = True,
    ) -> dict:
        """Analyze all dependencies in a requirements file.

        Provides comprehensive overview of project dependencies, versions, and security issues.

        Args:
            requirements_file: Path to requirements.txt or similar
            check_vulnerabilities: Check for security vulnerabilities (default True)

        Returns:
            {
                "requirements_file": str,
                "total_dependencies": int,
                "outdated_count": int,
                "vulnerable_count": int,
                "analyses": [
                    {
                        "library": str,
                        "version": str,
                        "latest_version": str,
                        "is_outdated": bool,
                        "vulnerabilities": [dict],
                    }
                ],
                "summary": {
                    "all_up_to_date": bool,
                    "security_issues": int,
                    "recommendations": [str],
                },
            }
        """
        try:
            from ..analysis.library_analyzer import get_analyzer

            analyzer = get_analyzer()
            analyses = await analyzer.analyze_requirements(
                requirements_file,
            )

            if not analyses:
                return {
                    "error": f"Could not analyze requirements: {requirements_file}",
                    "requirements_file": requirements_file,
                }

            # Calculate summary
            outdated = sum(1 for a in analyses if a.is_outdated)
            vulnerable = sum(len(a.vulnerabilities) for a in analyses)
            recommendations = []

            if outdated > 0:
                recommendations.append(
                    f"Update {outdated} outdated dependencies to latest versions"
                )

            if vulnerable > 0:
                recommendations.append(
                    f"Address {vulnerable} security vulnerabilities in dependencies"
                )

            return {
                "requirements_file": requirements_file,
                "total_dependencies": len(analyses),
                "outdated_count": outdated,
                "vulnerable_count": vulnerable,
                "analyses": [
                    {
                        "library": a.name,
                        "version": a.version,
                        "latest_version": a.latest_version,
                        "is_outdated": a.is_outdated,
                        "vulnerabilities": a.vulnerabilities,
                    }
                    for a in analyses
                ],
                "summary": {
                    "all_up_to_date": outdated == 0,
                    "security_issues": vulnerable,
                    "recommendations": recommendations,
                },
            }

        except Exception as e:
            logger.error(f"Requirements analysis failed: {e}")
            return {
                "error": f"Analysis failed: {str(e)}",
                "requirements_file": requirements_file,
            }

    @server.tool()
    async def check_library_compatibility(
        library1: str,
        library2: str,
        version1: str = None,
        version2: str = None,
    ) -> dict:
        """Check compatibility between two libraries.

        Args:
            library1: First library name
            library2: Second library name
            version1: First library version (optional)
            version2: Second library version (optional)

        Returns:
            {
                "library1": str,
                "library2": str,
                "compatible": bool,
                "issues": [str],
                "recommendations": [str],
            }
        """
        try:
            from ..analysis.library_analyzer import get_analyzer

            analyzer = get_analyzer()

            # Analyze both libraries
            analysis1 = await analyzer.analyze_library(library1, current_version=version1)
            analysis2 = await analyzer.analyze_library(library2, current_version=version2)

            if not analysis1 or not analysis2:
                return {
                    "error": "Could not analyze one or both libraries",
                    "library1": library1,
                    "library2": library2,
                }

            # Check for conflicts
            issues = []
            recommendations = []

            # Check Python version compatibility
            py_compat1 = analysis1.compatibility_matrix.get("python", "3.7+")
            py_compat2 = analysis2.compatibility_matrix.get("python", "3.7+")

            if py_compat1 != py_compat2:
                issues.append(
                    f"Different Python version requirements: {library1} ({py_compat1}) vs {library2} ({py_compat2})"
                )

            # Check for shared dependencies
            deps1 = {d.name for d in analysis1.dependencies}
            deps2 = {d.name for d in analysis2.dependencies}
            shared = deps1 & deps2

            if shared:
                issues.append(f"Shared dependencies: {', '.join(shared)}")

            compatible = len(issues) == 0

            return {
                "library1": library1,
                "library2": library2,
                "version1": analysis1.version,
                "version2": analysis2.version,
                "compatible": compatible,
                "issues": issues,
                "shared_dependencies": list(shared),
            }

        except Exception as e:
            logger.error(f"Compatibility check failed: {e}")
            return {
                "error": f"Compatibility check failed: {str(e)}",
                "library1": library1,
                "library2": library2,
            }

    @server.tool()
    def get_library_alternatives(library_name: str) -> dict:
        """Get alternative libraries with similar functionality.

        Args:
            library_name: Library to find alternatives for

        Returns:
            {
                "library": str,
                "alternatives": [
                    {
                        "name": str,
                        "advantage": str,
                    }
                ],
            }
        """
        try:
            from ..analysis.library_analyzer import get_analyzer

            analyzer = get_analyzer()

            # Get alternatives (synchronous method)
            alternatives_task = analyzer._find_alternatives(library_name)

            return {
                "library": library_name,
                "alternatives": alternatives_task,
            }

        except Exception as e:
            logger.error(f"Failed to get alternatives: {e}")
            return {
                "error": f"Failed to get alternatives: {str(e)}",
                "library": library_name,
            }
