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

class OverallIssueStrategy(BaseModel):
    """Complete issue analysis strategy - simplified"""
    model_config = ConfigDict(extra='allow')

    test_failures_analysis: Optional[str] = Field(None, description="Test failures: root_cause, strategy, automatable, risk, dependencies")
    linting_issues_analysis: Optional[str] = Field(None, description="Linting issues: root_cause, strategy, automatable, risk, dependencies")
    security_issues_analysis: Optional[str] = Field(None, description="Security issues: root_cause, strategy, automatable, risk, dependencies")
    breaking_changes_analysis: Optional[str] = Field(None, description="Breaking changes: root_cause, strategy, automatable, risk, dependencies")
    overall_strategy: str = Field(..., description="High-level approach")
    focus_areas: List[str] = Field(..., description="Priority areas to focus on")


class ExecutionPlan(BaseModel):
    """Complete execution plan for remediation - simplified"""
    model_config = ConfigDict(extra='allow')

    phases: List[str] = Field(..., description="Execution phases with format: 'Phase N: name - fix_ids - parallel(yes/no) - description - minutes - validation'")
    testing_strategy: str = Field(..., description="How to test after fixes")
    rollback_strategy: str = Field(..., description="How to rollback if needed")
    risks: List[str] = Field(default_factory=list, description="Potential risks")
    human_review_points: List[str] = Field(default_factory=list, description="Where human should check")


class PlanValidationResult(BaseModel):
    """Results of validating a remediation plan - simplified"""
    model_config = ConfigDict(extra='allow')

    valid: bool = Field(..., description="Whether plan is valid")
    completeness_score: int = Field(..., ge=0, le=100, description="Completeness score 0-100")
    issues: List[str] = Field(default_factory=list, description="Issues found with format: '[severity] issue: suggestion'")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvements")
    confidence: str = Field(..., description="Confidence in validation: low|medium|high")
    recommendation: str = Field(..., description="Final recommendation: approve|revise|reject")


# ============================================================================
# EXECUTOR AGENT SCHEMAS
# ============================================================================

class TestFixSuggestion(BaseModel):
    """AI suggestion for fixing a test - simplified"""
    model_config = ConfigDict(extra='allow')

    root_cause: str = Field(..., description="Why test is failing")
    files_to_modify: List[str] = Field(..., description="Files that need changes")
    changes: List[str] = Field(..., description="Specific code changes with format: 'file:line action old_code->new_code (explanation)'")
    confidence: str = Field(..., description="Confidence in fix: low|medium|high")
    test_after_fix: bool = Field(..., description="Whether to run tests after")
    additional_steps: List[str] = Field(default_factory=list, description="Manual steps needed")


class LintingFixSuggestion(BaseModel):
    """AI suggestion for fixing a linting issue - simplified"""
    model_config = ConfigDict(extra='allow')

    fixed_code: str = Field(..., description="Corrected code section")
    explanation: str = Field(..., description="What was fixed and why")
    confidence: str = Field(..., description="Confidence in fix: low|medium|high")


class SecurityFixSuggestion(BaseModel):
    """AI suggestion for fixing a security issue - simplified"""
    model_config = ConfigDict(extra='allow')

    vulnerability_type: str = Field(..., description="Type of vulnerability")
    risk_explanation: str = Field(..., description="Why this is dangerous")
    fix_strategy: str = Field(..., description="High-level fix approach")
    fixed_code: str = Field(..., description="Complete fixed file content")
    security_best_practices: List[str] = Field(..., description="Best practices applied")
    additional_steps: List[str] = Field(default_factory=list, description="Other security measures")
    confidence: str = Field(..., description="Confidence in fix: low|medium|high")


class ExecutionSummary(BaseModel):
    """Summary of execution for human review"""
    model_config = ConfigDict(extra='allow')

    text: str = Field(..., description="2-3 sentence summary of execution")


# ============================================================================
# GENERATOR AGENT SCHEMAS
# ============================================================================

class CommitMessage(BaseModel):
    """Generated commit message"""
    model_config = ConfigDict(extra='allow')

    message: str = Field(..., description="Full commit message in conventional commits format")


class PRDescription(BaseModel):
    """Generated PR description"""
    model_config = ConfigDict(extra='allow')

    markdown: str = Field(..., description="Markdown-formatted PR description")


class ActionDecision(BaseModel):
    """Decision on what action to take - simplified"""
    model_config = ConfigDict(extra='allow')

    action: str = Field(..., description="Action to take: merge|update_pr|manual_review|abort")
    confidence: str = Field(..., description="Decision confidence: low|medium|high")
    reasoning: str = Field(..., description="Why this action was chosen")
    requires_human_approval: bool = Field(..., description="Whether human approval needed")
    next_steps: List[str] = Field(..., description="What happens next")


