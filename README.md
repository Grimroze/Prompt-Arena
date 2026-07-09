# ⚔️ Prompt Arena: The Art of Prompt Engineering

Welcome to **Prompt Arena**, a cutting-edge Agentic AI application designed to evaluate the power of **Prompt Engineering**. The core intention of this project is **not** just to pit AI models against each other, but to demonstrate how **different prompts drastically affect the output of the same user query**.

By comparing how an LLM reacts to Prompt A vs Prompt B for the exact same question, developers can master the art of prompt design, discover best practices, and observe the nuanced behaviors of Large Language Models.

---

## ⭐ Key Features

- **Prompt Battle Arena:** Input a single query, write two distinct instructions (prompts), and observe how the AI's response changes.
- **Agentic Workflows:** The answering models are equipped with DuckDuckGo search tools to browse the internet for up-to-date facts (e.g., 2026 current events).
- **Autonomous Evaluation:** A powerful `Llama-3.3-70b` evaluator scores the responses based on the prompt adherence.
- **Supreme Judge:** A `GPT-OSS-20b` judge steps in to resolve ambiguous evaluations (confidence < 80%).
- **Guardrails:** Built-in Profanity Checker and PII (Personally Identifiable Information) Masker.
- **Human-in-the-loop (HITL):** Allows human override for toxic queries.
- **PostgreSQL Database:** Persists evaluations for the global leaderboard dashboard.
- **LangSmith Tracing:** Full end-to-end observability of LLM chains and tool calls.

---

## 🏛️ Architecture Flow

```mermaid
graph TD
    %% User Input
    U[User Query + Prompt A/B] --> F(Streamlit Frontend)
    
    %% Guardrails
    F -->|Submission| G1{Profanity Check}
    G1 -- Fail --> Human[Human-in-the-Loop Override]
    Human -- Reject --> F
    G1 -- Pass --> G2{PII Masking}
    Human -- Approve --> G2
    
    %% Agent generation
    G2 --> A[Model A Agent<br>Llama-3.1-8b]
    G2 --> B[Model B Agent<br>Qwen3-32b]
    
    %% Tools
    A <--> DDG[(DuckDuckGo Search)]
    B <--> DDG
    
    %% Evaluation Phase
    A --> Eval[Evaluator LLM<br>Llama-3.3-70b]
    B --> Eval
    
    %% Judge Phase
    Eval --> J{Confidence > 80%?}
    J -- No --> Judge[Judge LLM<br>GPT-OSS-20b]
    Judge --> J_Check{Resolved?}
    J_Check -- No --> Eval
    
    J -- Yes --> Save[(PostgreSQL DB)]
    J_Check -- Yes --> Save
    
    %% Output
    Save --> Out[Dashboard & Arena UI]
    Out --> F
```

---

##  The Evolution of Prompt Arena

Building a robust evaluation system took multiple iterations. Here is how the project evolved from a simple script to a production-ready LangGraph architecture.

### Version 1: The Basic Setup
- **Architecture:** A simple linear chain (User -> LLM -> Evaluator).
- **Flaws:** It lacked real-time knowledge. Both the answering models and the evaluator relied purely on their training data, making them fail on recent queries (e.g., 2025/2026 events).
- **Visual:**
  
  ![Workflow V1](ReadMe/workflow_v1.png)

### Version 2: The Agentic Mess
- **Architecture:** Upgraded models to "Agents" using `langchain.agents` and provided them with DuckDuckGo tools.
- **Flaws:** While the models could search the web, the Evaluator model was also converted into an Agent. Because of strict instruction-tuning, the open-source Llama-3 models began **hallucinating tools** (e.g., trying to call `<function=evaluate_responses>`). This caused severe API crashes and invalid JSON outputs.
- **Visual:**
  
  ![Workflow V2](ReadMe/workflow_v2.png)

### Version 3: The Robust LangGraph (Current)
- **Architecture:** Migrated to **LangGraph**. Separated concerns entirely.
  - Model A & B were given tools but constrained with a strict anti-hallucination system prompt.
  - The Evaluator was reverted to a **Pure LLM** (no tools) with a custom JSON parser, completely eliminating tool-call bugs.
  - Added a **Supreme Judge** for tie-breakers and edge cases.
  - Added Guardrails and Human-In-The-Loop.
- **Visual:**
  
  ![Workflow V3](ReadMe/workflow_v3.png)

---

## ⚖️ Tradeoffs

- **Speed vs. Quality:** Introducing a "Supreme Judge" for low-confidence scores increases the overall latency of the pipeline, but ensures highly accurate prompt evaluations.
- **Agentic Answering vs. Evaluator Stability:** We had to remove internet tools from the Evaluator LLM to prevent tool hallucination bugs on the Groq API. The tradeoff is that the Evaluator cannot fact-check against the live web, but it guarantees 100% stable JSON parsing.

---

## 📈 Future Improvements

1. **User Authentication:** Add login/signup functionality so users can have private dashboards instead of a global arena.
2. **Dynamic Model Selection:** Allow users to select which LLMs they want to test their prompts against via the UI.
3. **Prompt Optimization:** Implement an AI feature that takes the losing prompt and automatically rewrites it to be better.
4. **Custom Datasets:** Allow users to upload CSVs and test their prompts against 100+ queries in bulk.

---

## 🗄️ Database Schema

The application relies on Supabase (PostgreSQL) to persist evaluations and power the global leaderboard. The schema is designed to efficiently store user sessions, AI responses, and judge evaluations.

### Schema Overview
Below is the visual representation of our Supabase Database Schema:

![Supabase Schema PNG](ReadMe/supabase-schema.png.png)

*(A scalable vector version is also available at `ReadMe/supabase-schema.svg`)*

The database primarily tracks:
- **Prompts & Models:** Which prompts were used and by which models.
- **Evaluations:** Scores, winners, and AI reasoning.
- **Human-in-the-loop (HITL):** Thread state for resuming paused toxic queries using LangGraph Checkpointers.

---

## 💻 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd PromptArena
   ```

2. **Create a virtual environment & install dependencies:**
   ```bash
   python -m venv myenv
   source myenv/bin/activate  # On Windows use `myenv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key
   LANGCHAIN_PROJECT=PromptArena
   DB_URL=postgresql://user:password@host:port/dbname
   ```

4. **Run the Application:**
   ```bash
   streamlit run frontend/app.py
   ```

<br>
<div align="center">
Made with ❤️‍🩹 & ☕ by grimroze
</div>
