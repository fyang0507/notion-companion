# MEMORY Index

*Last Updated: 2025-08-13*

## Overview
This role-based documentation system replaces scattered project memory (CLAUDE.md, .cursor/rules, various docs/) with a structured approach. An agent will read product.md and engineering.md files to gather contexts before crafting a plan.

## Memory Structure

```
MEMORY/
├── INDEX.md                 # This file - master reference guide
├── engineering.md           # Consolidated technical implementation details
├── product.md               # Consolidated product vision and strategy
├── todo.md                 # to-do lists for future tasks (HUMAN-MANAGED)
├── changelog.md        # Rolling log of recent implementations
├── research/                # Experimentation, evaluation and analysis
│   ├── todo.md               # Future experiments plans (HUMAN-MANAGED)
│   ├── metrics.md             # Performance benchmarks
│   └── experiments/           # Records of past experiments and their results
├── archive/                 # Archived task summaries
└── specs/                   # Collection of deep technical specs for individual components
```