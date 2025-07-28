# MEMORY Index

*Last Updated: 2025-07-25*

## Overview
This role-based documentation system replaces scattered project memory (CLAUDE.md, .cursor/rules, various docs/) with a structured approach. When you are working on a task, you should categorize the task, read the relevant docs in the `MEMORY/` folder to understand the context.

## Memory Structure

```
MEMORY/
├── INDEX.md                 # This file - master reference guide
├── HUMANREADME.md           # Human-specific maintenance guidelines
├── product/                 # Product vision and strategy (HUMAN-MANAGED)
│   ├── overview.md            # Core product vision and features (HUMAN-MANAGED)
│   ├── roadmap.md             # Development milestones and progress (HUMAN-MANAGED)
│   └── decisions.md           # Key architectural and design choices (HUMAN-MANAGED)
├── project_management/      # Task-specific execution tracking
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