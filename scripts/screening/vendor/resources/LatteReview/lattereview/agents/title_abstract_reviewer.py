"""Reviewer agent implementation with consistent error handling and type safety."""

from typing import List, Dict, Any, Optional
from .basic_reviewer import BasicReviewer, AgentError

DEFAULT_MAX_RETRIES = 3

generic_prompt_all = """

**Stage 1 Review (Title + Abstract only)**
You are reviewing only `title` and `abstract` to decide a screening signal for a paper.
Do **not** use or assume any full-text content.
Evaluate whether the paper should be included based on the following criteria.
For this stage, prefer a high-recall filtering rule: if evidence is incomplete, do not force exclusion.

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
2. This is Stage 1 only:
   - Use only the provided `title` and `abstract`.
   - Do not treat missing details as exclusion evidence.
   - If information is insufficient, the correct signal is usually `3` rather than `1` or `2`.
3. If a paper is topically relevant but lacks explicit evidence in title/abstract, preserve it as possible (choose `3`) instead of excluding early.
4. When you are unsure, provide a conservative score (`3`) and explain what is missing.
5. Your response must be brief, and your `reasoning` must state the key evidence for your score in one concise paragraph.
6. Do not invent claims that are not in the provided text.
---

${reasoning}$

${additional_context}$

${examples}$

"""

generic_prompt_any = """

**Stage 1 Review (Title + Abstract only)**
You are reviewing only `title` and `abstract` to decide a screening signal for a paper.
Do **not** use or assume any full-text content.
Evaluate whether the paper should be included based on the following criteria.
For this stage, prefer a high-recall filtering rule: if evidence is incomplete, do not force exclusion.

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
2. This is Stage 1 only:
   - Use only the provided `title` and `abstract`.
   - Do not treat missing details as exclusion evidence.
   - If information is insufficient, the correct signal is usually `3` rather than `1` or `2`.
3. If a paper is topically relevant but lacks explicit evidence in title/abstract, preserve it as possible (choose `3`) instead of excluding early.
4. When you are unsure, provide a conservative score (`3`) and explain what is missing.
5. Your response must be brief, and your `reasoning` must state the key evidence for your score in one concise paragraph.
6. Do not invent claims that are not in the provided text.
---

${reasoning}

${additional_context}

${examples}

"""


class TitleAbstractReviewer(BasicReviewer):
    generic_prompt: Optional[str] = None
    inclusion_criteria: str = ""
    exclusion_criteria: str = ""
    response_format: Dict[str, Any] = {"reasoning": str, "evaluation": int}
    input_description: str = "article title/abstract"
    reasoning: str = "brief"
    max_retries: int = DEFAULT_MAX_RETRIES
    inclusion_match_mode: str = "all"  # "all" or "any"

    def model_post_init(self, __context: Any) -> None:
        """Initialize after Pydantic model initialization."""
        try:
            assert self.reasoning != None, "Reasoning type cannot be None for TitleAbstractReviewer"
            mode = (self.inclusion_match_mode or "all").strip().lower()
            if mode not in ("all", "any"):
                mode = "all"
            # 選擇對應語意的通用提示
            self.generic_prompt = generic_prompt_any if mode == "any" else generic_prompt_all
            self.setup()
        except Exception as e:
            raise AgentError(f"Error initializing agent: {str(e)}")
