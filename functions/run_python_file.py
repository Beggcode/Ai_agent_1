# functions/run_python_file.py
from google.genai import types
import os
import sys
import subprocess

# --- SCHEMA: what the LLM can choose ---
schema_run_python_file = types.FunctionDeclaration(
    name="run_python_file",
    description="Execute a Python file with optional command-line arguments (relative path).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="Relative path to the Python file to execute (e.g., 'main.py').",
            ),
            "args": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
                description="Optional list of CLI args to pass to the script.",
            ),
        },
        required=["file_path"],
    ),
)

# --- RUNTIME: your existing implementation ---
def run_python_file(working_directory, file_path, args=None):
    if args is None:
        args = []
    try:
        working_directory_abs = os.path.abspath(working_directory)
        target_path = os.path.abspath(os.path.join(working_directory_abs, file_path))

        if not target_path.startswith(working_directory_abs):
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'
        if not os.path.exists(target_path):
            return f'Error: File "{file_path}" not found.'
        if not target_path.endswith(".py"):
            return f'Error: "{file_path}" is not a Python file.'

        cmd = [sys.executable, target_path] + args
        completed = subprocess.run(
            cmd,
            cwd=working_directory_abs,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()

        chunks = []
        if stdout:
            chunks.append(f"STDOUT:\n{stdout}")
        if stderr:
            chunks.append(f"STDERR:\n{stderr}")
        if completed.returncode != 0:
            chunks.append(f"Process exited with code {completed.returncode}")

        return "\n".join(chunks) if chunks else "No output produced."
    except Exception as e:
        return f"Error: executing Python file: {e}"
