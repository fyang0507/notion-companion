# TODOs: Research

*Last Updated: 2025-07-21*

## Question Generation Self-verification
For every ⟨q, a⟩ pair, ask the same LLM to answer q given the full doc.  Keep only if the answer it produces contains the exact gold span (string match or ≥ 0.9 Rouge-L). This discards ~20 % noisy items automatically.

## Embedding Generation
- Summary / Question embedding; user query matching ANY(summary, question, chunk)

## Baseline benchmark
- paragraph-based chunking, no token overlap, no semantic merging