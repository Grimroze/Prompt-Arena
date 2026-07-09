from pydantic import BaseModel, Field

class EvaluationResult(BaseModel):

    winner: str = Field(
        description="Winner should be either A or B."
    )
    score_a: float = Field(
        ge=0,
        le=10
    )
    score_b: float = Field(
        ge=0,
        le=10
    )
    confidence: float = Field(
        ge=0,
        le=1
    )
    reason: str


from typing import Optional

class JudgeResult(BaseModel):

    is_resolved: bool = Field(
        description="True if you can confidently decide a winner, False if you want to send feedback to the evaluator."
    )
    winner: Optional[str] = Field(
        default=None,
        description="Final winner (A or B). Only provide if is_resolved is True."
    )
    confidence: float = Field(
        ge=0,
        le=1
    )
    reason: str = Field(
        description="Reason for your decision, or feedback for the evaluator if is_resolved is False."
    )