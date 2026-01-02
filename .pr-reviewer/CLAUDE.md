# 📁 CLAUDE.md - Directory Structure Guide

**Complete guide to the PR Reviewer Agent directory structure when deployed to your repository**

---

## 🎯 Overview

When you deploy the PR Reviewer Agent to your repository, it creates a `.pr-reviewer/` directory containing all agent code, configurations, and runtime files. This document explains every file and directory.

---

## 📂 Complete Directory Structure

```
your-repository/
│
├── .github/
│   └── workflows/
│       └── pr-reviewer-interactive.yml          # GitHub Actions workflow
│
├── .pr-reviewer/                                 # PR Reviewer root directory
│   │
│   ├── agents/                                   # Agent implementations
│   │   ├── summarization_agent.py               # Analyzes PRs comprehensively
│   │   ├── planner_agent.py                     # Creates remediation plans
│   │   ├── executor_agent.py                    # Applies fixes to code
│   │   ├── verifier_agent.py                    # Verifies changes
│   │   └── orchestrator_agent.py                # Coordinates workflow (optional)
│   │
│   ├── core/                                     # Core functionality modules
│   │   ├── __init__.py                          # Package initializer
│   │   ├── language_tools.py                    # Multi-language tool registry
│   │   ├── llm_summary.py                       # Claude API integration
│   │   ├── summarizer.py                        # Enhanced summarization
│   │   └── human_loop.py                        # Human feedback handling
│   │
│   ├── utils/                                    # Utility functions
│   │   ├── __init__.py                          # Package initializer
│   │   └── git_utils.py                         # Git operations wrapper
│   │
│   ├── scripts/                                  # Helper scripts
│   │   ├── github_workflow_runner.py            # Main orchestrator for GitHub Actions
│   │   ├── create_test_pr.sh                    # Creates test PRs
│   │   └── deploy_to_codebase.sh                # Deployment script (optional)
│   │
│   ├── agentfield/                               # AgentField control plane
│   │   ├── control-plane/                       # (Cloned during workflow)
│   │   ├── sdk/                                 # AgentField SDK
│   │   └── ...                                  # Other AgentField files
│   │
│   ├── logs/                                     # Runtime logs (gitignored)
│   │   ├── agentfield.log                       # AgentField control plane log
│   │   ├── summarizer.log                       # Summarizer agent log
│   │   ├── planner.log                          # Planner agent log
│   │   ├── executor.log                         # Executor agent log
│   │   └── verifier.log                         # Verifier agent log
│   │
│   ├── results/                                  # Review results (gitignored)
│   │   ├── summary_result.json                  # Analysis results
│   │   ├── plan_result.json                     # Remediation plan
│   │   ├── execution_result.json                # Execution results
│   │   └── verification_result.json             # Verification results
│   │
│   ├── requirements.txt                          # Python dependencies
│   ├── config.yml                                # Configuration file
│   └── README.md                                 # Quick reference guide
│
├── your-source-code/                             # Your actual codebase
│   ├── src/
│   ├── tests/
│   └── ...
│
└── .gitignore                                    # Updated to ignore logs/
```

---

## 📋 File-by-File Explanation

### **GitHub Actions Workflow**

#### `.github/workflows/pr-reviewer-interactive.yml`
**Purpose:** GitHub Actions workflow that runs the PR reviewer  
**Triggers:** PR creation, PR updates, `@pr-reviewer` comments  
**Actions:**
- Checks out code
- Sets up Python and Go
- Installs dependencies
- Starts AgentField control plane
- Starts all 5 agents
- Runs github_workflow_runner.py
- Posts results to PR

**Size:** ~150 lines  
**Language:** YAML  
**Editable:** Yes (customize triggers, timeouts, etc.)

---

### **Agent Files** (`/.pr-reviewer/agents/`)

#### `summarization_agent.py`
**Purpose:** Analyzes PR changes comprehensively  
**What it does:**
- Detects programming languages
- Runs tests (pytest, jest, go test, etc.)
- Runs linters (pylint, eslint, golangci-lint, etc.)
- Runs security scanners (bandit, gosec, etc.)
- Analyzes architecture (SOLID principles, design patterns)
- Generates LLM summary using Claude Sonnet 4

