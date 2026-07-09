import streamlit as st
import sys
import os
import uuid
import json

# ==========================================
# 1. Path Configuration (Very Important!)
# ==========================================
# Streamlit needs to know where our backend files are located.
# We get the absolute path of the current directory (frontend) 
# and add the parent directory (PromptArena) to the system path.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
backend_dir = os.path.join(parent_dir, "backend")

# Append both parent directory and backend directory to path
sys.path.append(parent_dir)
sys.path.append(backend_dir)

# Now we can import from our backend safely
from backend.graph import builder
from backend.state import GraphState
from Database import database
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from dotenv import load_dotenv

# Load environment variables (like SUPABASE_DB_URL)
load_dotenv()

# ==========================================
# 2. Page Configuration & Custom CSS
# ==========================================
# We set the page title and layout to be wide. 
st.set_page_config(page_title="PromptArena", layout="wide")

# This CSS hides the Streamlit main menu and footer for a cleaner look
# And adds a "made by grimroze" floating tag to the top right
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            .made-by {
                position: absolute;
                top: 10px;
                right: 15px;
                color: #888;
                font-family: monospace;
                font-size: 12px;
                z-index: 1000;
            }
            </style>
            <div class="made-by">made by grimroze</div>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)





# title ----------
st.markdown("""
<h1 style="
    text-align:left;
    font-family: 'Jetbrains Mono', 'Segoe UI', sans-serif;
    font-size:60px;
    font-weight:700;
    color:white;
    margin-bottom:5px;
">
Prompt Arena
</h1>

<p style="
    text-align:left;
    color:#b3b3b3;
    font-size:18px;
    font-style : italic;
    font-family:'Inter', sans-serif;
">
The art of Prompt Engineering
</p>
""", unsafe_allow_html=True)








# ==========================================
# 3. Session State Management
# ==========================================
# We use st.session_state to remember variables even when the page refreshes.
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()) # Generate a unique ID for the user's session

if "graph_app" not in st.session_state:
    # Initialize the database table
    database.init_db()
    
    # Check if we have a Supabase URL for memory persistence
    db_url = os.environ.get("SUPABASE_DB_URL")
    if db_url:
        st.session_state.db_url = db_url
        st.session_state.use_memory = True
    else:
        st.session_state.use_memory = False
        st.error("Database URL not found. Running without memory.")

# ==========================================
# 4. Helper Functions
# ==========================================
def display_model_response(col_title, result_dict, prefix):
    """
    This function displays the response of a model in a column.
    It checks if code was extracted. If yes, it uses st.code(), else st.markdown().
    """
    st.subheader(col_title)
    
    # Extract the response string
    response_text = result_dict.get(f"response_{prefix}", "")
    
    # Strip <think> tags if any slipped through
    import re
    response_text = re.sub(r'<think>.*?(?:</think>|$)\n*', '', response_text, flags=re.DOTALL | re.IGNORECASE).strip()

    # Check if there is extracted code
    code_dict = result_dict.get("code", {})
    extracted_code = code_dict.get(prefix.upper())
    
    if extracted_code:
        # If code exists, display the normal text first, then the code block
        text_without_code = response_text.replace(f"```python\n{extracted_code}\n```", "").strip()
        if text_without_code:
            st.markdown(text_without_code)
        st.code(extracted_code, language="python")
    else:
        # If no code, just display normal text
        st.markdown(response_text)
        
    # Display Metrics (Latency, Tokens, Cost)
    latency = result_dict.get("latency", {}).get(prefix.upper(), 0.0)
    tokens = result_dict.get("tokens", {}).get(prefix.upper(), 0)
    cost = result_dict.get("cost", {}).get(prefix.upper(), 0.0)
    st.caption(f"Latency: {latency:.2f}s | Tokens: {tokens} | Cost: ${cost:.5f}")

def generate_markdown_summary(query, prompt_a, prompt_b, winner, reason, response_a, response_b):
    import re
    reason = re.sub(r'<think>.*?(?:</think>|$)\n*', '', reason, flags=re.DOTALL | re.IGNORECASE).strip()
    
    return f"""# Prompt Arena - Comparison Summary

## User Query
{query}

---

## Winner: Model {winner}
**Reasoning:** 
{reason}

---

## Model A
**Prompt Used:**
{prompt_a}

**Response:**
{response_a}

---

## Model B
**Prompt Used:**
{prompt_b}

**Response:**
{response_b}
"""

# ==========================================
# 5. Main UI Layout
# ==========================================
# Sidebar UI
with st.sidebar:
    st.title("Prompt Arena")
    st.write("Compare AI models autonomously.")

    # Button to start a fresh comparison
    if st.button("New Comparison", type="primary"):
        st.session_state.session_id = str(uuid.uuid4()) # Generate new ID
        st.rerun() # Refresh the page

    st.caption(f"Session ID: {st.session_state.session_id[:8]}")


