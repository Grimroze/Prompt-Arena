from langchain_core.messages import HumanMessage
from llms import llm_a, llm_b, evaluator_llm, judge_llm
from utils import start_timer, stop_timer, extract_code

from better_profanity import profanity
from langgraph.types import interrupt
import re
import json
from llms import evaluator, judge
from langsmith import traceable
from langgraph.prebuilt import create_react_agent as create_agent
from tools import evaluator_tools
from langchain_core.messages import HumanMessage, SystemMessage
from schemas import EvaluationResult

from schemas import EvaluationResult

from prompts import EVALUATOR_PROMPT, JUDGE_PROMPT

@traceable
def guardrail_profanity(state):
    query = state["query"]
    prompt_a = state["prompt_a"]
    prompt_b = state["prompt_b"]

    # Check for profanity
    is_safe = not (profanity.contains_profanity(query) or 
                   profanity.contains_profanity(prompt_a) or 
                   profanity.contains_profanity(prompt_b))

    if not is_safe:
        # Dynamic Human-in-the-loop pause
        user_action = interrupt("Toxic content detected. Type 'approve' to override.")
        if user_action == "approve":
            is_safe = True

    return {"is_safe": is_safe}

@traceable
def guardrail_pii_mask(state):
    query = state["query"]
    prompt_a = state["prompt_a"]
    prompt_b = state["prompt_b"]

    pii_mapping = {}
    counter = 1

    # Custom Regex Patterns for PII
    patterns = {
        "EMAIL": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
        "PHONE": r'\+?\d[\d -]{8,12}\d'
    }

    def mask_text(text):
        nonlocal counter
        for entity_type, pattern in patterns.items():
            matches = list(re.finditer(pattern, text))
            # Process in reverse to avoid index shifting
            for match in sorted(matches, key=lambda x: x.start(), reverse=True):
                entity_text = match.group()
                placeholder = f"[{entity_type}_{counter}]"
                pii_mapping[placeholder] = entity_text
                text = text[:match.start()] + placeholder + text[match.end():]
                counter += 1
        return text

    masked_query = mask_text(query)
    masked_prompt_a = mask_text(prompt_a)
    masked_prompt_b = mask_text(prompt_b)

    return {
        "query": masked_query,
        "prompt_a": masked_prompt_a,
        "prompt_b": masked_prompt_b,
        "pii_mapping": pii_mapping
    }

@traceable
def generate_response_a(state):

    query = state["query"]
    prompt = state["prompt_a"]

    final_prompt = f"""
        User Question:
        {query}
        
        Instruction:
        {prompt}
        """

    start = start_timer()

    import datetime
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    system_prompt = f"""You are a helpful AI assistant. The current date is {current_date}. 
        You have access to a DuckDuckGo search tool. ALWAYS use it if the user asks for news, current events, or anything beyond your training data.
        CRITICAL RULE: Do NOT hallucinate or call any tools other than the ones explicitly provided to you. If you need to count words, evaluate text, or do something else, just do it yourself. Do NOT call imaginary tools."""

    agent_a = create_agent(llm_a, evaluator_tools, prompt=system_prompt)
    response_obj_a = agent_a.invoke({"messages": [HumanMessage(content=final_prompt)]})

    latency = stop_timer(start)
    
    input_tokens = 0
    output_tokens = 0
    for msg in response_obj_a.get("messages", []):
        if hasattr(msg, "response_metadata") and msg.response_metadata:
            meta = msg.response_metadata
            input_tokens += meta.get("token_usage", {}).get("prompt_tokens", 0)
            output_tokens += meta.get("token_usage", {}).get("completion_tokens", 0)
            
    total_tokens = input_tokens + output_tokens

    raw_response_a = response_obj_a["messages"][-1].content
    clean_response_a = re.sub(r'<think>.*?(?:</think>|$)\n*', '', raw_response_a, flags=re.DOTALL | re.IGNORECASE).strip()
    if not clean_response_a:
        clean_response_a = raw_response_a

    return {
        "response_a": clean_response_a,
        "latency_a": latency,
        "tokens_a": total_tokens,
        "cost_a": 0.0
    }

