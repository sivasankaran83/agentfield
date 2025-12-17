"""
Git Utilities
Helper functions for git operations
"""

import subprocess
from typing import List


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
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base_branch}...{head_branch}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            return files
        
        except Exception as e:
            print(f"Error getting changed files: {e}")
            return []
    
    @staticmethod
    def get_git_diff(base_branch: str = "main", head_branch: str = "HEAD") -> str:
        """Get git diff between branches"""
        try:
            result = subprocess.run(
                ["git", "diff", f"{base_branch}...{head_branch}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return result.stdout
        except Exception as e:
            return f"Error: {e}"
    
    @staticmethod
    def get_commit_messages(base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
        """Get commit messages between branches"""
        try:
            result = subprocess.run(
                ["git", "log", f"{base_branch}..{head_branch}", "--pretty=format:%s"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            messages = [msg.strip() for msg in result.stdout.split('\n') if msg.strip()]
            return messages
        except Exception as e:
            return [f"Error: {e}"]
