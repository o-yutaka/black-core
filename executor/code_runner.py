from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


class CodeSafetyError(ValueError):
    """Raised when submitted code violates executor safety rules."""


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    timed_out: bool
    summary: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "summary": self.summary,
            "reward": 1.0 if self.success else -0.5,
        }


class CodeRunner:
    """Executes python snippets in an isolated subprocess with static safety checks."""

    FORBIDDEN_CALLS = {
        "os.system",
        "subprocess.run",
        "subprocess.Popen",
        "eval",
        "exec",
        "compile",
        "__import__",
    }
    FORBIDDEN_IMPORTS = {"os", "subprocess", "socket", "shutil", "pathlib"}

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds

    def _validate(self, code: str) -> None:
        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            raise CodeSafetyError(f"Syntax error: {error}") from error

        imported: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                name = self._call_name(node.func)
                if name in self.FORBIDDEN_CALLS:
                    raise CodeSafetyError(f"Forbidden call detected: {name}")

        prohibited = sorted(set(imported).intersection(self.FORBIDDEN_IMPORTS))
        if prohibited:
            raise CodeSafetyError(f"Forbidden imports detected: {', '.join(prohibited)}")

    @staticmethod
    def _call_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            left = CodeRunner._call_name(node.value)
            return f"{left}.{node.attr}" if left else node.attr
        return ""

    def run(self, code: str) -> ExecutionResult:
        self._validate(code)

        with tempfile.TemporaryDirectory(prefix="black_exec_") as temp_dir:
            path = Path(temp_dir) / "generated_task.py"
            path.write_text(code, encoding="utf-8")

            try:
                completed = subprocess.run(
                    [sys.executable, str(path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                success = completed.returncode == 0
                summary = "execution_success" if success else "execution_failed"
                return ExecutionResult(
                    success=success,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    return_code=completed.returncode,
                    timed_out=False,
                    summary=summary,
                )
            except subprocess.TimeoutExpired as timeout_error:
                return ExecutionResult(
                    success=False,
                    stdout=timeout_error.stdout or "",
                    stderr=(timeout_error.stderr or "") + "\nExecution timed out",
                    return_code=124,
                    timed_out=True,
                    summary="execution_timeout",
                )
