#!/usr/bin/env python3
"""Script to run PR architecture review from GitHub Actions.

This script is called by the GitHub Action workflow to:
1. Run fitness checks on changed files
2. Analyze impact of ADR/pattern/constraint changes
3. Post review comments to PR
4. Set commit status

Usage:
    python scripts/run_pr_review.py \
        --pr-number 123 \
        --changed-files "file1.py file2.py" \
        --pr-title "Add feature X" \
        --pr-body "Description..." \
        --repo "owner/repo" \
        --commit-sha "abc123" \
        --github-token "$GITHUB_TOKEN" \
        --project-id 1
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.architecture.pr_reviewer import PRReviewer, ReviewAction
from athena.core.database import get_database


def main():
    parser = argparse.ArgumentParser(description="Run PR architecture review")

    parser.add_argument("--pr-number", type=int, required=True, help="PR number")
    parser.add_argument(
        "--changed-files", required=True, help="Space-separated list of changed files"
    )
    parser.add_argument("--pr-title", required=True, help="PR title")
    parser.add_argument("--pr-body", default="", help="PR body/description")
    parser.add_argument("--repo", required=True, help="Repository (owner/repo)")
    parser.add_argument("--commit-sha", required=True, help="Commit SHA")
    parser.add_argument("--github-token", required=True, help="GitHub token")
    parser.add_argument("--project-id", type=int, default=1, help="Project ID")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't post to GitHub, just print results",
    )

    args = parser.parse_args()

    # Parse changed files
    changed_files = args.changed_files.split()

    print(f"🔍 Reviewing PR #{args.pr_number}")
    print(f"   Changed files: {len(changed_files)}")
    print(f"   Title: {args.pr_title}")
    print()

    # Initialize reviewer
    try:
        db = get_database()
        project_root = Path.cwd()
        reviewer = PRReviewer(db, project_root)

        # Run review
        print("📊 Running architecture review...")
        pr_description = f"{args.pr_title}\n\n{args.pr_body}"

        review = reviewer.review_pr(
            pr_number=args.pr_number,
            changed_files=changed_files,
            pr_description=pr_description,
            project_id=args.project_id,
        )

        # Store changed files in metadata for impact analysis
        review.metadata["changed_files"] = changed_files

        # Print summary
        print()
        print("=" * 70)
        print("REVIEW RESULTS")
        print("=" * 70)
        print(f"Action: {review.action.value.upper()}")
        print(f"Summary: {review.summary}")
        print()
        print(f"Fitness Checks:")
        print(f"  ✅ Passed: {review.fitness_passed}")
        print(f"  ❌ Failed: {review.fitness_failed}")
        print(f"  Total Violations: {review.fitness_violations}")
        print()

        if review.adr_changes_detected:
            print(f"ADR Changes: {len(review.adr_changes_detected)}")
            for adr_id in review.adr_changes_detected:
                print(f"  - ADR-{adr_id}")
            print()

        if review.high_risk_changes:
            print(f"⚠️  High-Risk Changes: {len(review.high_risk_changes)}")
            for change in review.high_risk_changes:
                print(f"  - {change}")
            print()

        print(f"Comments: {len(review.comments)}")
        for i, comment in enumerate(review.comments[:5], 1):
            print(f"  {i}. {comment.file_path}")
            if comment.line_number:
                print(f"     Line {comment.line_number}")
            print(f"     [{comment.severity.value.upper()}] {comment.body[:60]}...")
        if len(review.comments) > 5:
            print(f"  ... and {len(review.comments) - 5} more")
        print()
        print("=" * 70)

        # Save results to file
        result_file = f"architecture-review-{args.pr_number}.json"
        with open(result_file, "w") as f:
            json.dump(
                {
                    "pr_number": review.pr_number,
                    "action": review.action.value,
                    "summary": review.summary,
                    "fitness_passed": review.fitness_passed,
                    "fitness_failed": review.fitness_failed,
                    "fitness_violations": review.fitness_violations,
                    "adr_changes": review.adr_changes_detected,
                    "high_risk_changes": review.high_risk_changes,
                    "comments_count": len(review.comments),
                    "reviewed_at": review.reviewed_at,
                },
                f,
                indent=2,
            )
        print(f"📄 Results saved to {result_file}")
        print()

        # Post to GitHub (unless dry-run)
        if not args.dry_run:
            print("📤 Posting review to GitHub...")
            try:
                # Post review
                response = reviewer.post_github_review(
                    pr_number=args.pr_number,
                    review=review,
                    github_token=args.github_token,
                    repo=args.repo,
                )
                print(f"✅ Review posted: {response.get('html_url', 'N/A')}")

                # Set commit status
                status_response = reviewer.set_pr_status(
                    pr_number=args.pr_number,
                    review=review,
                    github_token=args.github_token,
                    repo=args.repo,
                    commit_sha=args.commit_sha,
                )
                print(f"✅ Status set: {status_response.get('state', 'N/A')}")

            except Exception as e:
                print(f"❌ Error posting to GitHub: {e}")
                print("   (Review results still saved locally)")
        else:
            print("🚫 Dry-run mode - not posting to GitHub")

        # Exit code based on action
        if review.action == ReviewAction.REQUEST_CHANGES:
            print()
            print("🚫 Exiting with error code 1 (critical issues found)")
            sys.exit(1)
        else:
            print()
            print("✅ Review complete")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error during review: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