@traceable
def generate_response_b(state):
    query = state["query"]
    prompt_b = state["prompt_b"]

    final_prompt = f"{prompt_b}\n\nUser Query: {query}"

    start = start_timer()

    import datetime
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    system_prompt = f"""You are a helpful AI assistant. The current date is {current_date}. 
You have access to a DuckDuckGo search tool. ALWAYS use it if the user asks for news, current events, or anything beyond your training data.
CRITICAL RULE: Do NOT hallucinate or call any tools other than the ones explicitly provided to you. If you need to count words, evaluate text, or do something else, just do it yourself. Do NOT call imaginary tools."""

    agent_b = create_agent(llm_b, evaluator_tools, prompt=system_prompt)
    response_obj_b = agent_b.invoke({"messages": [HumanMessage(content=final_prompt)]})

    latency = stop_timer(start)
    
    input_tokens = 0
    output_tokens = 0
    for msg in response_obj_b.get("messages", []):
        if hasattr(msg, "response_metadata") and msg.response_metadata:
            meta = msg.response_metadata
            input_tokens += meta.get("token_usage", {}).get("prompt_tokens", 0)
            output_tokens += meta.get("token_usage", {}).get("completion_tokens", 0)
            
    total_tokens = input_tokens + output_tokens

    raw_response_b = response_obj_b["messages"][-1].content
    clean_response_b = re.sub(r'<think>.*?(?:</think>|$)\n*', '', raw_response_b, flags=re.DOTALL | re.IGNORECASE).strip()
    if not clean_response_b:
        clean_response_b = raw_response_b

    return {
        "response_b": clean_response_b,
        "latency_b": latency,
        "tokens_b": total_tokens,
        "cost_b": 0.0
    }

# Removed agent wrapper to prevent tool hallucination bugs on Groq API

@traceable
def evaluate_responses(state):
    feedback = state.get("judge_feedback", "")
    feedback_text = f"\n\nJudge Feedback:\n{feedback}" if feedback else ""

    # 1. Evaluator LLM ko prompt bhejna (without tools to guarantee stability)
    prompt = EVALUATOR_PROMPT.format(
        query=state["query"],
        response_a=state["response_a"],
        response_b=state["response_b"]
    ) + feedback_text

    llm_response = evaluator_llm.invoke([HumanMessage(content=prompt)])
    final_text = llm_response.content

    # 3. Final text ko JSON (EvaluationResult) mein convert karna
    # Ek naya parser LLM call jo sirf text ko JSON mein dale
    parser_prompt = f"""Extract the evaluation result from this text into a pure JSON object.
Do NOT use tool calls. Do NOT use <function> tags.
Respond ONLY with valid JSON matching this exact structure:
{{
  "winner": "A" or "B" or "Tie",
  "score_a": float (0-10),
  "score_b": float (0-10),
  "confidence": float (0-1),
  "reason": "String reasoning"
}}

Text to parse:
{final_text}
"""
    result = evaluator_llm.invoke([HumanMessage(content=parser_prompt)])
    content = result.content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
        
    try:
        parsed_json = json.loads(content)
    except:
        parsed_json = {"winner": "Tie", "score_a": 0, "score_b": 0, "confidence": 0, "reason": "Failed to parse"}

    return {
        "winner": parsed_json.get("winner", "Tie"),
        "score_a": parsed_json.get("score_a", 0.0),
        "score_b": parsed_json.get("score_b", 0.0),
        "confidence": parsed_json.get("confidence", 0.0),
        "reason": parsed_json.get("reason", "No reason provided")
    }

@traceable
def should_use_judge(state):
    if state.get("iterations", 0) >= 3:
        return "dashboard"
    if state["confidence"] >= 0.80:
        return "dashboard"
    return "judge"

