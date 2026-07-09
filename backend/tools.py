from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
import io, contextlib, re

@tool
def web_search_tool(query: str) -> str:
    """Use this tool to search the internet for facts to verify user claims."""
    search = DuckDuckGoSearchRun()
    try:
        # Pura query internet pe search karega
        result = search.invoke(query)
        return result
    except Exception as e:
        return f"Search failed: {str(e)}"

@tool
def execute_python_tool(text: str) -> str:
    """Use this tool to extract and execute Python code to check for syntax errors or bugs."""
    code_blocks = re.findall(r"```(?:python)?\n(.*?)\n```", text, re.DOTALL)

    if not code_blocks:
        return "No Python code found in response."

    code_to_run = code_blocks[0]  # Sirf pehla code block uthayenge

    output = io.StringIO()
    try:
        # Code ko run karna aur jo bhi print hoga usko 'output' mein save karna
        with contextlib.redirect_stdout(output):
            exec(code_to_run, {})
        return f"Execution Success! Output:\n{output.getvalue()}"
    except Exception as e:
        # Agar code crash hua, toh exact error message return karna
        return f"Execution Error/Crash: {str(e)}"

@tool
def count_words_tool(text: str) -> dict:
    """Use this tool to count words and characters if the prompt has length constraints."""

    words = len(text.split())
    chars = len(text)
    return {
        "words": words,
        "characters": chars
    }

# Tools ki list -> used in binding these with the llm
evaluator_tools = [web_search_tool, execute_python_tool, count_words_tool]