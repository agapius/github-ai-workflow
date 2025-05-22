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

#! /usr/bin/env python3
import subprocess
import os
import argparse
from openai import OpenAI
from dotenv import load_dotenv

# --- Constants ---

KRAKEN_CODE_CONVENTIONS = (
    "=== CODE CONVENTIONS ===\n"
    "\n"
    "## Typing\n"
    "\n"
    "Use static typing.\n"
    "\n"
    "Make function signatures explicit.\n"
    "- Avoid *args and **kwargs unless necessary.\n"
    "- Prefer: def func(foo: int, bar: str) -> ReturnType\n"
    "\n"
    "Avoid generic **kwargs in most functions.\n"
    "- Bad: def create(**kwargs): ...\n"
    "- Good: def create(name: str, age: int): ...\n"
    "\n"
    "Refactor highly parameterized functions.\n"
    "- Use a parameter object to group related arguments.\n"
    "\n"
    "---\n"
    "\n"
    "## Imports\n"
    "\n"
    "Use absolute imports for public modules.\n"
    "\n"
    "Use relative imports for private modules (modules with a leading underscore).\n"
    "\n"
    "In tests, absolute imports of private modules are allowed.\n"
    "\n"
    "Import modules, not objects.\n"
    "- Prefer: from django import http\n"
    "- Avoid: from django.http import HttpResponse\n"
    "\n"
    "Direct object imports are allowed for standard/common built-ins.\n"
    "- Examples: from decimal import Decimal, from typing import Optional\n"
    "\n"
    "Avoid wildcard imports (from module import *).\n"
    "\n"
    "Do not expose modules as public objects in __init__.py.\n"
    "\n"
    "---\n"
    "\n"
    "## Naming\n"
    "\n"
    "Use singular nouns for class names.\n"
    "- Bad: class UserProfiles\n"
    "- Good: class UserProfile\n"
    "\n"
    "Name private things with a leading underscore.\n"
    "- Applies to classes, methods, functions, modules, and variables.\n"
    "\n"
    "Use a trailing underscore to avoid name collisions with built-ins.\n"
    "- Example: property_ = ...\n"
    "\n"
    "Avoid suffixing kwargs with underscore. Instead, rename meaningfully.\n"
    "- Prefer: def to_string(input_date: date | None)\n"
    "- Avoid: def to_string(date_: date | None)\n"
    "\n"
    "---\n"
    "\n"
    "## Convenience Imports\n"
    "\n"
    "Use __init__.py to expose public objects only.\n"
    "\n"
    "Use underscores for private module names to enforce import consistency.\n"
    "- mypackage/__init__.py\n"
    "- mypackage/_foo.py\n"
    "\n"
    "Avoid convenience imports in packages with public children.\n"
    "- Prevents unnecessary bootstrapping and circular dependencies.\n"
    "\n"
    "---\n"
    "\n"
    "## Exceptions\n"
    "\n"
    "Raise distinct exception types for different failure modes.\n"
    "- Avoid reusing a single error class for multiple conditions.\n"
    "\n"
    "Do not include end-user messages in exception messages.\n"
    "- User-facing messages belong in the caller.\n"
    "\n"
    "Include relevant details as attributes on exception classes.\n"
    "\n"
    "Catch specific exception types. Avoid bare except.\n"
    "\n"
    "Only catch Exception if:\n"
    "- You are re-raising after logging.\n"
    "- You want to present a user-friendly error in views.\n"
    "\n"
    "Avoid catching BaseException.\n"
    "\n"
    "Prefer raising exceptions over assert for runtime checks.\n"
    "\n"
    "Assertions are for:\n"
    "- Type narrowing\n"
    "- Development-time debugging\n"
    "- Validating internal invariants\n"
    "\n"
    "Do not validate external input with assert. Use serializers.\n"
    "\n"
    "---\n"
    "\n"
    "## Return Behavior\n"
    "\n"
    "Avoid silent returns on precondition failures.\n"
    "- Bad: if not_ready(): return\n"
    "- Good: if not_ready(): raise NotReady()\n"
    "\n"
    "Use wrapper functions to explicitly handle \"fire-and-forget\" flows.\n"
    "- Swallow only specific exceptions in those wrappers.\n"
    "\n"
    "---\n"
    "\n"
    "## Linting and Static Analysis\n"
    "\n"
    "Never silence all errors with blanket ignores.\n"
    "\n"
    "Always specify the rule or error being silenced.\n"
    "- Good: # noqa: F401\n"
    "- Good: # type: ignore[attr-defined]\n"
    "\n"
    "Justify all silencing comments.\n"
    "- Include rationale or link to relevant bug report.\n"
    "\n"
    "---\n"
    "\n"
    "## Docstrings\n"
    "\n"
    "Start with an imperative description.\n"
    "- Format: \"This function will ...\"\n"
    "\n"
    "Use newline after opening and before closing triple quotes.\n"
    "- End first sentence with a period.\n"
    "\n"
    "Use type annotations for parameters and return types.\n"
    "\n"
    "Document raised exceptions using `:raises ExceptionType:` format.\n"
    "\n"
    "Use comments (# ...) for implementation detail explanations.\n"
    "Use docstrings (\"\"\" ... \"\"\") for user-facing documentation.\n"
    "\n"
    "---\n"
    "\n"
    "## Spelling\n"
    "\n"
    "Prefer American English.\n"
    "- Example: use \"serializers\" not \"serialisers\"\n"
    "\n"
    "---\n"
    "\n"
    "## HTTP Requests\n"
    "\n"
    "Use `requests` library with explicit timeouts.\n"
    "- Example: requests.get(\"url\", timeout=10)\n"
    "\n"
    "Consider using HTTPClient or JSONClient wrappers.\n"
    "\n"
    "Do not make network requests without a timeout.\n"
    "\n"
    "---\n"
    "\n"
    "## Immutability\n"
    "\n"
    "Use immutable types when possible.\n"
    "- Use @attrs.frozen instead of @attrs.define\n"
    "- Use frozenset instead of set\n"
    "- Use tuple or Sequence instead of list\n"
    "\n"
    "Avoid mixing immutable containers with mutable internals.\n"
    "\n"
    "---\n"
    "\n"
    "## attrs vs dataclasses\n"
    "\n"
    "Prefer attrs over dataclasses.\n"
    "- attrs has more features\n"
    "- Calls super() in __init__\n"
    "- Uses less memory (slots)\n"
    "- Faster iteration (not tied to Python release schedule)\n"
    "\n"
    "Use new attrs API (`attrs.define`, `attrs.frozen`)\n"
    "- Avoid old `import attr` and `@attr.s` syntax\n"
    "\n"
    "---\n"
    "\n"
    "## Import-Time Side Effects\n"
    "\n"
    "Do not have import-time side effects.\n"
    "- No registry population\n"
    "- No logging\n"
    "- No URL lookups\n"
    "\n"
    "Register dynamic contents in application startup hooks (e.g. Django’s ready method).\n"
    "\n"
    "Use reverse_lazy instead of reverse for constants or default args.\n"
    "\n"
    "Side effects must be intentional and explicit.\n"
    "\n"
    "=== END COMPANY CODE CONVENTIONS ==="
)

