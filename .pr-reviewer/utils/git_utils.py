"""
Git Utilities
Helper functions for git operations and GitHub PR interactions
"""

import subprocess
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GitUtils:
    """Utility class for git operations"""

    @staticmethod
    def get_changed_files(base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
        """
        Get list of changed files between branches

        Args:
            base_branch: Base branch
            head_branch: Head branch

        Returns:
            List of changed file paths
        """
        try:
            # In GitHub Actions, the base branch might not be checked out locally
            # Try to fetch it first if we're in a CI environment
            try:
                subprocess.run(
                    ["git", "fetch", "origin", f"{base_branch}:{base_branch}"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            except subprocess.CalledProcessError:
                # Branch might already exist or fetch failed, continue anyway
                logger.debug(f"Could not fetch {base_branch}, it may already exist locally")
                pass

            # Try with origin/ prefix first (works in CI environments)
            try:
                result = subprocess.run(
                    ["git", "diff", "--name-only", f"origin/{base_branch}...{head_branch}"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )
            except subprocess.CalledProcessError:
                # Fall back to local branch reference
                logger.debug(f"Trying local branch reference instead of origin/{base_branch}")
                result = subprocess.run(
                    ["git", "diff", "--name-only", f"{base_branch}...{head_branch}"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )

            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            return files

        except subprocess.CalledProcessError as e:
            error_msg = f"Git command failed (exit {e.returncode}): {e.stderr.strip() if e.stderr else 'no stderr'}"
            logger.error(f"Error getting changed files: {error_msg}")
            return []
        except Exception as e:
            logger.error(f"Error getting changed files: {e}")
            return []

    @staticmethod
    def get_git_diff(base_branch: str = "main", head_branch: str = "HEAD") -> str:
        """Get git diff between branches"""
        try:
            # Try to fetch base branch if needed
            try:
                subprocess.run(
                    ["git", "fetch", "origin", f"{base_branch}:{base_branch}"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            except subprocess.CalledProcessError:
                logger.debug(f"Could not fetch {base_branch}, it may already exist locally")
                pass

            # Try with origin/ prefix first
            try:
                result = subprocess.run(
                    ["git", "diff", f"origin/{base_branch}...{head_branch}"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )
            except subprocess.CalledProcessError:
                # Fall back to local branch reference
                result = subprocess.run(
                    ["git", "diff", f"{base_branch}...{head_branch}"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )

            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Git command failed (exit {e.returncode}): {e.stderr.strip() if e.stderr else 'no stderr'}"
            logger.error(f"Error getting git diff: {error_msg}")
            return f"Error: {error_msg}"
        except Exception as e:
            logger.error(f"Error getting git diff: {e}")
            return f"Error: {e}"

    @staticmethod
    def get_commit_messages(base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
        """Get commit messages between branches"""
        try:
            # Try to fetch base branch if needed
            try:
                subprocess.run(
                    ["git", "fetch", "origin", f"{base_branch}:{base_branch}"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            except subprocess.CalledProcessError:
                logger.debug(f"Could not fetch {base_branch}, it may already exist locally")
                pass

            # Try with origin/ prefix first
            try:
                result = subprocess.run(
                    ["git", "log", f"origin/{base_branch}..{head_branch}", "--pretty=format:%s"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )
            except subprocess.CalledProcessError:
                # Fall back to local branch reference
                result = subprocess.run(
                    ["git", "log", f"{base_branch}..{head_branch}", "--pretty=format:%s"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )

            messages = [msg.strip() for msg in result.stdout.split('\n') if msg.strip()]
            return messages
        except subprocess.CalledProcessError as e:
            error_msg = f"Git command failed (exit {e.returncode}): {e.stderr.strip() if e.stderr else 'no stderr'}"
            logger.error(f"Error getting commit messages: {error_msg}")
            return [f"Error: {error_msg}"]
        except Exception as e:
            logger.error(f"Error getting commit messages: {e}")
            return [f"Error: {e}"]


class GitHubUtils:
    """Utility class for GitHub PR interactions"""

    @staticmethod
    def post_comment(pr, message: str, console=None) -> bool:
        """
        Post comment to PR

        Args:
            pr: GitHub Pull Request object
            message: Comment message to post
            console: Optional rich Console for output

        Returns:
            True if successful, False otherwise
        """
        try:
            pr.create_issue_comment(message)
            if console:
                console.print("[green]✅ Posted comment[/green]")
            else:
                logger.info("Posted comment to PR")
            return True
        except Exception as e:
            error_msg = f"Failed to post comment: {e}"
            if console:
                console.print(f"[red]❌ {error_msg}[/red]")
            else:
                logger.error(error_msg)
            return False

    @staticmethod
    def post_json_as_comment(
        pr,
        title: str,
        data: Dict[str, Any],
        summary_text: str = "",
        console=None
    ) -> bool:
        """
        Post JSON data as a collapsible details comment in PR

        Args:
            pr: GitHub Pull Request object
            title: Title for the comment section
            data: JSON data to post
            summary_text: Optional summary text to show before JSON
            console: Optional rich Console for output

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create collapsible JSON section
            json_str = json.dumps(data, indent=2)

            comment = f"""## {title}

{summary_text}

<details>
<summary>📋 View Full JSON Results (click to expand)</summary>

```json
{json_str}
```

</details>
"""

            success = GitHubUtils.post_comment(pr, comment, console=None)

            if success:
                if console:
                    console.print("[green]✅ Posted JSON data as PR comment[/green]")
                else:
                    logger.info(f"Posted JSON data as PR comment: {title}")

            return success

        except Exception as e:
            error_msg = f"Failed to post JSON comment: {e}"
            if console:
                console.print(f"[red]❌ {error_msg}[/red]")
            else:
                logger.error(error_msg)
            return False

    @staticmethod
    def get_json_from_pr_comments(pr, title_pattern: str, console=None) -> Optional[Dict[str, Any]]:
        """
        Extract JSON data from PR comments by searching for a specific title

        Args:
            pr: GitHub Pull Request object
            title_pattern: Pattern to match in comment title (e.g., "Analysis Results")
            console: Optional rich Console for output

        Returns:
            Parsed JSON data or None if not found
        """
        if console:
            console.print(f"[dim]Looking for JSON with title pattern: {title_pattern}[/dim]")
        else:
            logger.debug(f"Looking for JSON with title pattern: {title_pattern}")

        try:
            for comment in pr.get_issue_comments():
                comment_body = comment.body
                if title_pattern in comment_body and "```json" in comment_body:
                    # Extract JSON from code block
                    try:
                        json_start = comment_body.find("```json") + 7
                        json_end = comment_body.find("```", json_start)
                        if json_end > json_start:
                            json_str = comment_body[json_start:json_end].strip()
                            data = json.loads(json_str)

                            if console:
                                console.print("[green]✅ Found JSON data in PR comments[/green]")
                            else:
                                logger.info(f"Found JSON data in PR comments: {title_pattern}")

                            return data
                    except json.JSONDecodeError as e:
                        warning_msg = f"Failed to parse JSON from comment: {e}"
                        if console:
                            console.print(f"[yellow]⚠️  {warning_msg}[/yellow]")
                        else:
                            logger.warning(warning_msg)
                        continue

            error_msg = f"No JSON found with pattern '{title_pattern}'"
            if console:
                console.print(f"[red]❌ {error_msg}[/red]")
            else:
                logger.warning(error_msg)

            return None

        except Exception as e:
            error_msg = f"Error retrieving JSON from comments: {e}"
            if console:
                console.print(f"[red]❌ {error_msg}[/red]")
            else:
                logger.error(error_msg)
            return None
