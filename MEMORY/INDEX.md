# MEMORY Index

*Last Updated: 2025-07-16*

## Overview
This role-based documentation system replaces scattered project memory (CLAUDE.md, .cursor/rules, various docs/) with a structured approach. Each document serves a specific role in the development process, preventing information overload while maintaining up-to-date project knowledge. The document system requires human and AI agents to collaboratively maintain.

## Quick Links
- [Folder Structure](#folder-structure)
- [Access Control](#document-access-control)
- [Task Types](#task-types)
- [Task Workflows](#task-document-workflows)
- [Summary Integration](#task-summary-workflow)

---

## Folder Structure

```
MEMORY/
├── INDEX.md                 # This file - master reference guide
├── product/                 # Product vision and strategy (HUMAN-MANAGED)
│   ├── overview.md            # Core product vision and features (HUMAN-MANAGED)
│   ├── roadmap.md             # Development milestones and progress (HUMAN-MANAGED)
│   └── decisions.md           # Key architectural and design choices (HUMAN-MANAGED)
├── project_management/        # Task-specific execution tracking
│   ├── bugs.md                # Bugs in the existing system (HUMAN-MANAGED)
│   ├── todos.md               # to-do lists for future tasks(HUMAN-MANAGED)
│   └── recent_changes.md      # Rolling log of recent implementations
├── engineering/             # Technical implementation details
│   ├── architecture.md        # Codebase structure, tech stack overview
│   ├── setup.md               # Dev environment, tooling, dependencies
│   └── standards.md           # Coding standards, SOPs, workflows; Common patterns, gotchas, know-hows
├── research/                # Experimentation, evaluation and analysis
│   └── todos.md               # Future experiments plans (HUMAN-MANAGED)
│   └── metrics.md             # Performance benchmarks
│   └── experiments/           # Records of past experiments and their results
├── archive/                 # Archived task summaries
└── specs/                   # Collection of deep technical specs for individual components
```

### Document Guidelines
- **Size limit**: Maximum 50 lines (excluding code snippets) or 500 words per document
- **Code snippets**: Maximum 10 lines; reference specific files for details
- **Metadata**: Each doc must include `Last Updated: YYYY-MM-DD` header

---

## Document Access Control

### 🔴 HUMAN-ONLY (Agents: READ-ONLY)
- `product/overview.md`
- `product/roadmap.md`  
- `product/decisions.md`
- `project_management/bugs.md`
- `project_management/todos.md`
- `research/todos.md`

**Agent Workflow for Product Updates:**
1. Create proposal: `MEMORY/proposals/YYYY-MM-DD-{feature-name}.md`
2. Add comment: `"⚠️ Requires human review for updates"`
3. Human reviews and manually updates relevant docs
4. Human archives proposal after integration

### 🟢 AGENT-ACCESSIBLE (Read & Write)
All other documents under `project_management/`, `engineering/`, and `research/` that are not marked as HUMAN-MANAGED

---

## Task Types

1. **New Feature Prototyping** - Adding new functionality
2. **Feature Enhancement** - Improving existing features
3. **Tech Debt Reduction & Refactoring** - Improving code quality/structure
4. **Bug Fix & Hotfix** - Fixing reported issues
5. **Reflection/Analysis & Documentation Update** - Code/architecture/security analysis, pure doc improvements
6. **Performance Optimization** - Speed/efficiency improvements
7. **Dependency Update** - Library/framework updates
8. **Configuration Change** - Settings/environment changes
9. **Testing Improvement** - Test coverage/quality
10. **Experimentation & Spike/PoC** - Research or proof-of-concept
11. **DevOps/Infrastructure** - CI/CD, deployment, monitoring
12. **Data Migration** - Schema changes, data transformations

---

## Task Document Workflows

### General Pattern
```
BEFORE: Categorize task → Read relevant docs → understand context
DURING: Reference patterns & standards
AFTER: Update impacted docs → integrate learnings → archive task summary
```

### New Feature
**READ before starting:**
- `product/overview.md`, `product/decisions.md` → align with important decisions
- `engineering/architecture.md` → understand architecture
- `engineering/standards.md`, `engineering/patterns.md` → follow development conventions
- `specs/` → selective reading of relevant component specs to understand the implementation details

**UPDATE after completion:**
- `project_management/recent_changes.md` → document addition
- `engineering/architecture.md`, `specs/` → if new components

### Bug Fix
**READ before starting:**
- `engineering/architecture.md` → locate issue
- `engineering/standards.md`, `engineering/patterns.md` → follow development conventions

**UPDATE after completion:**
- `project_management/recent_changes.md` → note fix
- `engineering/patterns.md` → if new pattern discovered

### Tech Debt Reduction / Refactoring
**READ before starting:**
- `engineering/architecture.md` → understand context
- `engineering/standards.md` → target state
- `product/decisions.md` → respect constraints

**UPDATE after completion:**
- `engineering/architecture.md` → structural changes
- `project_management/recent_changes.md` → document improvements
- `engineering/patterns.md` → new best practices

[Additional task types follow similar patterns - see full mapping above]

---

## Task Summary Workflow After Task Completion
1. **Extract & Integrate:**
   - Add 2-3 bullet summary to `project_management/recent_changes.md`
   - Update relevant permanent docs with learnings

2. **Archive & Cleanup:**
   - Write task summary to `archive/YYYY-MM-DD-{task-name}.md`

### Integration Rules
- One task = One summary (no proliferation)
- Summaries are temporary documents
- Permanent docs are the source of truth
- Recent changes older than 30 days should be archived

---

## Maintenance Guidelines

### Daily (Automated via Agents)
- Update `project_management/todos.md` with new issues
- Append to `project_management/recent_changes.md`

### Weekly (Human)
- Review and consolidate `project_management/recent_changes.md`
- Update product roadmap progress
- Archive old task summaries

### Monthly (Human)
- Audit all docs for staleness
- Update architecture diagrams
- Consolidate patterns and learnings
- Prune `project_management/recent_changes.md` (>30 days)

### Quarterly (Human)
- Major documentation review
- Align docs with actual codebase
- Update product vision/roadmap

---

## For AI Agents

**Remember:**
1. Never modify `product/` documents directly, instead create proposals
2. Create task summaries promptly
3. Reference specific files, not long code blocks
4. Update Last Updated dates when modifying docs