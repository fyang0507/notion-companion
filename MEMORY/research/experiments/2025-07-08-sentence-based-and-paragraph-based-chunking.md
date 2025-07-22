# Sentence-based and newline/paragraph-based chunking

*Last Updated: 2025-07-08*

## Purpose
Tested sentence-based and newline/paragraph-based chunking strategies.

## Results
- Sentence-based: the similarity between adjacent sentences is pretty low, making it meaningless to break down by sentence level.
- Newline/Paragraph-based: Notion treat multiple "Enter" as double newlines (no matter how many "Enter"s are there), so newline and paragraph-based chunking are the same.

## Decision
Keep paragraph-based chunking.