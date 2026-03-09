"""Reviewer agent implementation with consistent error handling and type safety."""

from typing import List, Dict, Any, Optional
from .basic_reviewer import BasicReviewer, AgentError

DEFAULT_MAX_RETRIES = 3

generic_prompt_all = """

**Review the title and abstract below and evaluate whether they should be included based on the following inclusion and exclusion criteria (if any).**
**Note that the study should be included only and only if it meets ALL inclusion criteria and NONE of the exclusion criteria.**

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
   - 1 means absolutely to exclude.
   - 2 means better to exclude.
   - 3 Not sure if to include or exclude.
   - 4 means better to include.
   - 5 means absolutely to include.
---

${reasoning}$

${additional_context}$

${examples}$

"""

generic_prompt_any = """

**Review the title and abstract below and evaluate whether they should be included based on the following inclusion and exclusion criteria (if any).**
**Note that the study should be included only and only if it meets ANY of the inclusion criteria and NONE of the exclusion criteria.**

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
   - 1 means absolutely to exclude.
   - 2 means better to exclude.
   - 3 Not sure if to include or exclude.
   - 4 means better to include.
   - 5 means absolutely to include.
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
