import os
from schemas import EvaluationResult, JudgeResult
from langchain_groq import ChatGroq

# Get API key from env (ensure it's loaded in app.py)
groq_api_key = os.environ.get("GROQ_API_KEY", "")

# Generates Response A
llm_a = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.4,
    api_key=groq_api_key
)

# Generates Response B (Identical model for fair prompt comparison)
llm_b = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    api_key=groq_api_key
)

# Fast evaluator (Using Llama-3.3-70b for high reasoning)
evaluator_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=groq_api_key
)

# Final Judge
judge_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=groq_api_key
)
evaluator = evaluator_llm.with_structured_output(EvaluationResult, method="json_mode")
judge = judge_llm.with_structured_output(JudgeResult, method="json_mode")