**Size:** ~640 lines  
**Language:** Python  
**AgentField Integration:**
```python
app = Agent(node_id="pr-reviewer-summarizer")

@app.reasoner()
async def analyze_pr_comprehensive(pr_number, base_branch, head_branch, repository):
    # Analysis logic
    return comprehensive_summary
```

**Endpoint:** `POST /api/v1/execute/pr-reviewer-summarizer.analyze_pr_comprehensive`

---

#### `planner_agent.py`
**Purpose:** Creates prioritized remediation plans  
**What it does:**
- Analyzes issues from summary
- Incorporates human context/feedback
- Prioritizes fixes (critical → high → medium → low)
- Estimates time for each fix
- Creates actionable plan

**Size:** ~500 lines  
**Language:** Python  
**AgentField Integration:**
```python
app = Agent(node_id="pr-reviewer-planner")

@app.reasoner()
async def create_remediation_plan(summary, pr_info, pr_comments, human_context):
    # Planning logic
    return remediation_plan
```

**Endpoint:** `POST /api/v1/execute/pr-reviewer-planner.create_remediation_plan`

---

#### `executor_agent.py`
**Purpose:** Applies fixes to code  
**What it does:**
- Executes remediation plan
- Fixes test failures using AI
- Fixes security vulnerabilities
- Fixes linting issues
- Applies code formatting
- Creates backups before changes
- Commits changes to PR branch

**Size:** ~760 lines  
**Language:** Python  
**AgentField Integration:**
```python
app = Agent(node_id="pr-reviewer-executor")

@app.reasoner()
async def execute_remediation_plan(plan):
    # Execution logic
    return execution_results
```

**Endpoint:** `POST /api/v1/execute/pr-reviewer-executor.execute_remediation_plan`

**Skills:**
- `read_file()` - Read file contents
- `write_file()` - Write file contents
- `run_command()` - Execute shell commands
- `git_commit()` - Commit changes
- `create_backup()` - Backup files
- `apply_formatting()` - Auto-format code

---

#### `verifier_agent.py`
**Purpose:** Verifies changes and checks human feedback alignment  
**What it does:**
- Re-runs tests to verify fixes
- Re-runs security scanners
- Checks code quality improvement
- Verifies human expectations met
- Decides if replanning needed
- Provides final recommendation

**Size:** ~600 lines  
**Language:** Python  
**AgentField Integration:**
```python
app = Agent(node_id="pr-reviewer-verifier")

@app.reasoner()
async def verify_fixes_comprehensive(original_summary, remediation_plan, execution_result):
    # Verification logic
    return verification_results
```

**Endpoint:** `POST /api/v1/execute/pr-reviewer-verifier.verify_fixes_comprehensive`

---

#### `orchestrator_agent.py` (Optional)
**Purpose:** High-level workflow coordination  
**What it does:**
- Coordinates agent interactions
- Manages workflow state
- Handles errors and retries

**Size:** ~400 lines  
**Language:** Python  
**Status:** Optional - github_workflow_runner.py handles orchestration

---

### **Core Modules** (`/.pr-reviewer/core/`)

#### `language_tools.py`
**Purpose:** Multi-language tool registry and execution  
**What it does:**
- Detects programming languages from file extensions
- Manages tools for each language (test, lint, format, security)
- Executes language-specific tools
- Parses tool output

**Supported Languages:**
- Python (pytest, pylint, black, bandit, mypy)
- TypeScript/JavaScript (jest, eslint, prettier, tsc)
- Go (go test, golangci-lint, gosec, gofmt)
- Java (maven, junit, checkstyle)
- Rust (cargo test, clippy, rustfmt)
- C++ (gtest, clang-tidy, clang-format)
- C# (dotnet test, roslyn)
- Ruby (rspec, rubocop)

**Size:** ~300 lines  
**Key Class:** `LanguageToolRegistry`

---

#### `llm_summary.py`
**Purpose:** Claude API integration for summaries  
**What it does:**
- Generates executive summaries
- Assesses PR risk level
- Identifies key changes
- Categorizes PR type (feature/bugfix/refactor)

**Size:** ~350 lines  
**API Used:** Anthropic Claude Sonnet 4  
**Key Function:** `generate_llm_summary()`