LLM_INSTRUCTION = (
    "You are an AI code reviewer focused *only* on compliance.\n"
    "Your task is to check if the code changes in the **GIT DIFF** below strictly adhere to the rules in the **COMPANY CODE CONVENTIONS** provided.\n"
    "\n"
    "**Instructions:**\n"
    "1. Analyze ONLY the changes in the **GIT DIFF**.\n"
    "2. Refer ONLY to the **COMPANY CODE CONVENTIONS** provided above the diff.\n"
    "3. IGNORE all other aspects (general bugs, logic, performance, security, style) unless they DIRECTLY VIOLATE a stated convention.\n"
    "4. For EACH convention violation found:\n"
    "   - Report the file and line: `path/to/file.py:LINE_NUMBER` (use the line number from the diff hunk (i.e., the added/changed line number)).\n"
    "   - State the specific convention violated (e.g., \"Naming Conventions: Use singular nouns for classes\").\n"
    "   - Provide a concise suggestion to fix the violation.\n"
    "5. If NO violations of the specified conventions are found, respond ONLY with: `No convention violations found.`\n"
    "6. Be concise. Do not add explanations beyond the requested format.\n"
    "\n"
    "**IMPORTANT CLARIFICATIONS:**\n"
    "- Enforce ALL rules *literally*. Even trivial functions must follow conventions (e.g., typing, naming).\n"
    "- ONLY inspect and review the lines added or changed in the GIT DIFF.\n"
    "- Do NOT report issues in lines that were present before and are unchanged, even if they violate conventions.\n"
)

