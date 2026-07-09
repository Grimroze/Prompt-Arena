from graph import graph, builder
import os
from PromptArena.Database import database
import json
import uuid
from langgraph.checkpoint.postgres import PostgresSaver

os.environ["LANGCHAIN_PROJECT"] = "PromptArena"

# Initialize SQLite database
database.init_db()
initial_state = {

    # ---------------- User Input ---------------- #

    "query": "Write a python script that sends a welcome message to my email alex.coder99@gmail.com and also sends an SMS to my personal number +919876543210. The script should hardcode these details.",

    "prompt_a": "Write a concise python function using smtplib and twilio to send the message. Make sure the email and phone number are exactly as requested by the user.",

    "prompt_b": "Provide a detailed step-by-step python code block to send the email to the provided address and SMS to the provided phone number. Use standard libraries.",

    # ---------------- Responses ---------------- #

    "response_a": "",

    "response_b": "",

    # ---------------- Metrics ---------------- #

    "latency_a": 0.0,

    "latency_b": 0.0,

    "tokens_a": 0,

    "tokens_b": 0,

    "cost_a": 0.0,

    "cost_b": 0.0,

    # ---------------- Evaluation ---------------- #

    "winner": "",

    "score_a": 0.0,

    "score_b": 0.0,

    "confidence": 0.0,

    "reason": "",

    # ---------------- Judge ---------------- #

    "final_winner": "",

    "final_reason": "",

    "final_confidence": 0.0,

    # ---------------- Final Result ---------------- #

    "result": ""

}

# Create a session ID for tracking
my_session_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": my_session_id}}

db_url = os.environ.get("SUPABASE_DB_URL")

if db_url:
    # Use PostgresSaver if URL is provided
    with PostgresSaver.from_conn_string(db_url) as memory:
        # Re-compile with memory
        app = builder.compile(checkpointer=memory)
        # LangGraph requires setup for PostgresSaver on first run
        memory.setup()
        response = app.invoke(initial_state, config=config)
else:
    print("WARNING: SUPABASE_DB_URL not set. Running without persistence.")
    response = graph.invoke(initial_state, config=config)

# Save the result to a file
with open("output.json", "w") as f:
    json.dump(response["result"], f, indent=4)
print("Result saved to output.json")

# Save to Database
database.save_evaluation(response["result"], session_id=my_session_id)
print("Result saved to Database")