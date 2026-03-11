"""Reviewer for full-text screening with consistent output schema."""

from typing import Dict, Any, Optional

from .basic_reviewer import BasicReviewer, AgentError

DEFAULT_MAX_RETRIES = 3

generic_prompt_all = """

**Stage 2 Review (Full Text)**
You are reviewing the provided full text to make the final criteria decision for this paper.
Evaluate against all inclusion and exclusion criteria using the text itself, not general impressions.
For exclusion claims and inclusion claims, base each judgment only on text evidence.

---

**Input item:**
<<${item}$>>

---

**Inclusion criteria:**
${inclusion_criteria}$

**Exclusion criteria:**
${exclusion_criteria}$

---

**Instructions**

1. Output your evaluation as an integer between 1 and 5, where:
   - 1 means strongly not include
   - 2 means likely not include
   - 3 means uncertain / need more evidence
   - 4 means likely include
   - 5 means strongly include
2. Prefer explicit evidence from the full text:
   - quote or paraphrase the exact signals for I1/I2/I3/E1/E2/E3/E4/E5 when deciding your score.
   - if a claim is not stated or is only implied, do not over-interpret it.
3. Your reasoning must be concise and explain the key pieces of evidence that drove inclusion vs exclusion.
4. Do not invent findings not present in the full text; if evidence is missing, use a conservative score (`3`) rather than guessing.
5. Keep the rationale focused on criteria-level evidence, not writing style or reputation.
---

${reasoning}$

${additional_context}$

${examples}$

"""

generic_prompt_any = """

**Stage 2 Review (Full Text)**
You are reviewing the provided full text to make the final criteria decision for this paper.
Evaluate against all inclusion and exclusion criteria using the text itself, not general impressions.
For exclusion claims and inclusion claims, base each judgment only on text evidence.

---

**Input item:**
<<${item}$>>

---

**Inclusion criteria:**
${inclusion_criteria}$

**Exclusion criteria:**
${exclusion_criteria}$

---

**Instructions**

1. Output your evaluation as an integer between 1 and 5, where:
   - 1 means strongly not include
   - 2 means likely not include
   - 3 means uncertain / need more evidence
   - 4 means likely include
   - 5 means strongly include
2. Prefer explicit evidence from the full text:
   - quote or paraphrase the exact signals for I1/I2/I3/E1/E2/E3/E4/E5 when deciding your score.
   - if a claim is not stated or is only implied, do not over-interpret it.
3. Your reasoning must be concise and explain the key pieces of evidence that drove inclusion vs exclusion.
4. Do not invent findings not present in the full text; if evidence is missing, use a conservative score (`3`) rather than guessing.
5. Keep the rationale focused on criteria-level evidence, not writing style or reputation.
---

${reasoning}$

${additional_context}$

${examples}$

"""


class FullTextReviewer(BasicReviewer):
    generic_prompt: Optional[str] = None
    inclusion_criteria: str = ""
    exclusion_criteria: str = ""
    response_format: Dict[str, Any] = {"reasoning": str, "evaluation": int}
    input_description: str = "article full text"
    reasoning: str = "brief"
    max_retries: int = DEFAULT_MAX_RETRIES
    inclusion_match_mode: str = "all"  # "all" or "any"

    def model_post_init(self, __context: Any) -> None:
        """Initialize after Pydantic model initialization."""
        try:
            assert self.reasoning is not None, "Reasoning type cannot be None for FullTextReviewer"
            mode = (self.inclusion_match_mode or "all").strip().lower()
            if mode not in ("all", "any"):
                mode = "all"
            self.generic_prompt = generic_prompt_any if mode == "any" else generic_prompt_all
            self.setup()
        except Exception as e:
            raise AgentError(f"Error initializing agent: {str(e)}")