---

#### `summarizer.py`
**Purpose:** Enhanced multi-language summarization  
**What it does:**
- Orchestrates language detection
- Runs all language-specific tools
- Aggregates results
- Generates comprehensive summary

**Size:** ~450 lines  
**Key Class:** `EnhancedMultiLanguageSummarizer`

---

#### `human_loop.py`
**Purpose:** Human feedback integration  
**What it does:**
- Extracts human context from PR comments
- Parses user instructions
- Tracks feedback alignment
- Manages replanning based on feedback

**Size:** ~250 lines  
**Key Functions:**
- `extract_human_context()`
- `check_feedback_alignment()`

---

### **Utilities** (`/.pr-reviewer/utils/`)

#### `git_utils.py`
**Purpose:** Git operations wrapper  
**What it does:**
- Get changed files
- Get diffs
- Commit changes
- Push to remote
- Create/switch branches

**Size:** ~150 lines  
**Key Class:** `GitUtils`

---

### **Scripts** (`/.pr-reviewer/scripts/`)

#### `github_workflow_runner.py`
**Purpose:** Main orchestrator for GitHub Actions  
**What it does:**
- Parses workflow action (analyze/proceed/execute/merge)
- Calls appropriate agents via AgentField API
- Posts results to PR as comments
- Manages workflow state
- Handles errors

**Size:** ~650 lines  
**Language:** Python  
**Usage:**
```bash
python github_workflow_runner.py \
  --pr-number 123 \
  --action analyze \
  --repo yourorg/yourrepo
```

**Actions:**
- `analyze` - Initial PR analysis
- `proceed` - Create remediation plan
- `execute` - Apply fixes
- `merge` - Final approval

**API Calls:**
```python
# Analyze
POST /api/v1/execute/pr-reviewer-summarizer.analyze_pr_comprehensive

# Plan
POST /api/v1/execute/pr-reviewer-planner.create_remediation_plan

# Execute
POST /api/v1/execute/pr-reviewer-executor.execute_remediation_plan

# Verify
POST /api/v1/execute/pr-reviewer-verifier.verify_fixes_comprehensive
```

---

#### `create_test_pr.sh`
**Purpose:** Creates test PRs automatically  
**What it does:**
- Creates new branch
- Adds intentional bugs
- Creates PR
- Triggers workflow

**Size:** ~200 lines  
**Language:** Bash  
**Test Issues Created:**
- SQL injection vulnerability
- Hard-coded credentials
- Failing tests
- Linting issues
- God Object pattern

---

### **AgentField** (`/.pr-reviewer/agentfield/`)

#### Purpose
AgentField control plane and SDK for managing agents

#### Contents
- `control-plane/` - AgentField server (Go)
- `sdk/` - Python SDK
- `Makefile` - Build/install commands

#### How it's set up
**Option 1: Cloned during workflow**
```yaml
- name: Setup AgentField
  run: |
    cd .pr-reviewer
    git clone https://github.com/Agent-Field/agentfield.git
    cd agentfield
    make install
```

**Option 2: Pre-included in repo**
```bash
# Copy during deployment
cp -r agentfield/ .pr-reviewer/
```

#### Why it's needed
- Provides control plane server
- Routes requests to agents
- Manages agent lifecycle

---

### **Logs** (`/.pr-reviewer/logs/`)

#### Purpose
Runtime logs from agents and AgentField

#### Files (gitignored)
```
logs/
├── agentfield.log          # Control plane log
├── summarizer.log          # Summarizer agent log
├── planner.log             # Planner agent log
├── executor.log            # Executor agent log
└── verifier.log            # Verifier agent log
```

#### How to view
**In GitHub Actions:**
```yaml
- name: Upload Logs
  uses: actions/upload-artifact@v4
  with:
    name: agent-logs
    path: .pr-reviewer/logs/
```

Download artifacts from workflow run.

**Locally:**
```bash
tail -f .pr-reviewer/logs/summarizer.log
```

---

### **Results** (`/.pr-reviewer/results/`)

#### Purpose
Stores results from each workflow phase

#### Files (gitignored)
```
results/
├── summary_result.json         # Analysis results
├── plan_result.json           # Remediation plan
├── execution_result.json      # Execution results
└── verification_result.json   # Verification results
```

