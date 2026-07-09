import time
import re
def start_timer():
    return time.perf_counter()

def stop_timer(start_time):
    return round(time.perf_counter() - start_time, 3)

def extract_code(text: str) -> str:
    """LLM ke response text mein se code blocks nikalne hai."""
    # Regex to find anything inside triple backticks
    code_blocks = re.findall(r"```(?:\w+)?\n(.*?)\n```", text, re.DOTALL)

    # Agar code mila toh usko join karke return karo, warna empty string
    if code_blocks:
        return "\n\n".join(code_blocks)
    return ""