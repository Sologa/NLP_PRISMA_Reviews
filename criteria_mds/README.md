# Criteria + Screening Question Sets (Bulleted / Atomic)

This zip contains:
- One Markdown file per SR paper (named by arXiv ID).
  - Original extracted criteria (Stage 1 retrieval / Stage 2 screening / QA if present).
  - A section listing **metadata-only programmable conditions** (出版時間 / peer-reviewed / paper 長度 / open-access).
  - A **Screening Question Set** section designed for an extraction agent (quote + location; no include/exclude decisions).

- `AGENT_PROMPT_generate_question_set_from_criteria.md`:
  - A reusable prompt for an agent that converts criteria → screening question set.

Usage tip:
- When you run the extraction agent, only provide the **Screening Question Set** section (do not provide the criteria section).
- After you get answers, apply inclusion/exclusion rules deterministically in your own pipeline.