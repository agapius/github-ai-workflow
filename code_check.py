#! /usr/bin/env python3
import subprocess
import os
from typing import Dict, List
from openai import OpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion
from dataclasses import dataclass
import argparse
from dotenv import load_dotenv
from model_pricing import MODEL_PRICING

load_dotenv()

@dataclass
class FileContext:
    path: str
    content: str

@dataclass
class DiffAnalysis:
    files_changed: List[str]
    diff_content: str
    file_contexts: Dict[str, FileContext]

def get_git_diff() -> str:
    """Get the git diff for the specified commit range."""
    result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout

def get_changed_files() -> List[str]:
    """Get list of files changed in the specified commit range."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff --name-only: {e}")
        raise # Re-raise the exception after printing
    return result.stdout.splitlines()

def get_file_content(file_path: str, commit: str = "HEAD") -> str:
    """Get content of a file at a specific commit."""
    try:
        # Ensure file paths with spaces are handled correctly (though git usually doesn't need quotes here)
        result = subprocess.run(
            ["git", "show", f"{commit}:{file_path}"],
            capture_output=True,
            text=True,
            check=True,
            errors='ignore' # Ignore decoding errors for binary files, etc.
        )
        return result.stdout
    except subprocess.CalledProcessError:
        # File might not exist at this commit (new file) or might be binary
        print(f"Warning: Could not get content for {file_path} at {commit}. Might be a new or binary file.")
        return ""

def collect_diff_context() -> DiffAnalysis:
    """Collect all context needed for diff analysis."""
    files = get_changed_files()
    diff = get_git_diff()

    file_contexts = {}
    for file_path in files:
        # Check if the file exists locally before trying to get git content
        # This helps avoid errors if a file was deleted in the changes
        if os.path.exists(file_path) or 'deleted file' not in diff: # Basic check
             content = get_file_content(file_path)
             if content: # Only add context if content was retrieved
                file_contexts[file_path] = FileContext(file_path, content)
        else:
             print(f"Skipping content fetch for potentially deleted file: {file_path}")


    return DiffAnalysis(files, diff, file_contexts)

def load_text_from_file(filename: str) -> str:
    """Loads the text from the specified text file."""
    # Try finding the file relative to the script first
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    if not os.path.exists(file_path):
        # If not found next to script, try current working directory as fallback
        print(f"Info: File not found at '{file_path}'. Trying current directory.")
        file_path = os.path.join(os.getcwd(), filename)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        print(f"Successfully loaded text from: {file_path}")
        # Add markers for clarity in the final prompt
        return f"\n\n{file_content}\n\n"
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Error: The file '{filename}' was not found in the script directory ({script_dir}) or the current directory ({os.getcwd()})."
            f"\nPlease create '{filename}' and place the code conventions text inside it."
        )
    except Exception as e:
        # Catch other potential file reading errors (e.g., permissions)
        raise IOError(f"Error reading conventions file '{file_path}': {e}")

def create_llm_prompt(analysis: DiffAnalysis, debug: bool) -> str:
    """Creates a concise LLM prompt focused *only* on convention checking."""

    # Load the structured conventions from the file
    # Error handling for file loading is done within load_conventions_from_file
    # Exception will propagate up if file is not found or unreadable
    prompt_instructions = load_text_from_file("llm_prompt.txt")
    code_conventions_text = load_text_from_file("code_conventions.txt")

    files_content = "\n\n".join(
        # Only include context if content was successfully retrieved
        f"--- {ctx.path} ---\n{ctx.content}"
        for ctx in analysis.file_contexts.values() if ctx.content
    )
    if not files_content:
        files_content = "[No relevant file context could be retrieved from HEAD]"

    # Combine loaded conventions, instructions, diff, and context
    full_prompt = code_conventions_text + "\n\n" + prompt_instructions

    # Handle potentially empty diff content gracefully in the format string
    diff_content_to_format = analysis.diff_content if analysis.diff_content else "[No diff content available]"
    if debug:
        # In debug mode, use a hardcoded prompt for testing
        return load_text_from_file("hardcode_prompt.txt")
    return full_prompt.format(diff=diff_content_to_format, files_content=files_content)

def analyze_diff(
    api_key: str = None,
    model_name: str = "gpt-4o", # Default to gpt-4o, can be changed
    debug: bool = False,
) -> ChatCompletion:
    """Main function to analyze a git diff using an OpenAI LLM."""
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables or provided via --api-key argument")
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        raise ConnectionError(f"Failed to initialize OpenAI client: {e}")


    print("Collecting diff context...")
    analysis = collect_diff_context()
    if not analysis.diff_content:
        return "No changes detected by git diff."

    print("Creating LLM prompt...")
    prompt = create_llm_prompt(analysis, debug)
    print(f"\n\nPROMPT:\n\n{prompt}")

    print(f"Sending request to OpenAI model: {model_name}...")
    try:
        completion = client.chat.completions.create(
            model=model_name,
            max_tokens=4096, # Keep max_tokens, adjust if needed for OpenAI models
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        return completion

    except Exception as e:
        # Catch potential API errors
        return f"Error calling OpenAI API: {e}"

def calculate_cost(usage: CompletionUsage, model_name: str) -> float:
    """Calculates the cost of usage in Dollar based on token counts."""
    pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["gpt-4o"])
    prompt_cost = (usage.prompt_tokens / 1_000_000) * pricing["prompt"]
    completion_cost = (usage.completion_tokens / 1_000_000) * pricing["completion"]
    total_cost = prompt_cost + completion_cost
    # Round the final result to 4 decimal places before returning
    return round(total_cost, 6)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze git diffs using an OpenAI LLM")
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (defaults to OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model name to use (e.g., gpt-4o, gpt-4-turbo, gpt-3.5-turbo)"
    )
    parser.add_argument(
        "--debug",
        help="Use hardcoded prompt for debugging",
    )

    args = parser.parse_args()

    try:
        result = analyze_diff(api_key=args.api_key, model_name=args.model, debug=args.debug)
        analysis = result.choices[0].message.content
        usage = result.usage
        cost_of_usage = calculate_cost(usage, model_name=args.model)
        print("\n=== AI Analysis ===")
        print(analysis)
        print("\n=== Cost of Usage ===")
        print(f"  Prompt Tokens: {usage.prompt_tokens}")
        print(f"  Completion Tokens: {usage.completion_tokens}")
        print(f"  Cost in Dollar: {cost_of_usage}")
    except (ValueError, ConnectionError, subprocess.CalledProcessError) as e:
        print(f"\nAn error occurred: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
