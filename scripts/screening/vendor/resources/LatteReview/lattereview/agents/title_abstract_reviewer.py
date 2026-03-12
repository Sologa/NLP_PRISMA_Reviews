"""Reviewer agent implementation with consistent error handling and type safety."""

from typing import List, Dict, Any, Optional
from .basic_reviewer import BasicReviewer, AgentError

DEFAULT_MAX_RETRIES = 3

generic_prompt_all = """

**Stage 1 Review (Title + Abstract only, high-recall gate)**
You are screening only `title` and `abstract` to decide whether a paper should move to full review.
Do not use or assume any full-text content.

This stage is recall-oriented: keep papers in flow when evidence is weak, and avoid hard exclusion without explicit evidence.

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

1. Output your evaluation as an integer between 1 and 5:
   - 1 強烈排除
   - 2 可能排除
   - 3 不確定 / 需要更多證據
   - 4 可能納入
   - 5 強烈納入
2. Stage 1 constraints:
   - 只看 `title` + `abstract`，不得依賴 full text。
   - 未出現否定性證據時，不應直接用 1 或 2 排除。
   - 對 topic relevance 有一定疑似但不足以證成的，請偏向 3。
3. Sparse metadata 規則（citation-like/keyword-only/metadata 片段）：
   - 不夠明確時不應直接視為 exclusion。
   - 若只有摘要片段且缺關鍵 evidence，請保守為 3 並說明缺什麼。
4. 理由要簡潔：
   - 指出你採用該分數的關鍵證據；若不確定，請明確列出缺少哪一條 criteria 證據。
5. 不要憑空捏造任何事實，不要推測 full text。
---

${reasoning}$

${additional_context}$

${examples}$

"""

generic_prompt_any = """

**Stage 1 Review (Title + Abstract only, high-recall gate)**
You are screening only `title` and `abstract` to decide whether a paper should move to full review.
Do not use or assume any full-text content.

This stage is recall-oriented: keep papers in flow when evidence is weak, and avoid hard exclusion without explicit evidence.

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

1. Output your evaluation as an integer between 1 and 5:
   - 1 強烈排除
   - 2 可能排除
   - 3 不確定 / 需要更多證據
   - 4 可能納入
   - 5 強烈納入
2. Stage 1 constraints:
   - 只看 `title` + `abstract`，不得依賴 full text。
   - 未出現否定性證據時，不應直接用 1 或 2 排除。
   - 對 topic relevance 有一定疑似但不足以證成的，請偏向 3。
3. Sparse metadata 規則（citation-like/keyword-only/metadata 片段）：
   - 不夠明確時不應直接視為 exclusion。
   - 若只有摘要片段且缺關鍵 evidence，請保守為 3 並說明缺什麼。
4. 理由要簡潔：
   - 指出你採用該分數的關鍵證據；若不確定，請明確列出缺少哪一條 criteria 證據。
5. 不要憑空捏造任何事實，不要推測 full text。
---

${reasoning}$

${additional_context}$

${examples}$

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
