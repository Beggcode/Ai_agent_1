# functions/get_files_info.py
from google.genai import types
import os

# --- SCHEMA (what the LLM sees/chooses) ---
schema_get_files_info = types.FunctionDeclaration(
    name="get_files_info",
    description="List files and directories",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "directory": types.Schema(
                type=types.Type.STRING,
                description="Directory path to list (default: '.')",
            ),
        },
        required=[],
    ),
)

def get_files_info(working_directory, directory="."):
    try:
        wd_abs = os.path.abspath(working_directory)
        target = os.path.abspath(os.path.join(wd_abs, directory))

        # stay inside the sandbox
        if not target.startswith(wd_abs):
            return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'

        if not os.path.isdir(target):
            return f'Error: "{directory}" is not a directory'

        names = sorted(os.listdir(target))
        if not names:
            return "(empty directory)"

        # Return lines that include just the names
        return "\n".join(names)

    except Exception as e:
        return f"Error: {e}"