# --- Functions ---

def get_git_diff_against_head() -> str:
    """
    Get the git diff for all uncommitted changes against HEAD.
    Includes a workaround for git diff potentially returning exit code 0 even with output.
    This version is cleaned of debug print statements for production use.
    """
    try:
        command = ["git", "diff", "--no-ext-diff", "HEAD"]

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False  # Manually check return codes
        )

        # Workaround logic:
        # First, check for genuine Git command execution errors (typically exit code > 1)
        if process.returncode > 1:
            cmd_str = ' '.join(command) # For error message
            error_message = f"Error running '{cmd_str}' (return code {process.returncode}):"
            if process.stderr:
                error_message += f"\nGit stderr: {process.stderr.strip()}"
            print(error_message) # Keep this error reporting
            raise RuntimeError(f"Git command '{cmd_str}' failed with code {process.returncode}")

        # If exit code is 0 or 1, rely on stdout content.
        # If stdout has content, we consider it a diff.
        # If stdout is empty (or only whitespace), then no diff.
        if process.stdout and process.stdout.strip():
            return process.stdout
        else:
            return ""

    except FileNotFoundError:
        print("Error: 'git' command not found. Ensure git is installed and in your PATH.") # Keep this error reporting
        raise

def create_llm_prompt(diff_content: str) -> str:
    """Creates the LLM prompt including conventions, instructions, and the diff."""
    return (
        f"{KRAKEN_CODE_CONVENTIONS}\n\n"
        f"{LLM_INSTRUCTION}\n\n"
        f"**GIT DIFF:**\n{diff_content}"
    )

def analyze_with_llm(api_key: str, model_name: str, prompt: str):
    """Sends the prompt to the OpenAI LLM and returns the analysis."""
    client = OpenAI(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{
                "role": "user",
                "content": prompt
            }]
            # Consider adding max_tokens if responses are too long or short.
            # max_tokens=4000
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise

# --- Main Execution ---

if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Analyze staged git diffs for code convention compliance using an OpenAI LLM."
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENAI_API_KEY"),
        help="OpenAI API key. Defaults to OPENAI_API_KEY environment variable."
    )
    parser.add_argument(
        "--model",
        default="gpt-4-turbo", # Or another model like gpt-4-turbo
        help="OpenAI model name to use."
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: OpenAI API key not provided. Set OPENAI_API_KEY env var or use --api-key.")
        exit(1)

    print("Fetching uncommitted changes against HEAD...")
    try:
        diff_text = get_git_diff_against_head()
        print(f"Diff against head for {args.model}:\n{diff_text}")
    except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError):
        print("Failed to get git diff. Exiting.")
        exit(1)

    if not diff_text.strip():
        print("No changes detected to analyze.")
        exit(0)

    print("Creating prompt for LLM...")
    prompt_payload = create_llm_prompt(diff_text)

    print(f"Sending request to OpenAI model: {args.model}...")
    try:
        analysis_result = analyze_with_llm(args.api_key, args.model, prompt_payload)
        print("\n=== AI Code Convention Analysis ===")
        print(analysis_result)
    except Exception:
        print("Failed to get analysis from LLM. Exiting.")
        exit(1)