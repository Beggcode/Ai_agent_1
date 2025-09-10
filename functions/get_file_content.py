# functions/get_file_content.py
from google.genai import types
import os
from functions.config import MAX_CHARS

# --- SCHEMA (what the LLM can call) ---
schema_get_file_content = types.FunctionDeclaration(
    name="get_file_content",
    description="Read the full text content of a file (relative to the working directory).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="Relative path to the file to read (e.g., 'main.py').",
            ),
        },
        required=["file_path"],
    ),
)


def get_file_content(working_directory, file_path):
    try:
        working_directory_abs = os.path.abspath(working_directory)
        target_path = os.path.abspath(os.path.join(working_directory_abs, file_path))

        if not target_path.startswith(working_directory_abs):
            return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(target_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'

        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if len(content) > MAX_CHARS:
            truncated_msg = f'\n[...File "{file_path}" truncated at {MAX_CHARS} characters]'
            return content[:MAX_CHARS] + truncated_msg

        return content
    except Exception as e:
        return f"Error: {e}"