#### Why stored
- Passed between workflow phases
- Available for debugging
- Uploaded as artifacts

#### Example structure
**summary_result.json:**
```json
{
  "pr_number": 123,
  "metadata": {
    "total_files_changed": 5,
    "languages_detected": ["Python"]
  },
  "language_analysis": {
    "python": {
      "test_results": {...},
      "linting_results": {...}
    }
  },
  "llm_summary": {...},
  "architectural_analysis": {...}
}
```

---

### **Configuration Files**

#### `requirements.txt`
**Purpose:** Python dependencies  
**Source:** Copied from `requirements-github-actions.txt`  
**Size:** ~80 lines  
**Contains:**
- agentfield
- anthropic
- PyGithub
- pytest, pylint, black, etc.

**Installation:**
```bash
pip install -r .pr-reviewer/requirements.txt
```

---

#### `config.yml`
**Purpose:** Agent configuration  
**Generated by:** Deployment script  
**Customizable:** Yes

**Structure:**
```yaml
project:
  name: "Your Project"
  repository: "yourorg/yourrepo"
  main_branch: "main"

languages:
  python:
    enabled: true
    version: "3.11"
    tools: [pytest, pylint, black, bandit]
  
  typescript:
    enabled: true
    version: "5.0"
    tools: [jest, eslint, prettier, tsc]

features:
  architectural_analysis:
    enabled: true
  security_scanning:
    enabled: true
  test_coverage:
    enabled: true
    minimum_coverage: 80
  human_feedback_loop:
    enabled: true
    max_iterations: 3

review_rules:
  block_on:
    - critical_security_issues
    - failing_tests
  warn_on:
    - linting_issues
    - missing_documentation
```

---

#### `README.md`
**Purpose:** Quick reference for team  
**Contents:**
- Quick commands
- Workflow overview
- Adding context
- Support links

---

### **Git Configuration**

#### `.gitignore` (updated)
```gitignore
# PR Reviewer Agent
.pr-reviewer/logs/
.pr-reviewer/results/
.pr-reviewer/*.log
.pr-reviewer/agentfield/  # Optional
```

**Why gitignored:**
- `logs/` - Runtime logs change constantly
- `results/` - Temporary workflow state
- `agentfield/` - Large, can be cloned during workflow

---

## 📊 Size Summary

| Directory/File | Size | Lines | Purpose |
|----------------|------|-------|---------|
| `agents/` | ~2.5 MB | ~3000 | Agent implementations |
| `core/` | ~150 KB | ~1500 | Core functionality |
| `utils/` | ~20 KB | ~200 | Utilities |
| `scripts/` | ~100 KB | ~1000 | Helper scripts |
| `agentfield/` | ~50 MB | ~50000 | Control plane (optional in repo) |
| **Total (without AgentField)** | **~3 MB** | **~6000** | Version controlled |
| **Total (with AgentField)** | **~53 MB** | **~56000** | Full installation |

---

## 🔄 Workflow Data Flow

