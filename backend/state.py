from typing import TypedDict


class GraphState(TypedDict):
    # ---------------- User Input ---------------- #
    query: str
    prompt_a: str
    prompt_b: str

    # ---------------- Guardrails ---------------- #
    is_safe: bool
    pii_mapping: dict
    override_safety: bool

    # ---------------- LLM Responses ---------------- #

    response_a: str
    response_b: str

    # ---------------- Metrics ---------------- #

    latency_a: float
    latency_b: float

    tokens_a: int
    tokens_b: int

    cost_a: float
    cost_b: float  # no cost cuz using ollama for now... poor T_T


    # ---------------- Evaluation ---------------- #

    winner: str
    score_a: float
    score_b: float
    confidence: float
    reason: str

    # judge
    final_winner: str
    final_reason: str
    final_confidence: float
    iterations: int
    judge_feedback: str

    # -------results------------
    result: dict