@traceable
def judge_responses(state):
    iterations = state.get("iterations", 0) + 1

    prompt = JUDGE_PROMPT.format(
        query=state["query"],
        response_a=state["response_a"],
        response_b=state["response_b"],
        winner=state["winner"],
        score_a=state["score_a"],
        score_b=state["score_b"],
        confidence=state["confidence"],
        reason=state["reason"]
    )

    judge_prompt = prompt + """\n\nAnalyze the above comparison. Provide your response as a pure JSON object matching this structure:
{{
  "is_resolved": boolean (true if you agree with the evaluator or if you can make a final decision, false if still ambiguous),
  "winner": "A" or "B" or "Tie" (your final decision if resolved, otherwise omit),
  "confidence": float (0-1),
  "reason": "String detailing your final feedback or decision"
}}
Do NOT use tool calls or `<function>` tags. Respond ONLY with valid JSON.
"""

    result = judge_llm.invoke(
        [HumanMessage(content=judge_prompt)]
    )
    
    content = result.content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
        
    try:
        parsed_json = json.loads(content)
    except:
        parsed_json = {"is_resolved": True, "winner": state["winner"], "confidence": state["confidence"], "reason": "Failed to parse Judge JSON"}

    is_resolved = parsed_json.get("is_resolved", False)

    if is_resolved or iterations >= 3:
        winner = parsed_json.get("winner") if parsed_json.get("winner") else state["winner"]
        return {
            "final_winner": winner,
            "final_confidence": parsed_json.get("confidence", state["confidence"]),
            "final_reason": parsed_json.get("reason", ""),
            "iterations": iterations,
            "judge_feedback": ""
        }
    else:
        return {
            "judge_feedback": parsed_json.get("reason", ""),
            "iterations": iterations,
            "final_winner": "" 
        }

@traceable
def prepare_result(state):

    # Check if blocked by guardrails
    if not state.get("is_safe", True):
        return {
            "result": {
                "error": "Query blocked due to inappropriate content.",
                "query": state["query"],
                "prompt_a": state["prompt_a"],
                "prompt_b": state["prompt_b"],
                "evaluated_by": "Guardrail"
            }
        }

    # Judge use hua ya nahi
    if state["final_winner"]:

        winner = state["final_winner"]
        confidence = state["final_confidence"]
        reason = state["final_reason"]

        evaluated_by = "Judge"

    else:

        winner = state["winner"]
        confidence = state["confidence"]
        reason = state["reason"]

        evaluated_by = "Evaluator"

    return {

        "result": {

            "query": state["query"],

            "prompt_a": state["prompt_a"],
            "prompt_b": state["prompt_b"],

            "response_a": state["response_a"],
            "response_b": state["response_b"],

            "code": {
                "A": extract_code(state["response_a"]),
                "B": extract_code(state["response_b"])
            },

            "latency": {
                "A": state["latency_a"],
                "B": state["latency_b"]
            },

            "tokens": {
                "A": state["tokens_a"],
                "B": state["tokens_b"]
            },

            "cost": {
                "A": state["cost_a"],
                "B": state["cost_b"]
            },

            "scores": {
                "A": state["score_a"],
                "B": state["score_b"]
            },

            "winner": winner,
            "confidence": confidence,
            "reason": reason,

            "evaluated_by": evaluated_by

        }

    }

@traceable
def guardrail_pii_unmask(state):
    # Restore PII placeholders from responses
    response_a = state["response_a"]
    response_b = state["response_b"]
    pii_mapping = state.get("pii_mapping", {})

    for placeholder, original_text in pii_mapping.items():
        if response_a:
            response_a = response_a.replace(placeholder, original_text)
        if response_b:
            response_b = response_b.replace(placeholder, original_text)

    return {
        "response_a": response_a,
        "response_b": response_b
    }