"""Reviewer for full-text screening with consistent output schema."""

from typing import Dict, Any, Optional

from .basic_reviewer import BasicReviewer, AgentError

DEFAULT_MAX_RETRIES = 3

generic_prompt_all = """

**Stage 2 Review (Full Text, criteria-level)**
You are doing final full-text screening for this paper.
Decide based on explicit criteria evidence in the text, not on overall impression.

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
   - 1 強烈不納入
   - 2 可能不納入
   - 3 不確定 / 需要更多證據
   - 4 可能納入
   - 5 強烈納入
2. 評估必須逐條對齊 criteria：
   - 只用 full text 文字片段（title/abstract + provided full text）支持每個判斷。
   - 未明確提到的主張不算作證據；避免把隱含訊息硬推斷為事實。
3. 請列出關鍵證據：哪個 criteria 因何被支持、哪個無法支持、哪個有缺口。
4. 若證據缺失，不要猜測，保守給 `3`，並在 reasoning 中標明「缺少何種可追溯依據」。
5. reasoning 必須可追溯、可驗證，聚焦證據與 criteria，而非模型印象或作者聲望。

---

${reasoning}$

${additional_context}$

${examples}$

"""

generic_prompt_any = """

**Stage 2 Review (Full Text, criteria-level)**
You are doing final full-text screening for this paper.
Decide based on explicit criteria evidence in the text, not on overall impression.

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
   - 1 強烈不納入
   - 2 可能不納入
   - 3 不確定 / 需要更多證據
   - 4 可能納入
   - 5 強烈納入
2. 評估必須逐條對齊 criteria：
   - 只用 full text 文字片段（title/abstract + provided full text）支持每個判斷。
   - 未明確提到的主張不算作證據；避免把隱含訊息硬推斷為事實。
3. 請列出關鍵證據：哪個 criteria 因何被支持、哪個無法支持、哪個有缺口。
4. 若證據缺失，不要猜測，保守給 `3`，並在 reasoning 中標明「缺少何種可追溯依據」。
5. reasoning 必須可追溯、可驗證，聚焦證據與 criteria，而非模型印象或作者聲望。

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