st.markdown("")

# Create Tabs for Arena and Dashboard
tab_arena, tab_dashboard = st.tabs(["Arena", "Dashboard"])

with tab_arena:
    # Input Form
    with st.form("evaluation_form"):
        query_input = st.text_area("User Query", placeholder="Enter the main problem or question here...", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            prompt_a_input = st.text_area("Prompt A", placeholder="Enter Prompt A (e.g., Be concise...)", height=150)
        with col2:
            prompt_b_input = st.text_area("Prompt B", placeholder="Enter Prompt B (e.g., Explain step-by-step...)", height=150)
            
        submitted = st.form_submit_button("Run Comparison")

# ==========================================
# 6. Graph Execution Logic
# ==========================================
    if submitted and query_input and prompt_a_input and prompt_b_input:
        # Prepare the initial state
        initial_state = {
            "query": query_input,
            "prompt_a": prompt_a_input,
            "prompt_b": prompt_b_input,
            "response_a": "",
            "response_b": "",
            "latency_a": 0.0, "latency_b": 0.0,
            "tokens_a": 0, "tokens_b": 0,
            "cost_a": 0.0, "cost_b": 0.0,
            "winner": "", "score_a": 0.0, "score_b": 0.0,
            "confidence": 0.0, "reason": "",
            "final_winner": "", "final_reason": "", "final_confidence": 0.0,
            "result": ""
        }
        
        config = {"configurable": {"thread_id": st.session_state.session_id}}
        
        # Run the graph
        with st.spinner("Analyzing and evaluating models..."):
            memory_successfully_used = False
            
            if st.session_state.use_memory:
                try:
                    # We connect to Supabase for the checkpointer
                    with PostgresSaver.from_conn_string(st.session_state.db_url) as memory:
                        memory.setup()
                        app_compiled = builder.compile(checkpointer=memory)
                        
                        # Execute the graph
                        response = app_compiled.invoke(initial_state, config=config)
                        
                        # Check if graph paused due to HITL (Human-In-The-Loop)
                        state_snapshot = app_compiled.get_state(config)
                        if state_snapshot.next:
                            st.session_state.paused = True
                        else:
                            st.session_state.paused = False
                            st.session_state.final_result = response.get("result")
                            
                        memory_successfully_used = True
                except Exception as e:
                    # Don't swallow real graph errors (like LLM or logic errors)
                    if "unexpected" in str(e).lower() or "groq" in str(e).lower() or "not defined" in str(e).lower() or "tool" in str(e).lower():
                        raise e
                    st.warning(f"Database Error: {e}. Falling back to run without memory.")
            
            if not memory_successfully_used:
                app_compiled = builder.compile()
                response = app_compiled.invoke(initial_state, config=config)
                st.session_state.paused = False
                st.session_state.final_result = response.get("result")

# ==========================================
# 7. Handling HITL (Human-in-the-Loop)
# ==========================================
    if st.session_state.get("paused", False):
        st.error("Toxic Content Detected! The guardrail has paused the execution.")
        st.warning("Do you want to override the safety protocol and proceed anyway?")
        
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button("Approve (Override)", type="primary"):
                # Resume the graph with 'approve' command
                with st.spinner("Resuming execution..."):
                    with PostgresSaver.from_conn_string(st.session_state.db_url) as memory:
                        app = builder.compile(checkpointer=memory)
                        config = {"configurable": {"thread_id": st.session_state.session_id}}
                        
                        # The Command(resume=...) passes the data back to the interrupt() function
                        response = app.invoke(Command(resume="approve"), config=config)
                        st.session_state.paused = False
                        st.session_state.final_result = response.get("result")
                        st.rerun()
                        
        with col_n:
            if st.button("Reject"):
                # Resume but don't approve
                with st.spinner("Rejecting..."):
                    with PostgresSaver.from_conn_string(st.session_state.db_url) as memory:
                        app = builder.compile(checkpointer=memory)
                        config = {"configurable": {"thread_id": st.session_state.session_id}}
                        response = app.invoke(Command(resume="reject"), config=config)
                        st.session_state.paused = False
                        st.session_state.final_result = response.get("result")
                        st.rerun()

# ==========================================
# 8. Displaying the Final Results
# ==========================================
    if st.session_state.get("final_result"):
        result = st.session_state.final_result
        
        if type(result) == str and "unsafe" in result.lower():
            # Display rejection message
            st.error("Query was rejected due to safety guardrails.")
        elif type(result) == dict and result.get("error"):
            # Display dict rejection message
            st.error(result.get("error"))
        else:
            # Display the successful comparison
            st.divider()
            
            # Determine the ultimate winner (either from Judge or Evaluator)
            ultimate_winner = result.get("final_winner") or result.get("winner")
            st.success(f"Winner: Model {ultimate_winner}")
            
            # Explain the reasoning
            reason = result.get("final_reason") or result.get("reason")
            st.markdown("### Reasoning")
            st.markdown(f"> {reason}")
            
            # Metrics Table
            st.markdown("### Performance Metrics")
            import pandas as pd
            metrics_df = pd.DataFrame({
                "Metric": ["Latency (seconds)", "Tokens Used"],
                "Model A": [f"{result.get('latency', {}).get('A', 0.0)}", result.get('tokens', {}).get('A', 0)],
                "Model B": [f"{result.get('latency', {}).get('B', 0.0)}", result.get('tokens', {}).get('B', 0)]
            })
            st.table(metrics_df.set_index("Metric"))
            
            st.divider()
            
            # Display Model A and Model B responses side-by-side
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                display_model_response("Model A Response", result, "a")
            with res_col2:
                display_model_response("Model B Response", result, "b")
                
            st.divider()
            # Export Button
            md_content = generate_markdown_summary(
                query=result.get("query", ""),
                prompt_a=result.get("prompt_a", ""),
                prompt_b=result.get("prompt_b", ""),
                winner=ultimate_winner,
                reason=reason,
                response_a=result.get("response_a", ""),
                response_b=result.get("response_b", "")
            )
            st.download_button(
                label="🔻 Download Comparison Summary",
                data=md_content,
                file_name="comparison_summary.md",
                mime="text/markdown"
            )
                
            # Save to SQLite database after successful completion
            try:
                database.save_evaluation(result, session_id=st.session_state.session_id)
            except Exception as e:
                pass # Ignore if already saved

with tab_dashboard:
    st.subheader("Recent Comparisons")
    
    # Fetch recent evaluations from Supabase
    recent_evals = database.get_recent_evaluations(limit=10)
    
    if recent_evals:
        # Display the data nicely in a dataframe (table)
        event = st.dataframe(
            recent_evals, 
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "id": None, # Hide internal DB ID
                "session_id": None,
                "response_a": None,
                "response_b": None,
                "code_a": None,
                "code_b": None,
                "score_a": None,
                "score_b": None,
                "latency_a": None,
                "latency_b": None,
                "tokens_a": None,
                "tokens_b": None,
                "cost_a": None,
                "cost_b": None,
                "reason": None,
                "query": "User Query",
                "prompt_a": "Prompt A",
                "prompt_b": "Prompt B",
                "winner": "Winner",
                "confidence": "Confidence Score",
                "evaluated_by": None, # Hiding as requested
                "timestamp": None   # Hiding as requested
            }
        )
        
        # Check if a row was clicked
        if len(event.selection.rows) > 0:
            selected_idx = event.selection.rows[0]
            selected_eval = recent_evals[selected_idx]
            
            st.divider()
            st.subheader("Detailed View")
            st.success(f"Winner: Model {selected_eval.get('winner')}")
            st.markdown("### Reasoning")
            st.markdown(f"> {selected_eval.get('reason')}")
            
            # Metrics Table
            st.markdown("### Performance Metrics")
            import pandas as pd
            metrics_df = pd.DataFrame({
                "Metric": ["Latency (seconds)", "Tokens Used"],
                "Model A": [f"{selected_eval.get('latency_a', 0.0)}", selected_eval.get('tokens_a', 0)],
                "Model B": [f"{selected_eval.get('latency_b', 0.0)}", selected_eval.get('tokens_b', 0)]
            })
            st.table(metrics_df.set_index("Metric"))
            
            st.divider()
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Model A Response**")
                st.markdown(selected_eval.get('response_a', ''))
            with col_b:
                st.markdown("**Model B Response**")
                st.markdown(selected_eval.get('response_b', ''))
                
            st.divider()
            # Export Button
            md_content_dash = generate_markdown_summary(
                query=selected_eval.get("query", ""),
                prompt_a=selected_eval.get("prompt_a", ""),
                prompt_b=selected_eval.get("prompt_b", ""),
                winner=selected_eval.get("winner", ""),
                reason=selected_eval.get("reason", ""),
                response_a=selected_eval.get("response_a", ""),
                response_b=selected_eval.get("response_b", "")
            )
            st.download_button(
                label="🔻 Download Summary",
                data=md_content_dash,
                file_name=f"comparison_{selected_idx}.md",
                mime="text/markdown"
            )
            
    else:
        st.info("No recent comparisons found in the database. Run a comparison in the Arena tab first!")