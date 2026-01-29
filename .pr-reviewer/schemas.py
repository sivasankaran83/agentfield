"""
Pydantic Schemas for PR Reviewer Agents

This module defines all Pydantic models used across the PR reviewer agent system.
These schemas ensure proper JSON structure for AI responses and enable type-safe
agent communication.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime


# ============================================================================
# PLANNER AGENT SCHEMAS
# ============================================================================

class IssueStrategyAnalysis(BaseModel):
    """Analysis strategy for a specific issue category"""
    model_config = ConfigDict(extra='forbid')

    root_cause: str = Field(..., description="Explanation of why these issues exist")
    strategy: str = Field(..., description="Fix approach for these issues")
    automatable: bool = Field(..., description="Whether fixes can be automated")
    risk: Literal["low", "medium", "high"] = Field(..., description="Risk level of applying fixes")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies for fixing")


class OverallIssueStrategy(BaseModel):
    """Complete issue analysis strategy"""
    model_config = ConfigDict(extra='forbid')

    test_failures: Optional[IssueStrategyAnalysis] = None
    linting_issues: Optional[IssueStrategyAnalysis] = None
    security_issues: Optional[IssueStrategyAnalysis] = None
    breaking_changes: Optional[IssueStrategyAnalysis] = None
    overall_strategy: str = Field(..., description="High-level approach")
    focus_areas: List[str] = Field(..., description="Priority areas to focus on")


class ExecutionPhase(BaseModel):
    """A phase in the remediation execution plan"""
    model_config = ConfigDict(extra='forbid')

    phase: int = Field(..., description="Phase number")
    name: str = Field(..., description="Phase name")
    fix_ids: List[str] = Field(..., description="IDs of fixes to apply in this phase")
    parallel: bool = Field(..., description="Whether fixes can run in parallel")
    description: str = Field(..., description="What this phase accomplishes")
    estimated_minutes: int = Field(..., description="Estimated time for this phase")
    validation: str = Field(..., description="How to validate after completion")


class ExecutionPlan(BaseModel):
    """Complete execution plan for remediation"""
    model_config = ConfigDict(extra='forbid')

    phases: List[ExecutionPhase] = Field(..., description="Execution phases")
    testing_strategy: str = Field(..., description="How to test after fixes")
    rollback_strategy: str = Field(..., description="How to rollback if needed")
    risks: List[str] = Field(..., description="Potential risks")
    human_review_points: List[str] = Field(..., description="Where human should check")


class ValidationIssue(BaseModel):
    """An issue found during plan validation"""
    model_config = ConfigDict(extra='forbid')

    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="Issue severity")
    issue: str = Field(..., description="Description of problem")
    suggestion: str = Field(..., description="How to fix")


class PlanValidationResult(BaseModel):
    """Results of validating a remediation plan"""
    model_config = ConfigDict(extra='forbid')

    valid: bool = Field(..., description="Whether plan is valid")
    completeness_score: int = Field(..., ge=0, le=100, description="Completeness score 0-100")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Issues found")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvements")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence in validation")
    recommendation: Literal["approve", "revise", "reject"] = Field(..., description="Final recommendation")


# ============================================================================
# EXECUTOR AGENT SCHEMAS
# ============================================================================

class FixChange(BaseModel):
    """A single code change made as part of a fix"""
    model_config = ConfigDict(extra='forbid')

    file: str = Field(..., description="File path")
    action: Literal["replace", "insert", "delete"] = Field(..., description="Type of change")
    line_number: Optional[int] = Field(None, description="Line number affected")
    old_code: Optional[str] = Field(None, description="Code being replaced")
    new_code: Optional[str] = Field(None, description="New code")
    explanation: str = Field(..., description="Why this fixes the issue")


class TestFixSuggestion(BaseModel):
    """AI suggestion for fixing a test"""
    model_config = ConfigDict(extra='forbid')

    root_cause: str = Field(..., description="Why test is failing")
    files_to_modify: List[str] = Field(..., description="Files that need changes")
    changes: List[FixChange] = Field(..., description="Specific code changes")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence in fix")
    test_after_fix: bool = Field(..., description="Whether to run tests after")
    additional_steps: List[str] = Field(default_factory=list, description="Manual steps needed")


class LintingFixSuggestion(BaseModel):
    """AI suggestion for fixing a linting issue"""
    model_config = ConfigDict(extra='forbid')

    fixed_code: str = Field(..., description="Corrected code section")
    explanation: str = Field(..., description="What was fixed and why")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence in fix")


class SecurityFixSuggestion(BaseModel):
    """AI suggestion for fixing a security issue"""
    model_config = ConfigDict(extra='forbid')

    vulnerability_type: str = Field(..., description="Type of vulnerability")
    risk_explanation: str = Field(..., description="Why this is dangerous")
    fix_strategy: str = Field(..., description="High-level fix approach")
    fixed_code: str = Field(..., description="Complete fixed file content")
    security_best_practices: List[str] = Field(..., description="Best practices applied")
    additional_steps: List[str] = Field(default_factory=list, description="Other security measures")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence in fix")


class ExecutionSummary(BaseModel):
    """Summary of execution for human review"""
    model_config = ConfigDict(extra='forbid')

    text: str = Field(..., description="2-3 sentence summary of execution")


# ============================================================================
# GENERATOR AGENT SCHEMAS
# ============================================================================

class CommitMessage(BaseModel):
    """Generated commit message"""
    model_config = ConfigDict(extra='forbid')

    message: str = Field(..., description="Full commit message in conventional commits format")


class PRDescription(BaseModel):
    """Generated PR description"""
    model_config = ConfigDict(extra='forbid')

    markdown: str = Field(..., description="Markdown-formatted PR description")


class ActionDecision(BaseModel):
    """Decision on what action to take"""
    model_config = ConfigDict(extra='forbid')

    action: Literal["merge", "update_pr", "manual_review", "abort"] = Field(..., description="Action to take")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Decision confidence")
    reasoning: str = Field(..., description="Why this action was chosen")
    requires_human_approval: bool = Field(..., description="Whether human approval needed")
    next_steps: List[str] = Field(..., description="What happens next")


class MergeSafetyCheck(BaseModel):
    """Final safety check before merge"""
    model_config = ConfigDict(extra='forbid')

    safe_to_merge: bool = Field(..., description="Whether safe to merge")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence level")
    concerns: List[str] = Field(default_factory=list, description="Remaining concerns")
    recommendation: Literal["merge", "wait", "manual_review"] = Field(..., description="Final recommendation")
    final_checks: List[str] = Field(..., description="Checklist for human review")


class FinalReport(BaseModel):
    """Final comprehensive report"""
    model_config = ConfigDict(extra='forbid')

    narrative: str = Field(..., description="Markdown narrative report")


# ============================================================================
# SUMMARIZATION AGENT SCHEMAS
# ============================================================================

class AnalysisPlan(BaseModel):
    """Plan for analyzing the PR"""
    model_config = ConfigDict(extra='forbid')

    priority_languages: List[str] = Field(..., description="Languages to analyze first")
    analysis_types: List[str] = Field(..., description="Types of analysis to perform")
    skip_analysis: List[str] = Field(default_factory=list, description="Analysis types to skip")
    focus_areas: List[str] = Field(..., description="Specific areas to focus on")
    rationale: str = Field(..., description="Why this order and approach")


class SOLIDPrincipleAnalysis(BaseModel):
    """Analysis of a single SOLID principle"""
    model_config = ConfigDict(extra='forbid')

    rating: Literal["excellent", "good", "fair", "poor"] = Field(..., description="Adherence rating")
    violations: List[str] = Field(default_factory=list, description="Specific violations with file:line")


class SOLIDPrinciples(BaseModel):
    """Complete SOLID principles analysis"""
    model_config = ConfigDict(extra='forbid')

    srp: SOLIDPrincipleAnalysis = Field(..., description="Single Responsibility Principle")
    ocp: SOLIDPrincipleAnalysis = Field(..., description="Open/Closed Principle")
    lsp: SOLIDPrincipleAnalysis = Field(..., description="Liskov Substitution Principle")
    isp: SOLIDPrincipleAnalysis = Field(..., description="Interface Segregation Principle")
    dip: SOLIDPrincipleAnalysis = Field(..., description="Dependency Inversion Principle")


class DesignPatterns(BaseModel):
    """Design patterns analysis"""
    model_config = ConfigDict(extra='forbid')

    good_patterns: List[str] = Field(..., description="Well-implemented patterns")
    pattern_misuse: List[str] = Field(..., description="Incorrectly applied patterns")
    missing_patterns: List[str] = Field(..., description="Where patterns would help")


class AntiPattern(BaseModel):
    """A detected anti-pattern"""
    model_config = ConfigDict(extra='forbid')

    type: str = Field(..., description="Type of anti-pattern")
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="Severity")
    location: str = Field(..., description="File and location")
    description: str = Field(..., description="What's wrong")
    recommendation: str = Field(..., description="How to fix")

class SeverityCounts(BaseModel):
    model_config = ConfigDict(extra='forbid')
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    
class AntiPatterns(BaseModel):
    """Anti-patterns detection"""
    model_config = ConfigDict(extra='forbid')
    detected: List[AntiPattern]
    count_by_severity: SeverityCounts


class CodeOrganization(BaseModel):
    """Code organization assessment"""
    model_config = ConfigDict(extra='forbid')

    separation_of_concerns: Literal["excellent", "good", "fair", "poor"] = Field(..., description="SoC quality")
    layering: str = Field(..., description="Layering assessment with issues")
    module_cohesion: Literal["excellent", "good", "fair", "poor"] = Field(..., description="Cohesion quality")
    structure_quality: Literal["excellent", "good", "fair", "poor"] = Field(..., description="Overall structure")


class CouplingCohesion(BaseModel):
    """Coupling and cohesion analysis"""
    model_config = ConfigDict(extra='forbid')

    coupling: Literal["high", "medium", "low"] = Field(..., description="Coupling level")
    cohesion: Literal["high", "medium", "low"] = Field(..., description="Cohesion level")
    issues: List[str] = Field(..., description="Specific coupling/cohesion issues")


class DependencyManagement(BaseModel):
    """Dependency management assessment"""
    model_config = ConfigDict(extra='forbid')

    injection_quality: Literal["excellent", "good", "fair", "poor"] = Field(..., description="DI quality")
    singleton_overuse: bool = Field(..., description="Whether singletons are overused")
    circular_dependencies: List[str] = Field(default_factory=list, description="Circular deps found")
    global_state: List[str] = Field(default_factory=list, description="Global state issues")


class Testability(BaseModel):
    """Testability assessment"""
    model_config = ConfigDict(extra='forbid')

    test_coverage_estimate: str = Field(..., description="Estimated test coverage")
    issues: List[str] = Field(..., description="Testability issues")
    mockability: Literal["excellent", "good", "fair", "poor"] = Field(..., description="How easy to mock")


class Maintainability(BaseModel):
    """Maintainability assessment"""
    model_config = ConfigDict(extra='forbid')

    complexity_hotspots: List[str] = Field(..., description="Complex areas")
    documentation_gaps: List[str] = Field(..., description="Missing documentation")
    naming_issues: List[str] = Field(..., description="Naming problems")
    duplication: List[str] = Field(..., description="Code duplication")


class OverallArchitecturalAssessment(BaseModel):
    """Overall architectural quality assessment"""
    model_config = ConfigDict(extra='forbid')

    architectural_quality: Literal["excellent", "good", "fair", "poor"] = Field(..., description="Overall quality")
    technical_debt_level: Literal["low", "medium", "high"] = Field(..., description="Tech debt level")
    refactoring_priority: Literal["immediate", "soon", "eventual", "none"] = Field(..., description="Refactoring urgency")
    major_concerns: List[str] = Field(..., description="Top 3-5 concerns")
    strengths: List[str] = Field(..., description="Architectural strengths")


class ArchitecturalRecommendations(BaseModel):
    """Architectural improvement recommendations"""
    model_config = ConfigDict(extra='forbid')

    immediate: List[str] = Field(..., description="Critical fixes needed now")
    short_term: List[str] = Field(..., description="Improvements for next sprint")
    long_term: List[str] = Field(..., description="Strategic refactoring")


class ArchitecturalAnalysis(BaseModel):
    """Complete architectural design analysis"""
    model_config = ConfigDict(extra='forbid')

    solid_principles: SOLIDPrinciples = Field(..., description="SOLID principles adherence")
    design_patterns: DesignPatterns = Field(..., description="Design patterns analysis")
    anti_patterns: AntiPatterns = Field(..., description="Anti-patterns detected")
    code_organization: CodeOrganization = Field(..., description="Organization quality")
    coupling_cohesion: CouplingCohesion = Field(..., description="Coupling/cohesion analysis")
    dependency_management: DependencyManagement = Field(..., description="Dependency management")
    testability: Testability = Field(..., description="Testability assessment")
    maintainability: Maintainability = Field(..., description="Maintainability concerns")
    overall_assessment: OverallArchitecturalAssessment = Field(..., description="Overall assessment")
    recommendations: ArchitecturalRecommendations = Field(..., description="Recommendations")


class PriorityItem(BaseModel):
    """A priority item to address"""
    model_config = ConfigDict(extra='forbid')

    priority: int = Field(..., ge=1, description="Priority rank")
    category: Literal["architecture", "testing", "security", "quality"] = Field(..., description="Category")
    issue: str = Field(..., description="Issue description")
    impact: Literal["high", "medium", "low"] = Field(..., description="Impact level")


class BlockingIssue(BaseModel):
    """An issue that blocks merge"""
    model_config = ConfigDict(extra='forbid')

    type: Literal["architecture", "security", "functionality"] = Field(..., description="Issue type")
    description: str = Field(..., description="Issue description")
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="Severity")


class ComprehensiveInsights(BaseModel):
    """Comprehensive AI insights combining all analyses"""
    model_config = ConfigDict(extra='forbid')

    assessment: Literal["ready_to_merge", "needs_work", "critical_issues", "architectural_refactoring_needed"] = Field(..., description="Overall assessment")
    priorities: List[PriorityItem] = Field(..., description="Top 5 priorities")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Risk level")
    estimated_effort_hours: float = Field(..., description="Estimated effort in hours")
    blocking_issues: List[BlockingIssue] = Field(..., description="Issues blocking merge")
    architectural_concerns_block_merge: bool = Field(..., description="Whether arch concerns block merge")
    recommendations: List[str] = Field(..., description="Immediate and long-term actions")
    strengths: List[str] = Field(..., description="PR strengths")
    summary: str = Field(..., description="2-3 sentence overall summary")


# ============================================================================
# VERIFIER AGENT SCHEMAS
# ============================================================================

class RemainingIssues(BaseModel):
    """Remaining issues after fixes"""
    model_config = ConfigDict(extra='forbid')

    critical: List[str] = Field(default_factory=list, description="Critical issues")
    high: List[str] = Field(default_factory=list, description="High priority issues")
    medium: List[str] = Field(default_factory=list, description="Medium priority issues")


class VerificationAnalysis(BaseModel):
    """AI analysis of verification results"""
    model_config = ConfigDict(extra='forbid')

    ready_to_merge: bool = Field(..., description="Whether ready to merge")
    quality_improvement: Literal["significant", "moderate", "minimal", "negative", "none"] = Field(..., description="Quality improvement level")
    remaining_issues: RemainingIssues = Field(..., description="Remaining issues by priority")
    new_issues: List[str] = Field(default_factory=list, description="New issues introduced")
    recommendation: Literal["merge", "fix_and_rerun", "rollback", "manual_review"] = Field(..., description="Recommendation")
    rationale: str = Field(..., description="Explanation of recommendation")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence level")


class BlockingIssueDetail(BaseModel):
    """Detail of an issue blocking merge"""
    model_config = ConfigDict(extra='forbid')

    issue: str = Field(..., description="Issue description")
    reason: str = Field(..., description="Why it blocks merge")
    estimated_time: str = Field(..., description="Estimated time to fix")


class IssuePrioritization(BaseModel):
    """Prioritization of remaining issues"""
    model_config = ConfigDict(extra='forbid')

    blocking_issues: List[BlockingIssueDetail] = Field(..., description="Issues blocking merge")
    can_defer: List[str] = Field(..., description="Issues that can wait")
    next_steps: List[str] = Field(..., description="Ordered list of actions")
    estimated_time_to_unblock: str = Field(..., description="Total time to unblock")


class ImprovementSuggestion(BaseModel):
    """A specific improvement suggestion"""
    model_config = ConfigDict(extra='forbid')

    area: str = Field(..., description="Area to improve")
    suggestion: str = Field(..., description="What to do")
    impact: str = Field(..., description="Expected benefit")


class ImprovementSuggestions(BaseModel):
    """Comprehensive improvement suggestions"""
    model_config = ConfigDict(extra='forbid')

    code_improvements: List[ImprovementSuggestion] = Field(..., description="Code improvements")
    testing_improvements: List[ImprovementSuggestion] = Field(..., description="Testing improvements")
    security_improvements: List[ImprovementSuggestion] = Field(..., description="Security improvements")
    architectural_improvements: List[ImprovementSuggestion] = Field(..., description="Architectural improvements")
    priority_order: List[str] = Field(..., description="Priority order of actions")
