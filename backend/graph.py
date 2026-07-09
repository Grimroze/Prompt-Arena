from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
import os
from dotenv import load_dotenv

load_dotenv()
from state import GraphState
from nodes import (
    generate_response_a,
    generate_response_b,
    evaluate_responses,
    judge_responses,
    should_use_judge,
    prepare_result,
    guardrail_profanity,
    guardrail_pii_mask,
    guardrail_pii_unmask
)

builder = StateGraph(GraphState)

# adding the nodes
builder.add_node("guardrail_profanity", guardrail_profanity)
builder.add_node("guardrail_pii_mask", guardrail_pii_mask)
builder.add_node("generate_response_a", generate_response_a)
builder.add_node("generate_response_b", generate_response_b)
builder.add_node("evaluate_responses", evaluate_responses)
builder.add_node("judge_responses", judge_responses)
builder.add_node("guardrail_pii_unmask", guardrail_pii_unmask)
builder.add_node("prepare_result", prepare_result)

# START -> guardrail_profanity
builder.add_edge(START, "guardrail_profanity")

def check_safety(state):
    if state.get("is_safe", True):
        return "safe"
    return "unsafe"

builder.add_conditional_edges(
    "guardrail_profanity",
    check_safety,
    {
        "safe": "guardrail_pii_mask",
        "unsafe": "prepare_result"
    }
)

# guardrail_pii_mask -> LLMs
builder.add_edge("guardrail_pii_mask", "generate_response_a")
builder.add_edge("guardrail_pii_mask", "generate_response_b")

# LLMs -> Evaluator
builder.add_edge("generate_response_a", "evaluate_responses")
builder.add_edge("generate_response_b", "evaluate_responses")

# Evaluator -> Judge OR Unmask PII
builder.add_conditional_edges(
    "evaluate_responses",
    should_use_judge,
    {
        "judge": "judge_responses",
        "dashboard": "guardrail_pii_unmask"
    }
)

def route_after_judge(state):
    if state.get("final_winner"):
        return "guardrail_pii_unmask"
    return "evaluate_responses"

builder.add_conditional_edges(
    "judge_responses",
    route_after_judge,
    {
        "guardrail_pii_unmask": "guardrail_pii_unmask",
        "evaluate_responses": "evaluate_responses"
    }
)

# Unmask PII -> Prepare Result -> END
builder.add_edge("guardrail_pii_unmask", "prepare_result")
builder.add_edge("prepare_result", END)

db_url = os.environ.get("SUPABASE_DB_URL")

if db_url:
    graph = builder.compile() # Will be re-compiled in test.py with checkpointer
else:
    graph = builder.compile()

