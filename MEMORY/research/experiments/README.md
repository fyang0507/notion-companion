# Experiments Directory

*Last Updated: 2025-07-16*

## Purpose

This directory contains experiment summaries and analysis from the evaluation pipeline. Each experiment should be documented with results, insights, and follow-up actions.

## Creating Experiment Summaries

### File Naming Convention
- `YYYY-MM-DD-experiment-name.md` - Individual experiment summary
- `YYYY-MM-DD-comparative-analysis.md` - Multi-experiment comparison

### Template Structure
```markdown
# [Experiment Name]

*Date: YYYY-MM-DD*
*Type: [chunking|question-generation|retrieval-evaluation]*

## Objective
Brief description of what was being tested.

## Methodology
- Configuration used
- Dataset/metrics applied
- Key parameters

## Results
- Key findings (max 5 bullet points)
- Performance metrics
- Unexpected observations

## Insights
- What worked well
- What didn't work
- Lessons learned

## Next Steps
- Follow-up experiments needed
- Configuration changes to try
- Questions to investigate
```

## Data References

- Reference actual data files in `evaluation/data/`
- Link to configuration files used
- Include relevant metrics and charts
- Keep summaries concise (<200 words each section)