```
1. PR Created/Updated
   ↓
2. GitHub Actions starts
   ↓
3. Agents start, register with AgentField
   ↓
4. github_workflow_runner.py executes

   ┌─────────────────────────────────────┐
   │ ANALYZE                             │
   ├─────────────────────────────────────┤
   │ summarization_agent.py              │
   │ ↓                                   │
   │ results/summary_result.json         │
   │ ↓                                   │
   │ PR Comment: "Analysis Complete"     │
   └─────────────────────────────────────┘
   
   Human: @pr-reviewer proceed
   
   ┌─────────────────────────────────────┐
   │ PLAN                                │
   ├─────────────────────────────────────┤
   │ planner_agent.py                    │
   │ ← reads summary_result.json         │
   │ ← reads PR comments                 │
   │ ↓                                   │
   │ results/plan_result.json            │
   │ ↓                                   │
   │ PR Comment: "Remediation Plan"      │
   └─────────────────────────────────────┘
   
   Human: @pr-reviewer execute
   
   ┌─────────────────────────────────────┐
   │ EXECUTE                             │
   ├─────────────────────────────────────┤
   │ executor_agent.py                   │
   │ ← reads plan_result.json            │
   │ ↓                                   │
   │ Modifies code files                 │
   │ Commits to PR branch                │
   │ ↓                                   │
   │ results/execution_result.json       │
   │ ↓                                   │
   │ PR Comment: "Execution Complete"    │
   │ ↓                                   │
   │ Auto-triggers verify                │
   └─────────────────────────────────────┘
   
   ┌─────────────────────────────────────┐
   │ VERIFY                              │
   ├─────────────────────────────────────┤
   │ verifier_agent.py                   │
   │ ← reads summary_result.json         │
   │ ← reads plan_result.json            │
   │ ← reads execution_result.json       │
   │ ← reads PR comments                 │
   │ ↓                                   │
   │ Re-runs tests                       │
   │ Checks feedback alignment           │
   │ ↓                                   │
   │ results/verification_result.json    │
   │ ↓                                   │
   │ PR Comment: "Verification Complete" │
   └─────────────────────────────────────┘
   
   If replanning needed: Go to PLAN
   
   Human: @pr-reviewer merge
   
   ┌─────────────────────────────────────┐
   │ MERGE                               │
   ├─────────────────────────────────────┤
   │ ← reads verification_result.json    │
   │ ↓                                   │
   │ PR Comment: "Ready to Merge!"       │
   └─────────────────────────────────────┘
```

---

## 🎯 What Gets Version Controlled

### **Committed to Git** ✅
```
.github/workflows/pr-reviewer-interactive.yml
.pr-reviewer/agents/*.py
.pr-reviewer/core/*.py
.pr-reviewer/utils/*.py
.pr-reviewer/scripts/*.py
.pr-reviewer/requirements.txt
.pr-reviewer/config.yml
.pr-reviewer/README.md
.gitignore (updated)
```

### **Gitignored** ❌
```
.pr-reviewer/logs/
.pr-reviewer/results/
.pr-reviewer/*.log
.pr-reviewer/agentfield/  # Optional - can be cloned
```

---

## 🚀 Quick Reference

### **Start Agents Locally**
```bash
cd .pr-reviewer

# Start AgentField
cd agentfield/control-plane
go run ./cmd/af dev &

# Start agents
cd ../..
python agents/summarization_agent.py &
python agents/planner_agent.py &
python agents/executor_agent.py &
python agents/verifier_agent.py &
```

### **Test Workflow Locally**
```bash
cd .pr-reviewer

python scripts/github_workflow_runner.py \
  --pr-number 123 \
  --action analyze \
  --repo yourorg/yourrepo
```

### **Create Test PR**
```bash
cd .pr-reviewer
./scripts/create_test_pr.sh
```

### **View Logs**
```bash
# Agent logs
tail -f .pr-reviewer/logs/summarizer.log

# All logs
tail -f .pr-reviewer/logs/*.log
```

### **Check Results**
```bash
# View analysis
cat .pr-reviewer/results/summary_result.json | jq

# View plan
cat .pr-reviewer/results/plan_result.json | jq
```

---

## 📚 Documentation Files

Located in repository root:

- `README.md` - Main documentation
- `EMBEDDED_ARCHITECTURE.md` - Architecture overview
- `GITHUB_ACTIONS_INTEGRATION.md` - Workflow setup
- `DEPLOYMENT_GUIDE.md` - Deployment instructions
- `TROUBLESHOOTING.md` - Common issues
- `AGENTFIELD_API_CORRECT.md` - API reference
- `CLAUDE.md` - This file!

---

## 🎉 Summary

**The `.pr-reviewer/` directory contains everything needed to run the PR Reviewer Agent:**

✅ **5 intelligent agents** - Analyze, plan, execute, verify  
✅ **Core modules** - Language tools, LLM integration, summarization  
✅ **Utilities** - Git operations, helpers  
✅ **Scripts** - Orchestrator, test PR creator  
✅ **AgentField** - Control plane (cloned or included)  
✅ **Configuration** - Customizable settings  
✅ **Logs & Results** - Runtime data (gitignored)  

**Total size: ~3 MB (version controlled) or ~53 MB (with AgentField)**

**The complete AI-powered PR review system lives in your repository! 🚀🤖✨**
