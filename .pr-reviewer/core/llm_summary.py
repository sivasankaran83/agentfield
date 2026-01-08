"""
LLM Summary Generator
Uses Claude Sonnet 4 API to generate intelligent PR summaries
"""

import os
import subprocess
from typing import Dict, List, Optional
import json
from anthropic import Anthropic


class LLMSummaryGenerator:
    """
    Generates comprehensive PR summaries using Claude AI
    Analyzes git diffs, commit messages, and code changes
    """

    def __init__(self):
        """Initialize with Anthropic API"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def get_git_diff(self, base_branch: str = "main", head_branch: str = "HEAD") -> str:
        """
        Get git diff between branches
        
        Args:
            base_branch: Base branch for comparison
            head_branch: Head branch (PR branch)
            
        Returns:
            Git diff output
        """
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
            return f"Error getting git diff: {e}"
    
    def get_commit_messages(self, base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
        """
        Get commit messages in the PR
        
        Args:
            base_branch: Base branch
            head_branch: Head branch
            
        Returns:
            List of commit messages
        """
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
            return [f"Error getting commits: {e}"]
    
    def get_changed_file_stats(self, base_branch: str = "main", head_branch: str = "HEAD") -> str:
        """
        Get statistics about changed files
        
        Args:
            base_branch: Base branch
            head_branch: Head branch
            
        Returns:
            File statistics
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", f"{base_branch}...{head_branch}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return result.stdout
        except Exception as e:
            return f"Error getting file stats: {e}"
    
    def generate_comprehensive_summary(
        self,
        base_branch: str = "main",
        head_branch: str = "HEAD",
        max_diff_length: int = 10000
    ) -> Dict:
        """
        Generate comprehensive PR summary using Claude AI
        
        Args:
            base_branch: Base branch for comparison
            head_branch: Head branch (PR branch)
            max_diff_length: Maximum length of diff to analyze
            
        Returns:
            Comprehensive summary dictionary
        """
        
        # Get git information
        git_diff = self.get_git_diff(base_branch, head_branch)
        commit_messages = self.get_commit_messages(base_branch, head_branch)
        file_stats = self.get_changed_file_stats(base_branch, head_branch)
        
        # Truncate diff if too long
        if len(git_diff) > max_diff_length:
            git_diff = git_diff[:max_diff_length] + "\n\n... (truncated)"
        
        # Create prompt for Claude
        prompt = f"""
Analyze this Pull Request and provide a comprehensive summary.

COMMIT MESSAGES:
{json.dumps(commit_messages, indent=2)}

FILE STATISTICS:
{file_stats}

GIT DIFF (changes made):
{git_diff}

Provide a comprehensive analysis in JSON format:

{{
    "executive_summary": "2-3 sentence high-level summary of what this PR does",
    
    "pr_type": "feature|bugfix|refactor|documentation|test|chore|hotfix",
    
    "risk_assessment": "low|medium|high|critical",
    
    "key_changes": [
        "Most important change 1",
        "Most important change 2",
        "Most important change 3"
    ],
    
    "files_affected": {{
        "added": ["list of new files"],
        "modified": ["list of modified files"],
        "deleted": ["list of deleted files"]
    }},
    
    "impact_analysis": {{
        "scope": "small|medium|large - how much of the codebase is affected",
        "complexity": "low|medium|high - how complex are the changes",
        "dependencies": "Are there external dependency changes?",
        "backwards_compatibility": "Does this maintain backwards compatibility?"
    }},
    
    "testing_requirements": [
        "What tests should be run",
        "What test coverage is needed",
        "Edge cases to test"
    ],
    
    "breaking_changes": [
        "List any breaking changes or empty array"
    ],
    
    "security_considerations": [
        "Any security implications",
        "Authentication/authorization changes",
        "Data handling changes"
    ],
    
    "recommendations": [
        "Suggestion 1 for reviewers",
        "Suggestion 2 for reviewers",
        "Areas requiring special attention"
    ],
    
    "estimated_review_time": "5m|15m|30m|1h|2h+ - estimated time to review",
    
    "confidence": "low|medium|high - confidence in this analysis"
}}

Focus on:
- What problem does this solve?
- How does it solve it?
- What are the risks?
- What should reviewers focus on?

Return ONLY valid JSON, no other text.
"""
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract JSON from response
            content = response.content[0].text

            # Parse JSON
            try:
                summary = json.loads(content)
                return summary
            except json.JSONDecodeError:
                # Try to extract JSON if wrapped in markdown
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                    summary = json.loads(content)
                    return summary
                else:
                    raise
        
        except Exception as e:
            # Return error summary
            return {
                "executive_summary": f"Error generating LLM summary: {e}",
                "pr_type": "unknown",
                "risk_assessment": "unknown",
                "key_changes": [],
                "impact_analysis": {},
                "testing_requirements": [],
                "breaking_changes": [],
                "security_considerations": [],
                "recommendations": [],
                "estimated_review_time": "unknown",
                "confidence": "low",
                "error": str(e)
            }
    
    def generate_quick_summary(self, commit_messages: List[str]) -> str:
        """
        Generate a quick one-line summary from commit messages
        
        Args:
            commit_messages: List of commit messages
            
        Returns:
            Quick summary string
        """
        try:
            prompt = f"""
Summarize these commit messages in ONE sentence:

{json.dumps(commit_messages, indent=2)}

Return ONLY the summary sentence, nothing else.
"""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=100,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.content[0].text.strip()
        
        except Exception as e:
            return f"Multiple commits: {len(commit_messages)} changes"
    
    def analyze_code_quality(self, code_snippet: str, language: str) -> Dict:
        """
        Analyze code quality of a specific snippet
        
        Args:
            code_snippet: Code to analyze
            language: Programming language
            
        Returns:
            Quality analysis
        """
        try:
            prompt = f"""
Analyze this {language} code for quality:

```{language}
{code_snippet}
```

Provide analysis in JSON:
{{
    "readability": "excellent|good|fair|poor",
    "maintainability": "excellent|good|fair|poor",
    "issues": ["list specific issues"],
    "suggestions": ["list improvements"],
    "complexity": "low|medium|high"
}}

Return ONLY valid JSON.
"""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text
            return json.loads(content)
        
        except Exception as e:
            return {
                "readability": "unknown",
                "maintainability": "unknown",
                "issues": [str(e)],
                "suggestions": [],
                "complexity": "unknown"
            }