class MergeSafetyCheck(BaseModel):
    """Final safety check before merge - simplified"""
    model_config = ConfigDict(extra='allow')

    safe_to_merge: bool = Field(..., description="Whether safe to merge")
    confidence: str = Field(..., description="Confidence level: low|medium|high")
    concerns: List[str] = Field(default_factory=list, description="Remaining concerns")
    recommendation: str = Field(..., description="Final recommendation: merge|wait|manual_review")
    final_checks: List[str] = Field(..., description="Checklist for human review")


class FinalReport(BaseModel):
    """Final comprehensive report"""
    model_config = ConfigDict(extra='allow')

    narrative: str = Field(..., description="Markdown narrative report")


# ============================================================================
# SUMMARIZATION AGENT SCHEMAS
# ============================================================================

class AnalysisPlan(BaseModel):
    """Plan for analyzing the PR"""
    model_config = ConfigDict(extra='allow')

    priority_languages: List[str] = Field(..., description="Languages to analyze first")
    analysis_types: List[str] = Field(..., description="Types of analysis to perform")
    skip_analysis: List[str] = Field(default_factory=list, description="Analysis types to skip")
    focus_areas: List[str] = Field(..., description="Specific areas to focus on")
    rationale: str = Field(..., description="Why this order and approach")


class SOLIDPrinciples(BaseModel):
    """Complete SOLID principles analysis - simplified"""
    model_config = ConfigDict(extra='allow')

    srp_rating: str = Field(..., description="Single Responsibility Principle rating: excellent|good|fair|poor")
    srp_violations: List[str] = Field(default_factory=list, description="SRP violations with file:line")
    ocp_rating: str = Field(..., description="Open/Closed Principle rating")
    ocp_violations: List[str] = Field(default_factory=list, description="OCP violations")
    lsp_rating: str = Field(..., description="Liskov Substitution Principle rating")
    lsp_violations: List[str] = Field(default_factory=list, description="LSP violations")
    isp_rating: str = Field(..., description="Interface Segregation Principle rating")
    isp_violations: List[str] = Field(default_factory=list, description="ISP violations")
    dip_rating: str = Field(..., description="Dependency Inversion Principle rating")
    dip_violations: List[str] = Field(default_factory=list, description="DIP violations")


class DesignPatterns(BaseModel):
    """Design patterns analysis"""
    model_config = ConfigDict(extra='allow')

    good_patterns: List[str] = Field(..., description="Well-implemented patterns")
    pattern_misuse: List[str] = Field(..., description="Incorrectly applied patterns")
    missing_patterns: List[str] = Field(..., description="Where patterns would help")


class AntiPatterns(BaseModel):
    """Anti-patterns detection - simplified"""
    model_config = ConfigDict(extra='allow')

    detected_patterns: List[str] = Field(..., description="List of detected anti-patterns with type, severity, location, description, and recommendation in one string")
    critical_count: int = Field(default=0, description="Number of critical issues")
    high_count: int = Field(default=0, description="Number of high severity issues")
    medium_count: int = Field(default=0, description="Number of medium severity issues")
    low_count: int = Field(default=0, description="Number of low severity issues")


class CodeOrganization(BaseModel):
    """Code organization assessment - simplified"""
    model_config = ConfigDict(extra='allow')

    separation_of_concerns: str = Field(..., description="SoC quality: excellent|good|fair|poor")
    layering: str = Field(..., description="Layering assessment with issues")
    module_cohesion: str = Field(..., description="Cohesion quality: excellent|good|fair|poor")
    structure_quality: str = Field(..., description="Overall structure: excellent|good|fair|poor")


class CouplingCohesion(BaseModel):
    """Coupling and cohesion analysis - simplified"""
    model_config = ConfigDict(extra='allow')

    coupling: str = Field(..., description="Coupling level: high|medium|low")
    cohesion: str = Field(..., description="Cohesion level: high|medium|low")
    issues: List[str] = Field(default_factory=list, description="Specific coupling/cohesion issues")


class DependencyManagement(BaseModel):
    """Dependency management assessment - simplified"""
    model_config = ConfigDict(extra='allow')

    injection_quality: str = Field(..., description="DI quality: excellent|good|fair|poor")
    singleton_overuse: bool = Field(..., description="Whether singletons are overused")
    circular_dependencies: List[str] = Field(default_factory=list, description="Circular deps found")
    global_state: List[str] = Field(default_factory=list, description="Global state issues")


class Testability(BaseModel):
    """Testability assessment - simplified"""
    model_config = ConfigDict(extra='allow')

    test_coverage_estimate: str = Field(..., description="Estimated test coverage")
    issues: List[str] = Field(default_factory=list, description="Testability issues")
    mockability: str = Field(..., description="How easy to mock: excellent|good|fair|poor")


