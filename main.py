import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Schemas + runtime functions
from functions.get_files_info import schema_get_files_info, get_files_info
from functions.get_file_content import schema_get_file_content, get_file_content
from functions.run_python_file import schema_run_python_file, run_python_file
from functions.write_file import schema_write_file, write_file

MODEL = "gemini-2.0-flash-001"
WORKING_DIR = "./calculator"
MAX_STEPS = 20

system_prompt = """
You are a helpful AI coding agent working on a small codebase located under ./calculator.

Agent policy:
- Prefer using the available tools to gather evidence before asking the user questions.
- When the user asks about behavior or implementation, proactively inspect the repository.
- Treat ambiguous references like “the calculator” as the code under ./calculator unless proven otherwise.
- Stop and ask for clarification only after you’ve attempted reasonable inspections.

Allowed operations (call exactly one per step as needed):
- List files and directories
- Read file contents
- Execute Python files with optional arguments
- Write or overwrite files

Default investigation plan for code questions:
1) List the repo root: get_files_info({ "directory": "." })
2) If ./pkg exists, list it: get_files_info({ "directory": "pkg" })
3) Read likely files: README.md, main.py, pkg/render.py, pkg/*.py
4) If tests are mentioned, run tests.py.

Safety rules:
- All paths are relative to ./calculator. Do not escape this directory.
- Do not invent filenames, directories, or arguments you don't have.
- If no operation applies, respond briefly in natural language.
"""

def call_function(function_call_part: types.FunctionCall, verbose: bool = False) -> dict:
    """Dispatch tool call to a local function and return {'name':..., 'result':...}."""
    name = function_call_part.name
    kwargs = dict(function_call_part.args or {})
    kwargs["working_directory"] = WORKING_DIR

    if verbose:
        print(f"Calling function: {name}({kwargs})")
    else:
        print(f" - Calling function: {name}")

    dispatch = {
        "get_files_info": get_files_info,
        "get_file_content": get_file_content,
        "run_python_file": run_python_file,
        "write_file": write_file,
    }
    fn = dispatch.get(name)
    if not fn:
        return {"name": name, "result": f"Error: Unknown function: {name}"}

    try:
        res = fn(**kwargs)
    except Exception as e:
        res = f"Error: {e}"

    return {"name": name, "result": res}

def main() -> None:
    # ---- CLI ----
    argv = sys.argv[1:]
    verbose = "--verbose" in argv
    args_without_flags = [a for a in argv if a != "--verbose"]
    if not args_without_flags:
        print("Error: You must provide a prompt as a command line argument")
        sys.exit(1)
    user_prompt = " ".join(args_without_flags)
    if verbose:
        print(f"User prompt: {user_prompt}")

    # ---- Auth ----
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment variables.")
    client = genai.Client(api_key=api_key)

    # ---- Conversation state ----
    messages: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=user_prompt)]),
    ]
    tools = [types.Tool(function_declarations=[
        schema_get_files_info,
        schema_get_file_content,
        schema_run_python_file,
        schema_write_file,
    ])]

    # ---- Agent loop ----
    for step in range(1, MAX_STEPS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=messages,  # always pass full history
                config=types.GenerateContentConfig(
                    tools=tools,
                    system_instruction=system_prompt,
                ),
            )
        except Exception as e:
            print(f"Agent error on step {step}: {e}")
            sys.exit(1)

        # Append the model's message(s) (tool intent / text) to the conversation
        candidates = getattr(response, "candidates", []) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if content:
                messages.append(content)

        # Collect tool calls (unified + fallback)
        tool_calls = []
        fc_direct = getattr(response, "function_calls", None) or []
        tool_calls.extend(fc_direct)
        if not fc_direct:
            for cand in candidates:
                parts = getattr(getattr(cand, "content", None), "parts", []) or []
                for part in parts:
                    fc = getattr(part, "function_call", None)
                    if fc:
                        tool_calls.append(fc)

        if tool_calls:
            # Execute tools and feed results back; then continue the loop
            for fc in tool_calls:
                out = call_function(fc, verbose=verbose)
                tool_msg = types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=out["name"],
                        response={"result": out["result"]},
                    )]
                )
                if verbose:
                    print(f"-> {tool_msg.parts[0].function_response.response}")
                messages.append(tool_msg)

            if verbose:
                usage = getattr(response, "usage_metadata", None)
                print(f"Prompt tokens: {getattr(usage, 'prompt_token_count', 0)}")
                print(f"Response tokens: {getattr(usage, 'candidates_token_count', 0)}")

            continue  # Let the model take the next step

        # No tool calls this turn; if there's final text, kaput
        if getattr(response, "text", None):
            print("Final response:")
            print(response.text)
            if verbose:
                usage = getattr(response, "usage_metadata", None)
                print(f"Prompt tokens: {getattr(usage, 'prompt_token_count', 0)}")
                print(f"Response tokens: {getattr(usage, 'candidates_token_count', 0)}")
            break

        # Neither tools nor text -> bail
        print("Final response:")
        print("I don't know")
        break

    else:
        # loop exhausted
        print("Final response:")
        print("I don't know")

if __name__ == "__main__":
    main()
