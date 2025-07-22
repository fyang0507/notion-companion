# Proposals Directory

*Last Updated: 2025-07-16*

## Purpose

This directory contains proposals from AI agents for updates to HUMAN-MANAGED documents.

## Workflow

When AI agents need to suggest updates to human-managed documents:

1. **Create proposal**: `YYYY-MM-DD-{feature-name}.md`
2. **Add marker**: `"⚠️ Requires human review for updates"`
3. **Human reviews** and manually updates relevant docs
4. **Human archives** proposal after integration

## Human-Managed Documents

AI agents cannot directly edit:
- `product/overview.md`
- `product/roadmap.md`  
- `product/decisions.md`
- `project_management/bugs.md`
- `project_management/todos.md`
- `research/todos.md`

## Proposal Template

```markdown
# [Feature Name] - Product Update Proposal

*Date: YYYY-MM-DD*

## Target Documents
- [ ] product/overview.md
- [ ] product/roadmap.md
- [ ] project_management/bugs.md
- ...

## Proposed Changes
Description of suggested updates.

## Rationale
Why these changes are needed.

⚠️ **Requires human review for updates**
```