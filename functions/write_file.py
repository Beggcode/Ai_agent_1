# functions/write_file.py
from google.genai import types

# --- SCHEMA: what the LLM can choose ---
schema_write_file = types.FunctionDeclaration(
    name="write_file",
    description="Write or overwrite a text file with the provided content (relative path).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="Relative path to the file to write (e.g., 'notes.txt').",
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="Full text content to write to the file.",
            ),
        },
        required=["file_path", "content"],
    ),
)

# --- RUNTIME: if you haven't already, add this (or keep your existing version) ---
import os

def write_file(working_directory, file_path, content):
    try:
        wd_abs = os.path.abspath(working_directory)
        target = os.path.abspath(os.path.join(wd_abs, file_path))

        if not target.startswith(wd_abs):
            return f'Error: Cannot write "{file_path}" as it is outside the permitted working directory'

        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)

        with open(target, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)

        return f'Wrote {len(content)} chars to "{file_path}"'
    except Exception as e:
        return f"Error: {e}"