class Maintainability(BaseModel):
    """Maintainability assessment"""
    model_config = ConfigDict(extra='allow')

    complexity_hotspots: List[str] = Field(..., description="Complex areas")
    documentation_gaps: List[str] = Field(..., description="Missing documentation")
    naming_issues: List[str] = Field(..., description="Naming problems")
    duplication: List[str] = Field(..., description="Code duplication")


class OverallArchitecturalAssessment(BaseModel):
    """Overall architectural quality assessment - simplified"""
    model_config = ConfigDict(extra='allow')

    architectural_quality: str = Field(..., description="Overall quality: excellent|good|fair|poor")
    technical_debt_level: str = Field(..., description="Tech debt level: low|medium|high")
    refactoring_priority: str = Field(..., description="Refactoring urgency: immediate|soon|eventual|none")
    major_concerns: List[str] = Field(default_factory=list, description="Top 3-5 concerns")
    strengths: List[str] = Field(default_factory=list, description="Architectural strengths")


class ArchitecturalRecommendations(BaseModel):
    """Architectural improvement recommendations - simplified"""
    model_config = ConfigDict(extra='allow')

    immediate: List[str] = Field(default_factory=list, description="Critical fixes needed now")
    short_term: List[str] = Field(default_factory=list, description="Improvements for next sprint")
    long_term: List[str] = Field(default_factory=list, description="Strategic refactoring")


class ArchitecturalAnalysis(BaseModel):
    """Complete architectural design analysis"""
    model_config = ConfigDict(extra='allow')

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


class ComprehensiveInsights(BaseModel):
    """Comprehensive AI insights combining all analyses - simplified"""
    model_config = ConfigDict(extra='allow')

    assessment: str = Field(..., description="Overall assessment: ready_to_merge|needs_work|critical_issues|architectural_refactoring_needed")
    priorities: List[str] = Field(..., description="Top 5 priorities with format: 'Priority N [category] impact: description'")
    risk_level: str = Field(..., description="Risk level: low|medium|high|critical")
    estimated_effort_hours: float = Field(..., description="Estimated effort in hours")
    blocking_issues: List[str] = Field(default_factory=list, description="Issues blocking merge with format: '[type] severity: description'")
    architectural_concerns_block_merge: bool = Field(..., description="Whether arch concerns block merge")
    recommendations: List[str] = Field(..., description="Immediate and long-term actions")
    strengths: List[str] = Field(default_factory=list, description="PR strengths")
    summary: str = Field(..., description="2-3 sentence overall summary")


# ============================================================================
# VERIFIER AGENT SCHEMAS
# ============================================================================

class VerificationAnalysis(BaseModel):
    """AI analysis of verification results - simplified"""
    model_config = ConfigDict(extra='allow')

    ready_to_merge: bool = Field(..., description="Whether ready to merge")
    quality_improvement: str = Field(..., description="Quality improvement level: significant|moderate|minimal|negative|none")
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues remaining")
    high_issues: List[str] = Field(default_factory=list, description="High priority issues remaining")
    medium_issues: List[str] = Field(default_factory=list, description="Medium priority issues remaining")
    new_issues: List[str] = Field(default_factory=list, description="New issues introduced")
    recommendation: str = Field(..., description="Recommendation: merge|fix_and_rerun|rollback|manual_review")
    rationale: str = Field(..., description="Explanation of recommendation")
    confidence: str = Field(..., description="Confidence level: low|medium|high")


class IssuePrioritization(BaseModel):
    """Prioritization of remaining issues - simplified"""
    model_config = ConfigDict(extra='allow')

    blocking_issues: List[str] = Field(..., description="Issues blocking merge with format: 'issue - reason - estimated_time'")
    can_defer: List[str] = Field(default_factory=list, description="Issues that can wait")
    next_steps: List[str] = Field(..., description="Ordered list of actions")
    estimated_time_to_unblock: str = Field(..., description="Total time to unblock")


class ImprovementSuggestions(BaseModel):
    """Comprehensive improvement suggestions - simplified"""
    model_config = ConfigDict(extra='allow')

    code_improvements: List[str] = Field(..., description="Code improvements with format: 'area: suggestion (impact)'")
    testing_improvements: List[str] = Field(default_factory=list, description="Testing improvements with format: 'area: suggestion (impact)'")
    security_improvements: List[str] = Field(default_factory=list, description="Security improvements with format: 'area: suggestion (impact)'")
    architectural_improvements: List[str] = Field(default_factory=list, description="Architectural improvements with format: 'area: suggestion (impact)'")
    priority_order: List[str] = Field(..., description="Priority order of actions")
