"""FluidAgent Pro runtime.

This module implements a reusable multi-stage research pipeline:
Codex implementation -> Codex/validator verification -> human review gating ->
Codex analysis -> human review gating -> Gemini paper draft ->
Codex Typst repair and final validation.

The implementation is intentionally stdlib-only so the controller can run in
minimal environments and be packaged later without extra Python dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import textwrap
import time
import traceback
import threading
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import termios
import tty


INVISIBLE_FILENAME_MARKS = {"\ufeff", "\u200b", "\u200c", "\u200d"}
DEFAULT_METADATA = {
    "title": "Real-Time Metal Surface Defect Detection with Improved YOLOv8",
    "authors": ["Unknown Author"],
    "reference_doi": "",
}
DEFAULT_STAGE_ATTEMPTS = 3
DEFAULT_CODEX_TIMEOUT = 60 * 60
DEFAULT_GEMINI_TIMEOUT = 5 * 60
DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"
DEFAULT_SUBDIRS = ("src", "configs", "weights", "analysis", "logs", "plots", "runs")
RESET_TOP_LEVEL_FILES = (
    ".agent_state.json",
    "current_task.txt",
    "paper.typ",
    "paper_final.typ",
    "paper.pdf",
)
RESET_TOP_LEVEL_DIRS = (
    "analysis",
    "logs",
    "plots",
    "runs",
    "__pycache__",
    ".mypy_cache",
    "$tmpdir",
)
RESET_HARD_TOP_LEVEL_DIRS = ("src",)
CLEAR_TOP_LEVEL_FILES = (
    "comparison_plot.png",
    "confusion_matrix.png",
    "f1_curve.png",
    "p_curve.png",
    "pr_curve.png",
    "r_curve.png",
    "results.png",
)
CLEAR_TOP_LEVEL_DIRS = (
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
)
CLEAR_TOP_LEVEL_GLOBS = (
    ".coverage*",
)
CLEAR_INSTALL_TOP_LEVEL_DIRS = (
    "build",
    "dist",
    ".eggs",
)
CLEAR_INSTALL_TOP_LEVEL_GLOBS = (
    "*.egg-info",
)
WORKSPACE_INVENTORY_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    "analysis",
    "build",
    "dist",
    "logs",
    "plots",
    "runs",
    "fluid-agent-pro",
    "fluid-agent-pro-open-source",
}
ARTIFACT_RE = re.compile(
    r"(?<![\w/])([A-Za-z0-9_./-]+\.(?:log|json|csv|png|svg|typ|pdf|txt|py|cpp|hpp|h|md))"
)


class WorkflowState(str, Enum):
    INIT = "STATE_INIT"
    CODING_VERIFY = "STATE_CODING_VERIFY"
    WAIT_VERIFY_REVIEW = "STATE_WAIT_VERIFY_REVIEW"
    DATA_ANALYSIS = "STATE_DATA_ANALYSIS"
    WAIT_ANALYSIS_REVIEW = "STATE_WAIT_ANALYSIS_REVIEW"
    PAPER_WRITING = "STATE_PAPER_WRITING"
    PAPER_FIX = "STATE_PAPER_FIX"
    WAIT_PAPER_REVIEW = "STATE_WAIT_PAPER_REVIEW"
    PAPER_TEMPLATE_EXPORT = "STATE_PAPER_TEMPLATE_EXPORT"
    WAIT_PAPER_TEMPLATE_REVIEW = "STATE_WAIT_PAPER_TEMPLATE_REVIEW"
    DONE = "STATE_DONE"
    ERROR = "STATE_ERROR"


def _strip_invisible_marks(text: str) -> str:
    return "".join(ch for ch in text if ch not in INVISIBLE_FILENAME_MARKS)


def _normalize_key(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum())


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def _json_load(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback


def _json_dump_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _shorten_text(text: str, limit: int = 160) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)] + "..."


def _delete_path(path: Path) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return True
    path.unlink()
    return True


def _is_probably_shell_command(text: str) -> bool:
    tokens = ("python", "pytest", "cmake", "make", "bash", "sh ", "python3", "typst", "cargo", "npm", "node")
    return any(token in text for token in tokens) or any(sep in text for sep in ("&&", "||", ";", "|"))


def _workspace_inventory(workspace: Path, max_depth: int = 2) -> str:
    lines: list[str] = []
    for path in sorted(workspace.rglob("*")):
        if not path.exists():
            continue
        rel = path.relative_to(workspace)
        if len(rel.parts) > max_depth:
            continue
        if any(part in WORKSPACE_INVENTORY_IGNORED_DIRS for part in rel.parts):
            continue
        suffix = "/" if path.is_dir() else ""
        lines.append(f"- {rel}{suffix}")
    return "\n".join(lines) if lines else "- (empty)"


def _load_metadata(metadata_path: Path) -> dict[str, object]:
    raw = _json_load(metadata_path, DEFAULT_METADATA.copy())
    if not isinstance(raw, dict):
        return DEFAULT_METADATA.copy()

    metadata = DEFAULT_METADATA.copy()
    title = raw.get("title") or raw.get("Title")
    if title:
        metadata["title"] = str(title)

    doi = raw.get("reference_doi") or raw.get("doi") or raw.get("DOI")
    if doi is not None:
        metadata["reference_doi"] = str(doi)

    authors = raw.get("authors") or raw.get("author") or raw.get("Authors")
    if isinstance(authors, list):
        cleaned = [str(item).strip() for item in authors if str(item).strip()]
        if cleaned:
            metadata["authors"] = cleaned
    elif isinstance(authors, str) and authors.strip():
        metadata["authors"] = [authors.strip()]

    for key in ("affiliations", "keywords", "venue", "year"):
        if key in raw:
            metadata[key] = raw[key]

    return metadata


@dataclass
class PhaseSpec:
    heading: str
    body: str
    commands: list[str] = field(default_factory=list)
    artifact_hints: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.heading.split(":", 1)[0].strip()


@dataclass
class ResearchPlan:
    path: Path
    preface: str
    phases: list[PhaseSpec]

    def phase_for_state(self, state: WorkflowState) -> PhaseSpec:
        if state == WorkflowState.CODING_VERIFY:
            return self._match_phase(("phase 1", "verification", "coding"))
        if state == WorkflowState.DATA_ANALYSIS:
            return self._match_phase(("phase 2", "analysis", "data"))
        if state in {WorkflowState.PAPER_WRITING, WorkflowState.PAPER_FIX, WorkflowState.PAPER_TEMPLATE_EXPORT}:
            return self._match_phase(("phase 3", "paper", "writing"))
        raise KeyError(f"No phase mapped to state {state.value}")

    def phase_by_label(self, label: str) -> Optional[PhaseSpec]:
        normalized = label.strip().lower()
        for phase in self.phases:
            phase_label = phase.label.strip().lower()
            phase_heading = phase.heading.strip().lower()
            if phase_label == normalized or phase_heading.startswith(normalized):
                return phase
        return None

    def _match_phase(self, keywords: tuple[str, ...]) -> PhaseSpec:
        for phase in self.phases:
            key = _normalize_key(phase.heading)
            if any(_normalize_key(word) in key for word in keywords):
                return phase
        if not self.phases:
            raise KeyError("Research plan has no phases.")
        return self.phases[min(len(self.phases) - 1, len(keywords) - 1)]


@dataclass
class EnvironmentCheckReport:
    success: bool
    checks: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    report_path: Optional[Path] = None


class ToolchainChecker:
    def check(
        self,
        *,
        phase: PhaseSpec,
        workspace: Path,
        log_dir: Path,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> EnvironmentCheckReport:
        status_cb = status_cb or (lambda _message: None)
        log_dir.mkdir(parents=True, exist_ok=True)
        report = EnvironmentCheckReport(success=True)
        phase_text = phase.body.lower()
        report.checks.append(f"python: {sys.executable} ({sys.version.split()[0]})")
        status_cb(f"[Bootstrap] Phase 0 tool check: python -> {sys.executable}")

        python_ok, python_detail = self._check_python_runtime()
        report.checks.append(python_detail)
        if not python_ok:
            report.success = False
            report.failures.append(python_detail)
            status_cb(f"[Bootstrap] Phase 0 tool check failed: {python_detail}")
        else:
            status_cb(f"[Bootstrap] Phase 0 tool check passed: {python_detail}")

        codex_ok, codex_detail = self._check_executable("codex")
        report.checks.append(codex_detail)
        if not codex_ok:
            report.success = False
            report.failures.append(codex_detail)
            status_cb(f"[Bootstrap] Phase 0 tool check failed: {codex_detail}")
        else:
            status_cb(f"[Bootstrap] Phase 0 tool check passed: {codex_detail}")

        executable_hints = {
            "pip": "pip",
            "typst": "typst",
        }
        for keyword, executable in executable_hints.items():
            if keyword not in phase_text:
                continue
            if executable == "typst":
                ok, detail = self._check_typst()
            else:
                ok, detail = self._check_executable(executable)
            report.checks.append(detail)
            if not ok:
                report.success = False
                report.failures.append(detail)
                status_cb(f"[Bootstrap] Phase 0 tool check failed: {detail}")
            else:
                status_cb(f"[Bootstrap] Phase 0 tool check passed: {detail}")

        module_hints = {
            "torchvision": "torchvision",
            "ultralytics": "ultralytics",
            "opencv-python": "cv2",
            "onnxruntime": "onnxruntime",
            "matplotlib": "matplotlib",
            "seaborn": "seaborn",
            "pandas": "pandas",
            "numpy": "numpy",
            "torch": "torch",
            "onnx": "onnx",
        }
        for keyword, module_name in module_hints.items():
            if keyword not in phase_text:
                continue
            ok, detail = self._check_python_module(module_name)
            report.checks.append(detail)
            if not ok:
                report.success = False
                report.failures.append(detail)
                status_cb(f"[Bootstrap] Phase 0 tool check failed: {detail}")
            else:
                status_cb(f"[Bootstrap] Phase 0 tool check passed: {detail}")

        report_path = log_dir / "phase0_environment_check.json"
        report.report_path = report_path
        _json_dump_atomic(
            report_path,
            {
                "success": report.success,
                "checks": report.checks,
                "failures": report.failures,
                "workspace": str(workspace),
                "phase_heading": phase.heading,
            },
        )
        (log_dir / "phase0_environment_check.log").write_text(
            "\n".join(report.checks + ([""] + report.failures if report.failures else [])) + "\n",
            encoding="utf-8",
        )
        return report

    @staticmethod
    def _check_python_runtime() -> tuple[bool, str]:
        version = sys.version.split()[0]
        if not version:
            return False, f"Python runtime unavailable: {sys.executable}"
        return True, f"Python runtime available: {sys.executable} ({version})"

    @staticmethod
    def _check_python_module(module_name: str) -> tuple[bool, str]:
        try:
            module = __import__(module_name)
        except Exception as exc:
            return False, f"Missing Python module: {module_name} ({exc})"
        version = getattr(module, "__version__", "unknown")
        return True, f"Python module available: {module_name} ({version})"

    @staticmethod
    def _check_executable(executable: str) -> tuple[bool, str]:
        path = shutil.which(executable)
        if path is None:
            return False, f"Missing executable on PATH: {executable}"
        try:
            completed = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except Exception as exc:
            return False, f"Failed to run {executable} --version: {exc}"
        version_text = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode != 0:
            return False, f"{executable} --version exited with rc={completed.returncode}: {version_text or '(no output)'}"
        return True, f"Executable available: {executable} ({version_text or path})"

    def _check_typst(self) -> tuple[bool, str]:
        path = shutil.which("typst")
        if path is None:
            return False, "Missing executable on PATH: typst"
        try:
            completed = subprocess.run(
                ["typst", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except Exception as exc:
            return False, f"Failed to run typst --version: {exc}"
        version_text = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode != 0:
            return False, f"typst --version exited with rc={completed.returncode}: {version_text or '(no output)'}"
        return True, f"Typst available: {version_text or path}"


@dataclass
class AgentContext:
    workspace: Path
    state_path: Path
    plan_path: Path
    metadata_path: Path
    state: WorkflowState = WorkflowState.INIT
    previous_state: Optional[WorkflowState] = None
    last_feedback: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)
    phase_attempts: dict[str, int] = field(default_factory=dict)
    consultations: list[dict[str, str]] = field(default_factory=list)
    plan_checksum: str = ""

    def load(self) -> None:
        if not self.state_path.exists():
            self.artifacts.setdefault("workspace", str(self.workspace))
            self.artifacts.setdefault("plan_path", str(self.plan_path))
            self.artifacts.setdefault("metadata_path", str(self.metadata_path))
            self.save()
            return

        data = _json_load(self.state_path, {})
        if not isinstance(data, dict):
            raise RuntimeError(f"Invalid state file: {self.state_path}")

        self.state = _coerce_state(data.get("state"), WorkflowState.INIT) or WorkflowState.INIT
        self.previous_state = _coerce_state(data.get("previous_state"), None)
        self.last_feedback = str(data.get("last_feedback", ""))
        self.artifacts = {str(k): str(v) for k, v in (data.get("artifacts") or {}).items()} if isinstance(data.get("artifacts"), dict) else {}
        self.phase_attempts = {str(k): int(v) for k, v in (data.get("phase_attempts") or {}).items()} if isinstance(data.get("phase_attempts"), dict) else {}
        consultations = data.get("consultations")
        self.consultations = []
        if isinstance(consultations, list):
            for item in consultations:
                if isinstance(item, dict):
                    self.consultations.append({str(k): str(v) for k, v in item.items()})
        self.plan_checksum = str(data.get("plan_checksum", ""))

        self.artifacts.setdefault("workspace", str(self.workspace))
        self.artifacts.setdefault("plan_path", str(self.plan_path))
        self.artifacts.setdefault("metadata_path", str(self.metadata_path))

    def save(self) -> None:
        payload = {
            "schema_version": 3,
            "workspace": str(self.workspace),
            "state_path": str(self.state_path),
            "plan_path": str(self.plan_path),
            "metadata_path": str(self.metadata_path),
            "state": self.state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "last_feedback": self.last_feedback,
            "artifacts": self.artifacts,
            "phase_attempts": self.phase_attempts,
            "consultations": self.consultations,
            "plan_checksum": self.plan_checksum,
        }
        _json_dump_atomic(self.state_path, payload)

    def transition_to(self, next_state: WorkflowState) -> None:
        self.previous_state = self.state
        self.state = next_state

    def rollback(self) -> None:
        self.state = self.previous_state or WorkflowState.INIT
        self.previous_state = None

    def bump_attempt(self, stage: WorkflowState) -> int:
        key = stage.value
        self.phase_attempts[key] = self.phase_attempts.get(key, 0) + 1
        return self.phase_attempts[key]


def _coerce_state(value: object, default: Optional[WorkflowState]) -> Optional[WorkflowState]:
    if value is None:
        return default
    if isinstance(value, WorkflowState):
        return value
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return default
        try:
            return WorkflowState(candidate)
        except ValueError:
            try:
                return WorkflowState[candidate]
            except KeyError:
                return default
    return default


class PlanParser:
    def resolve_plan_path(self, workspace: Path) -> Path:
        exact = workspace / "research_plan.md"
        if exact.exists():
            return exact
        candidates = []
        for entry in workspace.iterdir():
            if entry.is_file() and _strip_invisible_marks(entry.name) == "research_plan.md":
                candidates.append(entry)
        if not candidates:
            raise FileNotFoundError(f"Could not find research_plan.md in {workspace}")
        return sorted(candidates, key=lambda item: (len(item.name), item.name))[0]

    def parse(self, plan_path: Path) -> ResearchPlan:
        text = plan_path.read_text(encoding="utf-8")
        preface = ""
        phases: list[PhaseSpec] = []
        current_heading: Optional[str] = None
        current_lines: list[str] = []

        for line in text.splitlines():
            if line.startswith("## "):
                if current_heading is not None:
                    body = "\n".join(current_lines).strip()
                    phases.append(
                        PhaseSpec(
                            heading=current_heading,
                            body=body,
                            commands=self._extract_commands(body),
                            artifact_hints=self._extract_artifacts(body),
                        )
                    )
                else:
                    preface = "\n".join(current_lines).strip()
                current_heading = line[3:].strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_heading is not None:
            body = "\n".join(current_lines).strip()
            phases.append(
                PhaseSpec(
                    heading=current_heading,
                    body=body,
                    commands=self._extract_commands(body),
                    artifact_hints=self._extract_artifacts(body),
                )
            )
        elif text.strip():
            preface = text.strip()

        return ResearchPlan(path=plan_path, preface=preface, phases=phases)

    def build_codex_prompt(
        self,
        *,
        plan: ResearchPlan,
        phase: PhaseSpec,
        state: WorkflowState,
        workspace: Path,
        context: AgentContext,
        stage_goal: str,
    ) -> str:
        instructions = [
            "You are Codex running inside FluidAgent Pro.",
            f"Stage goal: {stage_goal}",
            f"Current state: {state.value}",
            f"Workspace: {workspace}",
            "",
            "Hard rules:",
            "- Edit the current workspace in place. Do not recreate the whole project.",
            "- Keep the controller files intact unless the plan explicitly requires changes.",
            "- Make the smallest useful incremental changes.",
            "- When validation fails, fix the same stage instead of starting over.",
            "- Return a concise final summary in your last message.",
            "- Do not start by recursively enumerating the entire workspace; inspect the explicit source files in this prompt first and only expand outward when needed.",
            "",
            "Workspace hygiene:",
            "- Treat the workspace-root copies of fluid_agent_pro.py, research_plan.md, and paper-template/ as authoritative.",
            "- Ignore backup copies under fluid-agent-pro/ and fluid-agent-pro-open-source/ unless the task explicitly names them.",
            "- Ignore generated directories such as analysis/, build/, dist/, logs/, plots/, runs/, and any *.egg-info metadata.",
            "- Avoid whole-tree scans like `rg --files .` or `find .` unless a later step absolutely requires them.",
        ]

        if plan.preface:
            instructions += ["", "Plan preface:", plan.preface]

        instructions += ["", f"Phase: {phase.heading}", phase.body]

        if phase.commands:
            instructions += ["", "Validation commands extracted from the plan:"]
            instructions += [f"- {cmd}" for cmd in phase.commands]

        if phase.artifact_hints:
            instructions += ["", "Expected artifacts extracted from the plan:"]
            instructions += [f"- {hint}" for hint in phase.artifact_hints]

        if context.last_feedback:
            instructions += ["", "Reviewer feedback to incorporate:", context.last_feedback]

        instructions += ["", "Workspace inventory:", _workspace_inventory(workspace)]
        return "\n".join(instructions).strip() + "\n"

    @staticmethod
    def _extract_commands(body: str) -> list[str]:
        commands: list[str] = []
        fence_re = re.compile(r"```(?P<lang>[^\n`]*)\n(?P<body>.*?)\n```", re.S)
        for match in fence_re.finditer(body):
            lang = match.group("lang").strip().lower()
            block = match.group("body").strip()
            if lang in {"bash", "sh", "shell", "zsh", "console", ""}:
                for line in block.splitlines():
                    line = line.strip()
                    if line.startswith("$ "):
                        line = line[2:]
                    if line and _is_probably_shell_command(line):
                        commands.append(line)
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("- run:"):
                cmd = stripped.split(":", 1)[1].strip()
                if cmd:
                    commands.append(cmd)
        deduped: list[str] = []
        for cmd in commands:
            if cmd not in deduped:
                deduped.append(cmd)
        return deduped

    @staticmethod
    def _extract_artifacts(body: str) -> list[str]:
        hints: list[str] = []
        for match in ARTIFACT_RE.finditer(body):
            hints.append(match.group(1))
        deduped: list[str] = []
        for hint in hints:
            if hint not in deduped:
                deduped.append(hint)
        return deduped


@dataclass
class CodexExecution:
    run_dir: Path
    prompt_path: Path
    stdout_path: Path
    stderr_path: Path
    events_path: Path
    last_message_path: Path
    returncode: int
    modified_files: list[str] = field(default_factory=list)
    stdout_text: str = ""
    stderr_text: str = ""
    last_message: str = ""


class CodexRunner:
    def __init__(
        self,
        *,
        model: Optional[str] = None,
        timeout_seconds: int = DEFAULT_CODEX_TIMEOUT,
        unsafe_bypass: bool = False,
    ) -> None:
        self.model = model or os.environ.get("FLUID_AGENT_CODEX_MODEL", "").strip() or None
        self.timeout_seconds = timeout_seconds
        self.unsafe_bypass = unsafe_bypass or os.environ.get("FLUID_AGENT_CODEX_UNSAFE", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def run(self, *, workspace: Path, prompt: str, run_dir: Path) -> CodexExecution:
        return self.run_with_status(workspace=workspace, prompt=prompt, run_dir=run_dir, status_cb=None)

    def run_with_status(
        self,
        *,
        workspace: Path,
        prompt: str,
        run_dir: Path,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> CodexExecution:
        status_cb = status_cb or (lambda _message: None)
        if shutil.which("codex") is None:
            raise FileNotFoundError("codex CLI not found on PATH.")

        run_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = run_dir / "prompt.txt"
        stdout_path = run_dir / "codex.stdout.jsonl"
        stderr_path = run_dir / "codex.stderr.log"
        events_path = run_dir / "codex.events.json"
        last_message_path = run_dir / "codex.last_message.txt"
        prompt_path.write_text(prompt, encoding="utf-8")

        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--full-auto",
            "--json",
            "--output-last-message",
            str(last_message_path),
            "-C",
            str(workspace),
        ]
        if self.model:
            cmd += ["-m", self.model]
        if self.unsafe_bypass:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        cmd.append("-")

        stdout_events: list[dict[str, Any]] = []
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        start_time = time.monotonic()
        last_activity = start_time
        last_heartbeat = start_time
        heartbeat_interval = 30.0

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=workspace,
            bufsize=1,
        )

        def read_stdout() -> None:
            nonlocal last_activity
            assert process.stdout is not None
            with stdout_path.open("w", encoding="utf-8") as out:
                for raw_line in iter(process.stdout.readline, ""):
                    if raw_line == "":
                        break
                    out.write(raw_line)
                    out.flush()
                    stdout_lines.append(raw_line)
                    last_activity = time.monotonic()
                    event = self._summarize_event_line(raw_line, status_cb=status_cb)
                    if event is not None:
                        stdout_events.append(event)
            process.stdout.close()

        def read_stderr() -> None:
            nonlocal last_activity
            assert process.stderr is not None
            with stderr_path.open("w", encoding="utf-8") as out:
                for raw_line in iter(process.stderr.readline, ""):
                    if raw_line == "":
                        break
                    out.write(raw_line)
                    out.flush()
                    stderr_lines.append(raw_line)
                    last_activity = time.monotonic()
                    text = raw_line.strip()
                    if text:
                        status_cb(f"[Codex:stderr] {_shorten_text(text, 200)}")
            process.stderr.close()

        stdout_thread = threading.Thread(target=read_stdout, name="codex-stdout-reader", daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, name="codex-stderr-reader", daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        try:
            assert process.stdin is not None
            process.stdin.write(prompt)
            process.stdin.close()

            while True:
                returncode = process.poll()
                if returncode is not None:
                    break
                now = time.monotonic()
                if now - start_time > self.timeout_seconds:
                    process.kill()
                    raise TimeoutError(f"Codex timed out after {self.timeout_seconds} seconds.")
                if now - last_heartbeat >= heartbeat_interval and now - last_activity >= heartbeat_interval:
                    status_cb("[Codex] still running...")
                    last_heartbeat = now
                time.sleep(1.0)
        except KeyboardInterrupt:
            process.kill()
            raise
        finally:
            try:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
            except Exception:
                pass

        stdout_thread.join(timeout=10.0)
        stderr_thread.join(timeout=10.0)

        returncode = process.wait()
        stdout_text = "".join(stdout_lines)
        stderr_text = "".join(stderr_lines)
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")

        modified_files = self._parse_modified_files(stdout_text)
        events_path.write_text(
            json.dumps(
                {
                    "returncode": returncode,
                    "duration_seconds": round(time.monotonic() - start_time, 3),
                    "events": stdout_events,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        last_message = last_message_path.read_text(encoding="utf-8") if last_message_path.exists() else ""

        return CodexExecution(
            run_dir=run_dir,
            prompt_path=prompt_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            events_path=events_path,
            last_message_path=last_message_path,
            returncode=returncode,
            modified_files=modified_files,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            last_message=last_message,
        )

    @staticmethod
    def _parse_modified_files(stdout_text: str) -> list[str]:
        modified: list[str] = []
        for line in stdout_text.splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            item = obj.get("item")
            if not isinstance(item, dict):
                continue
            if item.get("type") != "file_change":
                continue
            for change in item.get("changes", []):
                if isinstance(change, dict):
                    path = change.get("path")
                    if path and path not in modified:
                        modified.append(str(path))
        return modified

    @staticmethod
    def _summarize_event_line(line: str, *, status_cb: Callable[[str], None]) -> Optional[dict[str, Any]]:
        raw = line.strip()
        if not raw:
            return None
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            status_cb(f"[Codex] {_shorten_text(raw, 180)}")
            return {"type": "raw", "text": raw}

        event_type = event.get("type", "unknown")
        summary: Optional[str] = None

        if event_type == "thread.started":
            summary = f"[Codex] thread started ({event.get('thread_id', 'unknown')})"
        elif event_type == "turn.started":
            summary = "[Codex] turn started"
        elif event_type == "turn.completed":
            usage = event.get("usage") or {}
            summary = (
                f"[Codex] turn completed "
                f"(input={usage.get('input_tokens', '?')}, output={usage.get('output_tokens', '?')})"
            )
        elif event_type == "item.started":
            item = event.get("item") or {}
            item_type = item.get("type")
            if item_type == "command_execution":
                summary = f"[Codex] running command: {_shorten_text(str(item.get('command', '')), 220)}"
            elif item_type == "agent_message":
                summary = f"[Codex] {_shorten_text(str(item.get('text', '')), 220)}"
        elif event_type == "item.completed":
            item = event.get("item") or {}
            item_type = item.get("type")
            if item_type == "agent_message":
                summary = f"[Codex] {_shorten_text(str(item.get('text', '')), 220)}"
            elif item_type == "file_change":
                changes = item.get("changes") or []
                paths = [
                    str(change.get("path"))
                    for change in changes
                    if isinstance(change, dict) and change.get("path")
                ]
                if paths:
                    summary = f"[Codex] file change: {', '.join(paths[:4])}"
                else:
                    summary = "[Codex] file change recorded"
            elif item_type == "command_execution":
                summary = (
                    f"[Codex] command completed rc={item.get('exit_code', '?')}: "
                    f"{_shorten_text(str(item.get('command', '')), 220)}"
                )

        if summary:
            status_cb(summary)
        return {"type": event_type, "summary": summary or raw}


@dataclass
class ValidationReport:
    success: bool
    checks: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    executed_commands: list[str] = field(default_factory=list)
    artifact_checks: list[str] = field(default_factory=list)
    report_path: Optional[Path] = None


class ValidationRunner:
    def __init__(self, *, command_timeout: int = 60 * 30) -> None:
        self.command_timeout = command_timeout

    def validate(
        self,
        *,
        state: WorkflowState,
        phase: PhaseSpec,
        workspace: Path,
        run_dir: Path,
        status_cb: Optional[Callable[[str], None]] = None,
        template_root: Optional[Path] = None,
    ) -> ValidationReport:
        status_cb = status_cb or (lambda _message: None)
        run_dir.mkdir(parents=True, exist_ok=True)
        report = ValidationReport(success=True)

        commands = list(phase.commands)
        commands.extend(self._default_commands(state=state, workspace=workspace))
        deduped_commands = self._dedupe(commands)
        if deduped_commands:
            status_cb(f"[Validator] {state.value}: running {len(deduped_commands)} command(s)")
        for index, command in enumerate(deduped_commands, start=1):
            status_cb(f"[Validator] command {index}/{len(deduped_commands)}: {_shorten_text(command, 240)}")
            result = self._run_shell_command(command, workspace=workspace, run_dir=run_dir)
            report.executed_commands.append(command)
            report.checks.append(result["summary"])
            if result["returncode"] != 0:
                report.success = False
                report.failures.append(result["summary"])
                status_cb(f"[Validator] command {index}/{len(deduped_commands)} failed rc={result['returncode']}")
            else:
                status_cb(f"[Validator] command {index}/{len(deduped_commands)} passed")

        artifacts = list(phase.artifact_hints)
        artifacts.extend(self._default_artifacts(state=state))
        deduped_artifacts = self._dedupe(artifacts)
        if deduped_artifacts:
            status_cb(f"[Validator] {state.value}: checking {len(deduped_artifacts)} artifact(s)")
        for index, hint in enumerate(deduped_artifacts, start=1):
            resolved = self._resolve_artifact_hint(hint, workspace)
            if resolved.exists():
                size = resolved.stat().st_size
                report.artifact_checks.append(f"OK {hint} -> {resolved} ({size} bytes)")
                status_cb(
                    f"[Validator] artifact {index}/{len(deduped_artifacts)} OK: {hint} -> {resolved} ({size} bytes)"
                )
                if size <= 0:
                    report.success = False
                    report.failures.append(f"Artifact is empty: {resolved}")
            else:
                report.artifact_checks.append(f"MISSING {hint} -> {resolved}")
                report.success = False
                report.failures.append(f"Missing artifact: {resolved}")
                status_cb(f"[Validator] artifact {index}/{len(deduped_artifacts)} MISSING: {hint} -> {resolved}")

        if state in {WorkflowState.PAPER_WRITING, WorkflowState.PAPER_FIX, WorkflowState.PAPER_TEMPLATE_EXPORT}:
            paper_path = self._paper_source_path(state, workspace)
            if paper_path.exists():
                status_cb(f"[Validator] {paper_path.name} exists; running structure checks")
                checks = self._check_paper_source(
                    paper_path,
                    workspace,
                    state=state,
                    template_root=template_root,
                )
                report.checks.extend(checks["checks"])
                report.failures.extend(checks["failures"])
                if not checks["success"]:
                    report.success = False
                    status_cb(f"[Validator] {paper_path.name} structure check failed")
                else:
                    status_cb(f"[Validator] {paper_path.name} structure check passed")
            else:
                status_cb(f"[Validator] {paper_path.name} missing")
                report.success = False
                report.failures.append(f"{paper_path.name} missing")

        report_path = run_dir / "validation_report.json"
        report.report_path = report_path
        _json_dump_atomic(
            report_path,
            {
                "success": report.success,
                "checks": report.checks,
                "failures": report.failures,
                "executed_commands": report.executed_commands,
                "artifact_checks": report.artifact_checks,
            },
        )
        return report

    def _default_commands(self, *, state: WorkflowState, workspace: Path) -> list[str]:
        commands: list[str] = []
        if state in {WorkflowState.CODING_VERIFY, WorkflowState.DATA_ANALYSIS}:
            python_files = self._python_files(workspace)
            if python_files:
                quoted = " ".join(repr(str(path)) for path in python_files)
                commands.append(f"{shlex_quote(sys.executable)} -m py_compile {quoted}")

        if state == WorkflowState.DATA_ANALYSIS:
            analysis_script = workspace / "analysis" / "run_analysis.py"
            if analysis_script.exists():
                commands.insert(0, f"{shlex_quote(sys.executable)} {shlex_quote(str(analysis_script))}")

        if state in {WorkflowState.PAPER_WRITING, WorkflowState.PAPER_FIX} and shutil.which("typst"):
            commands.append(f"typst compile {shlex_quote(str(workspace / 'paper.typ'))} {shlex_quote(str(workspace / 'paper.pdf'))}")
        if state == WorkflowState.PAPER_TEMPLATE_EXPORT and shutil.which("typst"):
            commands.append(
                f"typst compile {shlex_quote(str(workspace / 'paper_final.typ'))} {shlex_quote(str(workspace / 'paper.pdf'))}"
            )
        return commands

    def _default_artifacts(self, *, state: WorkflowState) -> list[str]:
        if state in {WorkflowState.PAPER_WRITING, WorkflowState.PAPER_FIX}:
            return ["paper.typ"]
        if state == WorkflowState.PAPER_TEMPLATE_EXPORT:
            return ["paper_final.typ", "paper.pdf"]
        return []

    def _python_files(self, workspace: Path) -> list[Path]:
        paths: list[Path] = []
        skip_parts = {".git", "__pycache__", ".mypy_cache", "runs"}
        for path in workspace.rglob("*.py"):
            if any(part in skip_parts for part in path.parts):
                continue
            paths.append(path)
        return sorted(paths)

    def _run_shell_command(self, command: str, *, workspace: Path, run_dir: Path) -> dict[str, Any]:
        index = len(list(run_dir.glob("command_*.log"))) + 1
        log_path = run_dir / f"command_{index:02d}.log"
        started = time.time()
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=self.command_timeout,
            check=False,
        )
        duration = time.time() - started
        log_path.write_text(
            "\n".join(
                [
                    f"$ {command}",
                    f"returncode: {completed.returncode}",
                    "",
                    completed.stdout or "",
                    "",
                    completed.stderr or "",
                ]
            ),
            encoding="utf-8",
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or "",
            "duration_seconds": round(duration, 3),
            "log_path": str(log_path),
            "summary": f"{command} -> rc={completed.returncode} ({duration:.1f}s)",
        }

    def _paper_source_path(self, state: WorkflowState, workspace: Path) -> Path:
        if state == WorkflowState.PAPER_TEMPLATE_EXPORT:
            return workspace / "paper_final.typ"
        return workspace / "paper.typ"

    def _check_paper_source(
        self,
        paper_path: Path,
        workspace: Path,
        *,
        state: WorkflowState,
        template_root: Optional[Path] = None,
    ) -> dict[str, Any]:
        text = paper_path.read_text(encoding="utf-8")
        checks = []
        failures = []
        if state == WorkflowState.PAPER_TEMPLATE_EXPORT:
            required_sections = ["Introduction", "Methods", "Results", "Discussion", "Conclusion"]
            if re.search(r"(?m)^#show:\s*iclr2025\.with\(", text):
                checks.append("OK template wrapper present: iclr2025.with")
            else:
                failures.append("Missing template wrapper: iclr2025.with")
            for token in ("#set document(", "#set heading(", "#set text("):
                if token in text:
                    failures.append(f"Draft-only directive should be removed: {token}")
            if template_root is not None:
                logo_name = re.escape((template_root / "logo.typ").name)
                if re.search(rf"(?m)^#import\s+\"[^\"]*{logo_name}\":\s*LaTeX,\s*LaTeXe", text):
                    checks.append("OK template logo import present")
                else:
                    failures.append("Missing template logo import")
            if re.search(r"(?m)^#bibliography\(", text):
                checks.append("OK bibliography call present")
            else:
                failures.append("Missing bibliography call")
            if template_root is not None:
                template_logo = template_root / "logo.typ"
                if template_logo.exists():
                    checks.append(f"OK template asset present: {template_logo}")
                else:
                    failures.append(f"Missing template asset: {template_logo}")
        else:
            required_sections = ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion"]
        for section in required_sections:
            if self._paper_has_section(text, section):
                checks.append(f"OK section present: {section}")
            else:
                failures.append(f"Missing section: {section}")
        for token in ("TODO", "TBD", "PLACEHOLDER"):
            if token in text:
                failures.append(f"Found placeholder token: {token}")
        if state == WorkflowState.PAPER_TEMPLATE_EXPORT and re.search(r"(?m)^abstract:\s*\[", text):
            checks.append("OK abstract parameter present in template wrapper")
        elif state == WorkflowState.PAPER_TEMPLATE_EXPORT:
            failures.append("Missing abstract parameter in template wrapper")
        return {
            "success": not failures,
            "checks": checks,
            "failures": failures,
        }

    @staticmethod
    def _paper_has_section(text: str, title: str) -> bool:
        patterns = [
            rf"(?m)^=+\s*{re.escape(title)}\b",
            rf"(?m)^#heading\([^\n]*\)\s*\[{re.escape(title)}\]",
            rf"(?m)^#heading\([^\n]*{re.escape(title)}[^\n]*\)",
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    def _resolve_artifact_hint(self, hint: str, workspace: Path) -> Path:
        hint_path = Path(hint)
        if hint_path.is_absolute():
            return hint_path
        candidates = [workspace / hint_path]
        if len(hint_path.parts) == 1:
            for subdir in ("logs", "analysis", "plots", "src", "runs"):
                candidates.append(workspace / subdir / hint_path.name)
        else:
            candidates.append(workspace / hint_path)
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


@dataclass
class GeminiExecution:
    request_path: Path
    response_path: Path
    raw_response_path: Path
    text: str
    data: dict[str, Any]


class GeminiClient:
    def __init__(
        self,
        *,
        model: Optional[str] = None,
        timeout_seconds: int = DEFAULT_GEMINI_TIMEOUT,
        max_retries: int = 5,
        base_backoff: float = 1.5,
        max_backoff: float = 30.0,
    ) -> None:
        self.model = model or os.environ.get("FLUID_AGENT_GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff

    def generate_json(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        schema: dict[str, Any],
        run_dir: Path,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> GeminiExecution:
        status_cb = status_cb or (lambda _message: None)
        api_key = self._api_key()
        run_dir.mkdir(parents=True, exist_ok=True)
        request_path = run_dir / "gemini_request.json"
        response_path = run_dir / "gemini_response.json"
        raw_response_path = run_dir / "gemini_raw_response.txt"

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
                "temperature": 0.2,
            },
        }
        _json_dump_atomic(request_path, payload)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = json.dumps(payload).encode("utf-8")
        last_error: Optional[Exception] = None
        status_cb(f"[Gemini] request prepared for model {self.model}")
        for attempt in range(1, self.max_retries + 1):
            status_cb(f"[Gemini] attempt {attempt}/{self.max_retries}")
            req = Request(
                url,
                data=body,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urlopen(req, timeout=self.timeout_seconds) as resp:
                    raw = resp.read().decode("utf-8")
                raw_response_path.write_text(raw, encoding="utf-8")
                data = json.loads(raw)
                text = self._extract_text(data)
                response_path.write_text(text, encoding="utf-8")
                return GeminiExecution(
                    request_path=request_path,
                    response_path=response_path,
                    raw_response_path=raw_response_path,
                    text=text,
                    data=data,
                )
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 503} or attempt == self.max_retries:
                    raise
                status_cb(f"[Gemini] HTTP {exc.code}; retrying with backoff")
                self._sleep_backoff(attempt, exc)
            except URLError as exc:
                last_error = exc
                if attempt == self.max_retries:
                    raise
                status_cb(f"[Gemini] transport error; retrying with backoff")
                self._sleep_backoff(attempt, exc)
        assert last_error is not None
        raise last_error

    def _api_key(self) -> str:
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            value = os.environ.get(name, "").strip()
            if value:
                return value
        raise RuntimeError("Missing Gemini API key. Set GEMINI_API_KEY or GOOGLE_API_KEY.")

    def _sleep_backoff(self, attempt: int, exc: Exception) -> None:
        delay = min(self.max_backoff, self.base_backoff * (2 ** (attempt - 1)))
        if isinstance(exc, HTTPError):
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    pass
        time.sleep(delay + random.uniform(0, 0.5))

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini response did not contain candidates: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        text = "".join(text_parts).strip()
        if not text:
            raise RuntimeError(f"Gemini response did not contain text parts: {data}")
        return text


@dataclass
class ReviewDecision:
    approved: bool
    feedback: str = ""
    quit_requested: bool = False
    consult_requested: bool = False
    rewind_requested: bool = False
    rewind_target_state: Optional[WorkflowState] = None
    question: str = ""


class HumanReviewCLI:
    def __init__(self, *, auto_approve: Optional[bool] = None, force_stdio: bool = False) -> None:
        self.force_stdio = force_stdio
        if auto_approve is None:
            env_flag = os.environ.get("FLUID_AGENT_AUTO_APPROVE", "").strip().lower()
            if force_stdio:
                auto_approve = env_flag in {"1", "true", "yes", "on"}
            else:
                auto_approve = env_flag in {"1", "true", "yes", "on"} or not sys.stdin.isatty()
        self.auto_approve = auto_approve

    def print_status(self, message: str) -> None:
        print(f">>> [FluidAgentPro] {message}", flush=True)

    def prompt(
        self,
        *,
        state: WorkflowState,
        log_path: Path,
        summary_lines: list[str],
        prompt_text: Optional[str] = None,
        feedback_prompt: Optional[str] = None,
        rewind_feedback_prompt: Optional[str] = None,
        allow_rewind: bool = False,
        rewind_target_state: Optional[WorkflowState] = None,
    ) -> ReviewDecision:
        if state in {WorkflowState.WAIT_PAPER_REVIEW, WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW}:
            waiting_for = "repair guidance"
        else:
            waiting_for = "approval"
        self.print_status(f"[Review] Waiting for {waiting_for} at {state.value}")
        self.print_status(f"[Review] Inspect log/report: {log_path}")
        for line in summary_lines:
            self.print_status(f"[Review] {line}")
        if self.auto_approve:
            self.print_status("[Review] Auto-approve enabled.")
            return ReviewDecision(approved=True)

        prompt_text = prompt_text or "Approve with Y, reject with N, consult Codex with C, or quit with Q:"
        feedback_prompt = feedback_prompt or "Enter reviewer feedback: "
        rewind_feedback_prompt = rewind_feedback_prompt or "Describe why this should go back to Phase 2: "
        while True:
            try:
                self.print_status(f"[Review] {prompt_text}")
                answer = self._read_visible_line(">>> [FluidAgentPro] [Review] Choice: ").strip()
            except EOFError:
                return ReviewDecision(approved=True)
            choice = answer.casefold()
            self.print_status(f"[Review] Choice received: {answer!r}")
            if choice in {"y", "yes"}:
                self.print_status("[Review] Selected action: APPROVE")
                return ReviewDecision(approved=True)
            if choice in {"q", "quit"}:
                self.print_status("[Review] Selected action: QUIT")
                return ReviewDecision(approved=False, quit_requested=True)
            if choice in {"c", "consult", "?"}:
                self.print_status("[Review] Selected action: CONSULT")
                question = self._read_multiline_question()
                if question:
                    return ReviewDecision(approved=False, consult_requested=True, question=question)
                self.print_status("[Review] Question cannot be empty.")
                continue
            normalized_choice = _normalize_key(choice)
            if allow_rewind and rewind_target_state is not None:
                rewind_aliases = {
                    WorkflowState.CODING_VERIFY: {
                        "b",
                        "back",
                        "rewind",
                        "p1",
                        "phase1",
                        "backp1",
                        "rewindp1",
                        "backphase1",
                        "rewindphase1",
                        "phase1back",
                        "phase1rewind",
                        "1",
                    },
                    WorkflowState.DATA_ANALYSIS: {
                        "b",
                        "back",
                        "rewind",
                        "p2",
                        "phase2",
                        "backp2",
                        "rewindp2",
                        "backphase2",
                        "rewindphase2",
                        "phase2rewind",
                        "phase2back",
                        "2",
                    },
                }
                if normalized_choice in rewind_aliases.get(rewind_target_state, set()):
                    target_label = rewind_target_state.value
                    self.print_status(f"[Review] Selected action: REWIND_TO_{target_label}")
                    feedback = input(rewind_feedback_prompt).strip()
                    return ReviewDecision(
                        approved=False,
                        feedback=feedback,
                        rewind_requested=True,
                        rewind_target_state=rewind_target_state,
                    )
            elif allow_rewind and normalized_choice in {
                "b",
                "back",
                "rewind",
                "p2",
                "phase2",
                "backp2",
                "rewindp2",
                "backphase2",
                "rewindphase2",
                "phase2rewind",
                "phase2back",
                "2",
            }:
                self.print_status("[Review] Selected action: REWIND_TO_PHASE_2")
                feedback = input(rewind_feedback_prompt).strip()
                return ReviewDecision(approved=False, feedback=feedback, rewind_requested=True, rewind_target_state=WorkflowState.DATA_ANALYSIS)
            if choice in {"n", "no"}:
                self.print_status("[Review] Selected action: REJECT")
                feedback = input(feedback_prompt).strip()
                return ReviewDecision(approved=False, feedback=feedback)
            if allow_rewind:
                self.print_status("[Review] Please enter Y, N, B, C, or Q.")
            else:
                self.print_status("[Review] Please enter Y, N, C, or Q.")

    def _read_visible_line(self, prompt: str) -> str:
        if self.force_stdio:
            return input(prompt)
        tty_fd: Optional[int] = None
        owns_tty_fd = False
        try:
            try:
                tty_fd = os.open("/dev/tty", os.O_RDWR)
                owns_tty_fd = True
            except OSError:
                if not sys.stdin.isatty():
                    return input(prompt)
                tty_fd = sys.stdin.fileno()

            original = termios.tcgetattr(tty_fd)
            os.write(tty_fd, prompt.encode("utf-8", errors="ignore"))
            chars: list[str] = []
            try:
                tty.setcbreak(tty_fd)
                while True:
                    raw = os.read(tty_fd, 1)
                    if not raw:
                        break
                    ch = raw.decode("utf-8", errors="ignore")
                    if ch in {"\r", "\n"}:
                        os.write(tty_fd, b"\n")
                        break
                    if ch in {"\x7f", "\b"}:
                        if chars:
                            chars.pop()
                            os.write(tty_fd, b"\b \b")
                        continue
                    chars.append(ch)
                    os.write(tty_fd, raw)
            finally:
                termios.tcsetattr(tty_fd, termios.TCSADRAIN, original)
            return "".join(chars)
        finally:
            if owns_tty_fd and tty_fd is not None:
                os.close(tty_fd)

    def _read_multiline_question(self) -> str:
        self.print_status("[Review] Enter your question for Codex.")
        self.print_status("[Review] Finish with a blank line.")
        lines: list[str] = []
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            if not line.strip():
                break
            lines.append(line.rstrip())
        return "\n".join(lines).strip()


class PaperWriter:
    def __init__(self, client: GeminiClient) -> None:
        self.client = client

    def write(
        self,
        *,
        context: AgentContext,
        plan: ResearchPlan,
        phase: PhaseSpec,
        verification_report: ValidationReport,
        analysis_report: ValidationReport,
        run_dir: Path,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> GeminiExecution:
        status_cb = status_cb or (lambda _message: None)
        metadata = _load_metadata(context.metadata_path)
        schema = {
            "type": "object",
            "properties": {
                "paper_typst": {"type": "string"},
                "summary": {"type": "string"},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["paper_typst", "summary", "warnings"],
            "additionalProperties": False,
        }
        system_instruction = textwrap.dedent(
            """
            You are an expert scientific writer.
            Produce a valid Typst manuscript using only the provided facts.
            Do not hallucinate numbers, citations, or claims.
            If information is missing, state the limitation in warnings instead of inventing it.
            Return JSON only that matches the requested schema.
            """
        ).strip()
        user_prompt = self._build_prompt(
            context=context,
            plan=plan,
            phase=phase,
            metadata=metadata,
            verification_report=verification_report,
            analysis_report=analysis_report,
        )
        status_cb(f"[Gemini] writing paper draft for {phase.heading}")

        attempt_dir = run_dir / "gemini"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        execution = self.client.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            schema=schema,
            run_dir=attempt_dir,
            status_cb=status_cb,
        )
        data = json.loads(execution.text)
        paper_typst = str(data.get("paper_typst", "")).strip()
        if not paper_typst:
            raise RuntimeError("Gemini response did not include paper_typst.")
        paper_typst = self._sanitize_typst_paper(paper_typst)

        paper_path = context.workspace / "paper.typ"
        paper_path.write_text(paper_typst.rstrip() + "\n", encoding="utf-8")
        paper_log = run_dir / "paper_writer.log"
        paper_log.write_text(
            json.dumps(
                {
                    "summary": data.get("summary", ""),
                    "warnings": data.get("warnings", []),
                    "paper_path": str(paper_path),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        status_cb(f"[Gemini] paper draft written to {paper_path}; handing off to Codex repair.")
        return execution

    def _build_prompt(
        self,
        *,
        context: AgentContext,
        plan: ResearchPlan,
        phase: PhaseSpec,
        metadata: dict[str, object],
        verification_report: ValidationReport,
        analysis_report: ValidationReport,
    ) -> str:
        payload = {
            "workspace": str(context.workspace),
            "plan_heading": phase.heading,
            "plan_preface": plan.preface,
            "plan_body": phase.body,
            "metadata": metadata,
            "verification_report": {
                "success": verification_report.success,
                "checks": verification_report.checks,
                "failures": verification_report.failures,
                "artifact_checks": verification_report.artifact_checks,
            },
            "analysis_report": {
                "success": analysis_report.success,
                "checks": analysis_report.checks,
                "failures": analysis_report.failures,
                "artifact_checks": analysis_report.artifact_checks,
            },
            "last_feedback": context.last_feedback,
        }
        outline = textwrap.dedent(
            """
            Write a Typst paper draft using this outline:
            - Title page
            - Abstract
            - Introduction
            - Methods
            - Results
            - Discussion
            - Conclusion
            - References or placeholder references section

            Use the provided phase 3 plan content as the narrative guide.
            Reference only files and results that exist in the workspace.
            Focus on producing the manuscript content. Codex will perform the
            final Typst syntax repair pass after this draft is written.
            The document date must be `none`, not a formatted string.
            """
        ).strip()
        return outline + "\n\nContext JSON:\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    @staticmethod
    def _sanitize_typst_paper(text: str) -> str:
        lines = text.splitlines()
        normalized: list[str] = []
        inside_document = False
        document_depth = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#set document("):
                inside_document = True
                document_depth = stripped.count("(") - stripped.count(")")
                normalized.append(line)
                continue
            if inside_document:
                if "date:" in line:
                    indent = line[: len(line) - len(line.lstrip())]
                    normalized.append(f"{indent}date: none,")
                    continue
                document_depth += stripped.count("(") - stripped.count(")")
                if document_depth <= 0:
                    inside_document = False
            normalized.append(line)
        return "\n".join(normalized)


@dataclass
class TemplateExportExecution:
    template_root: Path
    draft_path: Path
    final_path: Path
    pdf_path: Path
    manifest_path: Path
    bibliography_path: str
    section_titles: list[str] = field(default_factory=list)


class PaperTemplateExporter:
    def export(
        self,
        *,
        context: AgentContext,
        plan: ResearchPlan,
        phase: PhaseSpec,
        run_dir: Path,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> TemplateExportExecution:
        status_cb = status_cb or (lambda _message: None)
        run_dir.mkdir(parents=True, exist_ok=True)
        draft_path = context.workspace / "paper.typ"
        if not draft_path.exists():
            raise FileNotFoundError(f"Draft paper not found: {draft_path}")

        template_root = self._resolve_template_root(context.workspace)
        bibliography_path = self._resolve_bibliography_path(context.workspace, template_root)
        metadata = _load_metadata(context.metadata_path)
        draft_text = draft_path.read_text(encoding="utf-8")
        sections = self._split_heading_sections(draft_text)
        if not sections:
            raise RuntimeError("paper.typ does not contain any top-level sections to export.")

        abstract_text, body_sections, abstract_found = self._partition_draft_sections(sections)
        if not abstract_found:
            status_cb(
                "[TemplateExport] Draft has no explicit Abstract heading; synthesizing a fallback abstract from the manuscript content."
            )
            abstract_text = self._fallback_abstract(body_sections)
        if not abstract_text.strip():
            raise RuntimeError("paper.typ does not contain enough content to synthesize an abstract for template export.")

        final_path = context.workspace / "paper_final.typ"
        final_text = self._compose_document(
            metadata=metadata,
            template_root=template_root,
            workspace=context.workspace,
            bibliography_path=bibliography_path,
            abstract_text=abstract_text,
            body_sections=body_sections,
        )
        final_path.write_text(final_text.rstrip() + "\n", encoding="utf-8")

        manifest_path = run_dir / "template_export_manifest.json"
        manifest = {
            "workspace": str(context.workspace),
            "plan_heading": phase.heading,
            "template_root": str(template_root),
            "draft_path": str(draft_path),
            "final_path": str(final_path),
            "pdf_path": str(context.workspace / "paper.pdf"),
            "bibliography_path": bibliography_path,
            "title": str(metadata.get("title", DEFAULT_METADATA["title"])),
            "authors": self._normalize_list(metadata.get("authors")) or list(DEFAULT_METADATA["authors"]),
            "keywords": self._normalize_list(metadata.get("keywords")),
            "section_titles": [title for title, _ in body_sections],
        }
        _json_dump_atomic(manifest_path, manifest)
        status_cb(f"[TemplateExport] template root: {template_root}")
        status_cb(f"[TemplateExport] final Typst written to {final_path}")
        status_cb(f"[TemplateExport] manifest written to {manifest_path}")
        return TemplateExportExecution(
            template_root=template_root,
            draft_path=draft_path,
            final_path=final_path,
            pdf_path=context.workspace / "paper.pdf",
            manifest_path=manifest_path,
            bibliography_path=bibliography_path,
            section_titles=[title for title, _ in body_sections],
        )

    def _resolve_template_root(self, workspace: Path) -> Path:
        candidates = [
            workspace / "template" / "jrip",
            workspace / "template" / "industrial-vision",
            workspace / "template" / "clear-iclr",
            workspace / "paper-template" / "jrip",
            workspace / "paper-template" / "industrial-vision",
            workspace / "paper-template" / "clear-iclr",
        ]
        for candidate in candidates:
            if candidate.exists() and (candidate / "logo.typ").exists() and (candidate / "main.typ").exists():
                return candidate
        raise FileNotFoundError(
            f"Could not find a Typst template directory in {workspace}."
        )

    def _resolve_bibliography_path(self, workspace: Path, template_root: Path) -> str:
        workspace_bib = workspace / "references.bib"
        if workspace_bib.exists():
            return _safe_relpath(workspace_bib, workspace)
        template_bib = template_root / "main.bib"
        if template_bib.exists():
            return _safe_relpath(template_bib, workspace)
        raise FileNotFoundError("Could not find references.bib or template main.bib for template export.")

    @staticmethod
    def _split_sections(text: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        current_title: Optional[str] = None
        current_lines: list[str] = []
        for line in text.splitlines():
            match = re.match(r"^\s*=\s+(.+?)\s*$", line)
            if match:
                if current_title is not None:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                current_title = match.group(1).strip()
                current_lines = []
                continue
            current_lines.append(line)
        if current_title is not None:
            sections.append((current_title, "\n".join(current_lines).strip()))
        return sections

    @staticmethod
    def _split_heading_sections(text: str) -> list[tuple[int, str, str]]:
        sections: list[tuple[int, str, str]] = []
        current_level: Optional[int] = None
        current_title: Optional[str] = None
        current_lines: list[str] = []
        for line in text.splitlines():
            match = re.match(r"^(=+)\s+(.+?)\s*$", line)
            if match:
                level = len(match.group(1))
                if current_title is not None:
                    sections.append((current_level or level, current_title, "\n".join(current_lines).strip()))
                current_level = level
                current_title = match.group(2).strip()
                current_lines = []
                continue
            current_lines.append(line)
        if current_title is not None:
            sections.append((current_level or 1, current_title, "\n".join(current_lines).strip()))
        return sections

    @classmethod
    def _partition_draft_sections(
        cls,
        sections: list[tuple[int, str, str]],
    ) -> tuple[str, list[tuple[str, str]], bool]:
        abstract_text = ""
        abstract_found = False
        body_sections: list[tuple[str, str]] = []
        for index, (level, title, body) in enumerate(sections):
            cleaned_title = title.strip()
            cleaned_body = body.strip()
            if index == 0 and level == 1:
                continue
            if cleaned_title.lower() == "abstract":
                abstract_found = True
                if not abstract_text:
                    abstract_text = cleaned_body
                continue
            if cleaned_body:
                body_sections.append((cleaned_title, cleaned_body))
        return abstract_text, body_sections, abstract_found

    @staticmethod
    def _fallback_abstract(body_sections: list[tuple[str, str]], max_words: int = 180) -> str:
        for _title, body in body_sections:
            snippet = " ".join(body.split()).strip()
            if snippet:
                words = snippet.split()
                if len(words) > max_words:
                    return " ".join(words[:max_words]).rstrip() + " ..."
                return snippet
        return ""

    def _compose_document(
        self,
        *,
        metadata: dict[str, object],
        template_root: Path,
        workspace: Path,
        bibliography_path: str,
        abstract_text: str,
        body_sections: list[tuple[str, str]],
    ) -> str:
        title = str(metadata.get("title") or DEFAULT_METADATA["title"])
        authors = self._render_authors(metadata)
        keywords = self._render_keywords(metadata)
        logo_import = _safe_relpath(template_root / "logo.typ", workspace).replace("\\", "/")
        body_text = self._render_body(body_sections)
        if not abstract_text.strip():
            abstract_text = self._fallback_abstract(body_sections)
        parts = [
            f'#import "{logo_import}": LaTeX, LaTeXe',
            '#import "@preview/clear-iclr:0.7.0": iclr2025',
            "",
            "#show: iclr2025.with(",
            f"  title: [#text({json.dumps(title)})],",
            f"  authors: {authors},",
            f"  keywords: {keywords},",
            "  abstract: [",
            self._indent_block(abstract_text),
            "  ],",
            f"  bibliography: bibliography({json.dumps(bibliography_path)}),",
            "  appendix: [],",
            "  accepted: false,",
            ")",
            "",
        ]
        if body_text:
            parts.append(body_text.rstrip())
            parts.append("")
        parts.append(f"#bibliography({json.dumps(bibliography_path)}, title: \"References\")")
        return "\n".join(parts).rstrip() + "\n"

    def _render_authors(self, metadata: dict[str, object]) -> str:
        names = self._normalize_list(metadata.get("authors"))
        if not names:
            names = list(DEFAULT_METADATA["authors"])
        name_entries = ", ".join(f"[#text({json.dumps(name)})]" for name in names)
        affiliation = self._pick_affiliation(metadata)
        address = self._pick_address(metadata)
        email = self._pick_email(metadata)
        return textwrap.dedent(
            f"""(
  (
    names: ({name_entries}),
    affilation: [#text({json.dumps(affiliation)})],
    address: [#text({json.dumps(address)})],
    email: {json.dumps(email)},
  ),
)"""
        ).strip()

    def _render_keywords(self, metadata: dict[str, object]) -> str:
        keywords = self._normalize_list(metadata.get("keywords"))
        if not keywords:
            return "()"
        return "(" + ", ".join(f"#text({json.dumps(item)})" for item in keywords) + ")"

    def _render_body(self, sections: list[tuple[str, str]]) -> str:
        rendered: list[str] = []
        for title, body in sections:
            if title.strip().lower() == "abstract":
                continue
            body_text = body.strip()
            if body_text:
                rendered.append(f"= {title}\n\n{body_text}")
            else:
                rendered.append(f"= {title}")
        return "\n\n".join(rendered).strip()

    @staticmethod
    def _indent_block(text: str, indent: int = 4) -> str:
        prefix = " " * indent
        lines = text.strip().splitlines()
        if not lines:
            return prefix + "#text(\"Abstract unavailable.\")"
        return "\n".join(f"{prefix}{line}" if line.strip() else "" for line in lines)

    @staticmethod
    def _pick_affiliation(metadata: dict[str, object]) -> str:
        value = metadata.get("affiliations") or metadata.get("affiliation") or metadata.get("venue")
        items = PaperTemplateExporter._normalize_list(value)
        if items:
            return " / ".join(items)
        if value:
            return str(value)
        return "FluidAgent Pro Research Group"

    @staticmethod
    def _pick_address(metadata: dict[str, object]) -> str:
        value = metadata.get("address") or metadata.get("location") or metadata.get("venue")
        items = PaperTemplateExporter._normalize_list(value)
        if items:
            return " / ".join(items)
        if value:
            return str(value)
        return "Unknown address"

    @staticmethod
    def _pick_email(metadata: dict[str, object]) -> str:
        value = metadata.get("email")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "unknown@example.org"

    @staticmethod
    def _normalize_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return items
        if isinstance(value, tuple):
            items = [str(item).strip() for item in value if str(item).strip()]
            return items
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        return [str(value).strip()] if str(value).strip() else []


@dataclass
class StageReport:
    stage: WorkflowState
    attempt: int
    run_dir: Path
    prompt_path: Path
    report_path: Path
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


class FluidAgentPro:
    def __init__(
        self,
        *,
        workspace: Path,
        auto_approve: Optional[bool] = None,
        force_stdio: bool = False,
        dry_run: bool = False,
        clear: bool = False,
        clear_hard: bool = False,
        purge_install: bool = False,
        codex_model: Optional[str] = None,
        gemini_model: Optional[str] = None,
        max_stage_attempts: int = DEFAULT_STAGE_ATTEMPTS,
        codex_timeout: int = DEFAULT_CODEX_TIMEOUT,
        gemini_timeout: int = DEFAULT_GEMINI_TIMEOUT,
    ) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.dry_run = dry_run
        self.clear_requested = clear or clear_hard
        self.clear_hard_requested = clear_hard
        self.clear_purge_install_requested = purge_install
        self.max_stage_attempts = max_stage_attempts
        self.plan_parser = PlanParser()
        self.toolchain_checker = ToolchainChecker()
        self.review_cli = HumanReviewCLI(auto_approve=auto_approve, force_stdio=force_stdio)
        self.codex_runner = CodexRunner(model=codex_model, timeout_seconds=codex_timeout)
        self.validation_runner = ValidationRunner()
        self.gemini_client = GeminiClient(model=gemini_model, timeout_seconds=gemini_timeout)
        self.paper_writer = PaperWriter(self.gemini_client)
        self.paper_template_exporter = PaperTemplateExporter()
        self.context: Optional[AgentContext] = None
        self.plan: Optional[ResearchPlan] = None
        self.metadata: dict[str, object] = {}

    def bootstrap(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        for subdir in DEFAULT_SUBDIRS:
            (self.workspace / subdir).mkdir(parents=True, exist_ok=True)

        plan_path = self.plan_parser.resolve_plan_path(self.workspace)
        plan = self.plan_parser.parse(plan_path)
        metadata_path = self.workspace / "metadata.json"
        metadata = _load_metadata(metadata_path)
        phase_zero = plan.phase_by_label("Phase 0")
        if phase_zero is None:
            raise RuntimeError("research_plan.md is missing Phase 0: Environment Setup.")
        phase_zero_report = self.toolchain_checker.check(
            phase=phase_zero,
            workspace=self.workspace,
            log_dir=self.workspace / "logs",
            status_cb=self.review_cli.print_status,
        )
        if not phase_zero_report.success:
            failure_text = "\n".join(f"- {item}" for item in phase_zero_report.failures)
            raise RuntimeError(f"Phase 0 environment check failed. Fix the missing tools before starting Codex.\n{failure_text}")
        state_path = self.workspace / ".agent_state.json"
        current_plan_checksum = _sha256_file(plan_path)

        context = AgentContext(
            workspace=self.workspace,
            state_path=state_path,
            plan_path=plan_path,
            metadata_path=metadata_path,
            plan_checksum=current_plan_checksum,
        )
        context.load()
        saved_plan_checksum = context.plan_checksum
        if not saved_plan_checksum:
            context.plan_checksum = current_plan_checksum
        elif saved_plan_checksum != current_plan_checksum:
            self.review_cli.print_status("Plan file changed since the last run; resetting workflow state.")
            context.state = WorkflowState.INIT
            context.previous_state = None
            context.last_feedback = ""
            context.artifacts = {}
            context.phase_attempts = {}
            context.consultations = []
            context.plan_checksum = current_plan_checksum

        context.artifacts.setdefault("workspace", str(self.workspace))
        context.artifacts.setdefault("plan_path", str(plan_path))
        context.artifacts.setdefault("metadata_path", str(metadata_path))
        context.artifacts.setdefault("plan_checksum", context.plan_checksum)
        context.artifacts.setdefault("phase0_environment_report", str(phase_zero_report.report_path or self.workspace / "logs" / "phase0_environment_check.json"))
        context.save()

        self.context = context
        self.plan = plan
        self.metadata = metadata

        self.review_cli.print_status(f"[Bootstrap] Workspace ready: {self.workspace}")
        self.review_cli.print_status(f"[Bootstrap] Plan path: {plan_path}")
        self.review_cli.print_status(f"[Bootstrap] Phases detected: {len(plan.phases)}")
        self.review_cli.print_status(f"[Bootstrap] Resume state: {context.state.value}")
        for phase in plan.phases:
            self.review_cli.print_status(f"[Bootstrap] {phase.heading}")
            if phase.artifact_hints:
                self.review_cli.print_status(f"[Bootstrap]   Artifacts: {', '.join(phase.artifact_hints)}")

    def _clear_generated_workspace(self, *, include_src: bool = False, purge_install: bool = False) -> None:
        self._reset_generated_workspace(hard=include_src, clear_all=True, purge_install=purge_install)

    def _reset_generated_workspace(
        self,
        *,
        hard: bool = False,
        clear_all: bool = False,
        purge_install: bool = False,
        preserve_state: bool = False,
    ) -> None:
        preserve_names = {
            "fluid_agent_pro.py",
            "readme.md",
            "metadata.json",
            "references.bib",
            "ghiau.u.txt",
            "ghiav.v.txt",
            "research_plan.md",
        }
        targets: list[Path] = []
        for name in RESET_TOP_LEVEL_FILES:
            if preserve_state and name == ".agent_state.json":
                continue
            targets.append(self.workspace / name)
        for name in RESET_TOP_LEVEL_DIRS:
            targets.append(self.workspace / name)
        if hard:
            for name in RESET_HARD_TOP_LEVEL_DIRS:
                targets.append(self.workspace / name)
        if clear_all:
            for name in CLEAR_TOP_LEVEL_FILES:
                targets.append(self.workspace / name)
            for name in CLEAR_TOP_LEVEL_DIRS:
                targets.append(self.workspace / name)
            for pattern in CLEAR_TOP_LEVEL_GLOBS:
                targets.extend(self.workspace.glob(pattern))
        if purge_install:
            for name in CLEAR_INSTALL_TOP_LEVEL_DIRS:
                targets.append(self.workspace / name)
            for pattern in CLEAR_INSTALL_TOP_LEVEL_GLOBS:
                targets.extend(self.workspace.glob(pattern))

        state_path = self.workspace / ".agent_state.json"
        if not preserve_state:
            saved_state = _json_load(state_path, {})
            if isinstance(saved_state, dict):
                artifacts = saved_state.get("artifacts", {})
                if isinstance(artifacts, dict):
                    for value in artifacts.values():
                        candidate = self._path_within_workspace(value)
                        if candidate is not None:
                            targets.append(candidate)
        elif clear_all:
            # Even when preserving the state file, we still want to clear the generated paths
            # recorded there so the next stage does not inherit stale outputs.
            saved_state = _json_load(state_path, {})
            if isinstance(saved_state, dict):
                artifacts = saved_state.get("artifacts", {})
                if isinstance(artifacts, dict):
                    for key, value in artifacts.items():
                        if key in {"workspace", "plan_path", "metadata_path", "plan_checksum"}:
                            continue
                        candidate = self._path_within_workspace(value)
                        if candidate is not None:
                            targets.append(candidate)

        unique_targets: list[Path] = []
        seen: set[str] = set()
        for target in targets:
            resolved = target.resolve(strict=False)
            if resolved == self.workspace:
                continue
            if resolved.name in preserve_names or _strip_invisible_marks(resolved.name) == "research_plan.md":
                continue
            if not hard:
                try:
                    resolved.relative_to(self.workspace / "src")
                except ValueError:
                    pass
                else:
                    continue
            if any(part in {"paper-template", "template"} for part in resolved.parts):
                continue
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            unique_targets.append(resolved)

        removed: list[str] = []
        for target in unique_targets:
            if _delete_path(target):
                removed.append(_safe_relpath(target, self.workspace))

        if removed:
            action = "Clear" if clear_all else "Reset"
            self.review_cli.print_status(f"[{action}] Removed generated paths:")
            for item in removed:
                self.review_cli.print_status(f"[{action}]   {item}")

    def _path_within_workspace(self, value: object) -> Optional[Path]:
        if not isinstance(value, str) or not value.strip():
            return None
        candidate = Path(value.strip())
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self.workspace)
        except ValueError:
            return None
        return resolved

    def run(self) -> None:
        if self.clear_requested:
            self.workspace.mkdir(parents=True, exist_ok=True)
            clear_mode = "hard" if self.clear_hard_requested else "soft"
            include_src = "including src/" if self.clear_hard_requested else "without src/"
            include_install = "purging editable-install files" if self.clear_purge_install_requested else "keeping editable-install files"
            self.review_cli.print_status(
                f"[Bootstrap] Clear requested ({clear_mode}, {include_src}, {include_install}); removing generated workspace outputs."
            )
            self._clear_generated_workspace(include_src=self.clear_hard_requested, purge_install=self.clear_purge_install_requested)
            self.review_cli.print_status("[FSM] Clear completed.")
            return
        if self.context is None or self.plan is None:
            self.bootstrap()
        assert self.context is not None
        assert self.plan is not None

        while True:
            state = self.context.state
            if state == WorkflowState.DONE:
                self.context.save()
                final_pdf = self.context.artifacts.get("paper_pdf", str(self.workspace / "paper.pdf"))
                final_source = self.context.artifacts.get("paper_final_typ", self.context.artifacts.get("paper_typ", str(self.workspace / "paper.typ")))
                self.review_cli.print_status(f"[FSM] Workflow finished. Final source: {final_source}; PDF: {final_pdf}")
                return
            if state == WorkflowState.ERROR:
                self.context.save()
                self.review_cli.print_status("[FSM] Workflow ended in error.")
                return

            if state == WorkflowState.INIT:
                self.review_cli.print_status("[FSM] STATE_INIT -> STATE_CODING_VERIFY")
                self.context.transition_to(WorkflowState.CODING_VERIFY)
                self.context.save()
                continue

            if state == WorkflowState.CODING_VERIFY:
                self._run_codex_stage(
                    state=state,
                    next_wait_state=WorkflowState.WAIT_VERIFY_REVIEW,
                    next_active_state=WorkflowState.DATA_ANALYSIS,
                    stage_goal="Implement the Phase 1 code and verification artifacts.",
                )
                continue

            if state == WorkflowState.WAIT_VERIFY_REVIEW:
                decision = self._prompt_review(state)
                if decision.quit_requested:
                    self.context.save()
                    return
                if decision.consult_requested:
                    self.review_cli.print_status("[FSM] Review consultation requested; staying in STATE_WAIT_VERIFY_REVIEW")
                    self._run_review_consult(state=state, question=decision.question)
                    continue
                if decision.approved:
                    self.review_cli.print_status("[FSM] Review approved -> STATE_DATA_ANALYSIS")
                    self.context.last_feedback = ""
                    self.context.transition_to(WorkflowState.DATA_ANALYSIS)
                    self.context.save()
                    continue
                self.review_cli.print_status("[FSM] Review rejected -> rollback to STATE_CODING_VERIFY")
                self.context.last_feedback = decision.feedback
                self.context.rollback()
                self.context.save()
                continue

            if state == WorkflowState.DATA_ANALYSIS:
                self._run_codex_stage(
                    state=state,
                    next_wait_state=WorkflowState.WAIT_ANALYSIS_REVIEW,
                    next_active_state=WorkflowState.PAPER_WRITING,
                    stage_goal="Implement the Phase 2 data analysis and comparison artifacts.",
                )
                continue

            if state == WorkflowState.WAIT_ANALYSIS_REVIEW:
                decision = self._prompt_review(state)
                if decision.quit_requested:
                    self.context.save()
                    return
                if decision.consult_requested:
                    self.review_cli.print_status("[FSM] Review consultation requested; staying in STATE_WAIT_ANALYSIS_REVIEW")
                    self._run_review_consult(state=state, question=decision.question)
                    continue
                if decision.rewind_requested:
                    self.review_cli.print_status("[FSM] Analysis review requested rewind -> STATE_CODING_VERIFY")
                    self._rewind_to_phase_one(source_state=state, reason=decision.feedback)
                    continue
                if decision.approved:
                    self.review_cli.print_status("[FSM] Review approved -> STATE_PAPER_WRITING")
                    self.context.last_feedback = ""
                    self.context.transition_to(WorkflowState.PAPER_WRITING)
                    self.context.save()
                    continue
                self.review_cli.print_status("[FSM] Review rejected -> rollback to STATE_DATA_ANALYSIS")
                self.context.last_feedback = decision.feedback
                self.context.rollback()
                self.context.save()
                continue

            if state == WorkflowState.WAIT_PAPER_REVIEW:
                decision = self._prompt_review(state)
                if decision.quit_requested:
                    self.context.save()
                    return
                if decision.consult_requested:
                    self.review_cli.print_status("[FSM] Paper repair consultation requested; staying in STATE_WAIT_PAPER_REVIEW")
                    self._run_review_consult(state=state, question=decision.question)
                    continue
                if decision.rewind_requested:
                    self.review_cli.print_status("[FSM] Paper review requested rewind -> STATE_DATA_ANALYSIS")
                    self._rewind_to_phase_two(source_state=state, reason=decision.feedback)
                    continue
                if decision.approved:
                    self.review_cli.print_status("[FSM] Paper repair approved -> STATE_PAPER_FIX")
                    self.context.transition_to(WorkflowState.PAPER_FIX)
                    self.context.save()
                    continue
                if decision.feedback:
                    self.review_cli.print_status("[FSM] Paper repair guidance captured -> STATE_PAPER_FIX")
                    merged_feedback = decision.feedback.strip()
                    if self.context.last_feedback.strip():
                        merged_feedback = f"{merged_feedback}\n\nPrevious validation details:\n{self.context.last_feedback.strip()}"
                    self.context.last_feedback = merged_feedback.strip() + "\n"
                else:
                    self.review_cli.print_status("[FSM] Paper repair guidance empty; reusing existing validation feedback.")
                self.context.transition_to(WorkflowState.PAPER_FIX)
                self.context.save()
                continue

            if state == WorkflowState.PAPER_TEMPLATE_EXPORT:
                self.review_cli.print_status("[FSM] STATE_PAPER_TEMPLATE_EXPORT -> template export")
                self._run_paper_template_export_stage()
                continue

            if state == WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW:
                decision = self._prompt_review(state)
                if decision.quit_requested:
                    self.context.save()
                    return
                if decision.consult_requested:
                    self.review_cli.print_status("[FSM] Template export consultation requested; staying in STATE_WAIT_PAPER_TEMPLATE_REVIEW")
                    self._run_review_consult(state=state, question=decision.question)
                    continue
                if decision.rewind_requested:
                    self.review_cli.print_status("[FSM] Template export requested rewind -> STATE_DATA_ANALYSIS")
                    self._rewind_to_phase_two(source_state=state, reason=decision.feedback)
                    continue
                if decision.approved:
                    self.review_cli.print_status("[FSM] Template export approved -> STATE_PAPER_TEMPLATE_EXPORT")
                    self.context.transition_to(WorkflowState.PAPER_TEMPLATE_EXPORT)
                    self.context.save()
                    continue
                self.review_cli.print_status("[FSM] Template export guidance captured -> STATE_PAPER_TEMPLATE_EXPORT")
                if decision.feedback:
                    merged_feedback = decision.feedback.strip()
                    if self.context.last_feedback.strip():
                        merged_feedback = f"{merged_feedback}\n\nPrevious validation details:\n{self.context.last_feedback.strip()}"
                    self.context.last_feedback = merged_feedback.strip() + "\n"
                self.context.transition_to(WorkflowState.PAPER_TEMPLATE_EXPORT)
                self.context.save()
                continue

            if state == WorkflowState.PAPER_WRITING:
                self.review_cli.print_status("[FSM] STATE_PAPER_WRITING -> Gemini draft")
                self._run_paper_stage()
                continue

            if state == WorkflowState.PAPER_FIX:
                self.review_cli.print_status("[FSM] STATE_PAPER_FIX -> Codex repair")
                self._run_paper_fix_stage()
                continue

            raise RuntimeError(f"Unsupported state: {state.value}")

    def _run_codex_stage(
        self,
        *,
        state: WorkflowState,
        next_wait_state: WorkflowState,
        next_active_state: WorkflowState,
        stage_goal: str,
    ) -> None:
        assert self.context is not None
        assert self.plan is not None
        phase = self.plan.phase_for_state(state)
        attempt = self.context.bump_attempt(state)
        if attempt > self.max_stage_attempts:
            self._enter_error(f"Exceeded max attempts for {state.value}")
            return

        run_dir = self.workspace / "runs" / state.value / f"{_now_stamp()}_attempt{attempt}"
        prompt = self.plan_parser.build_codex_prompt(
            plan=self.plan,
            phase=phase,
            state=state,
            workspace=self.workspace,
            context=self.context,
            stage_goal=stage_goal,
        )
        prompt_path = run_dir / "prompt.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        current_task = self.workspace / "current_task.txt"
        current_task.write_text(prompt, encoding="utf-8")
        self.review_cli.print_status(f"[{state.value}] Phase: {phase.heading}")
        self.review_cli.print_status(f"[{state.value}] Goal: {stage_goal}")
        self.review_cli.print_status(f"[{state.value}] Attempt: {attempt}")
        self.review_cli.print_status(f"[{state.value}] Prompt: {prompt_path}")
        self.review_cli.print_status(f"[{state.value}] Current task: {current_task}")
        if phase.commands:
            self.review_cli.print_status(f"[{state.value}] Plan commands: {len(phase.commands)}")
            for index, command in enumerate(phase.commands, start=1):
                self.review_cli.print_status(f"[{state.value}]   cmd {index}: {_shorten_text(command, 180)}")
        if phase.artifact_hints:
            self.review_cli.print_status(f"[{state.value}] Expected artifacts: {', '.join(phase.artifact_hints)}")
        self.review_cli.print_status(f"[{state.value}] launching Codex attempt {attempt} in {run_dir}")

        if self.dry_run:
            self.review_cli.print_status(f"[dry-run] Would run Codex for {state.value} -> {next_wait_state.value}")
            self.review_cli.print_status(f"[dry-run] Validation hints: {phase.artifact_hints or ['(none)']}")
            return

        codex = self.codex_runner.run_with_status(
            workspace=self.workspace,
            prompt=prompt,
            run_dir=run_dir,
            status_cb=self.review_cli.print_status,
        )
        self.review_cli.print_status(f"[{state.value}] Codex finished with rc={codex.returncode}; validating output.")
        validation = self.validation_runner.validate(
            state=state,
            phase=phase,
            workspace=self.workspace,
            run_dir=run_dir,
            status_cb=self.review_cli.print_status,
        )
        stage_report = self._write_stage_report(
            state=state,
            attempt=attempt,
            run_dir=run_dir,
            prompt_path=prompt_path,
            codex=codex,
            validation=validation,
        )

        self.context.artifacts.update(
            {
                f"{state.value.lower()}_run_dir": str(run_dir),
                f"{state.value.lower()}_report": str(stage_report.report_path),
                f"{state.value.lower()}_validation": str(validation.report_path) if validation.report_path else "",
            }
        )

        if codex.returncode == 0 and validation.success:
            self.context.last_feedback = ""
            self.context.transition_to(next_wait_state)
            self.context.save()
            summary = f"{state.value} passed validation; awaiting human review."
            self.review_cli.print_status(summary)
            return

        feedback = self._compose_retry_feedback(state=state, codex=codex, validation=validation)
        self.context.last_feedback = feedback
        self.context.save()
        self.review_cli.print_status(f"{state.value} failed validation; retrying with feedback.")
        self._run_codex_stage(
            state=state,
            next_wait_state=next_wait_state,
            next_active_state=next_active_state,
            stage_goal=stage_goal,
        )

    def _run_paper_stage(self) -> None:
        assert self.context is not None
        assert self.plan is not None
        phase = self.plan.phase_for_state(WorkflowState.PAPER_WRITING)
        attempt = self.context.bump_attempt(WorkflowState.PAPER_WRITING)

        run_dir = self.workspace / "runs" / WorkflowState.PAPER_WRITING.value / f"{_now_stamp()}_attempt{attempt}"
        verification_phase = self.plan.phase_for_state(WorkflowState.CODING_VERIFY)
        analysis_phase = self.plan.phase_for_state(WorkflowState.DATA_ANALYSIS)
        verification_report = self._load_latest_validation_report(verification_phase, WorkflowState.CODING_VERIFY)
        analysis_report = self._load_latest_validation_report(analysis_phase, WorkflowState.DATA_ANALYSIS)
        self.review_cli.print_status(f"[{WorkflowState.PAPER_WRITING.value}] Phase: {phase.heading}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_WRITING.value}] Attempt: {attempt}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_WRITING.value}] Using verification report: {verification_report.report_path or '(missing)'}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_WRITING.value}] Using analysis report: {analysis_report.report_path or '(missing)'}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_WRITING.value}] launching Gemini attempt {attempt} in {run_dir}")

        if self.dry_run:
            self.review_cli.print_status("[dry-run] Would call Gemini to write paper.typ")
            return

        execution = self.paper_writer.write(
            context=self.context,
            plan=self.plan,
            phase=phase,
            verification_report=verification_report,
            analysis_report=analysis_report,
            run_dir=run_dir,
            status_cb=self.review_cli.print_status,
        )
        self.context.artifacts.update(
            {
                "paper_draft_run_dir": str(run_dir),
                "paper_draft_request": str(execution.request_path),
                "paper_draft_response": str(execution.response_path),
                "paper_draft_raw_response": str(execution.raw_response_path),
                "paper_typ": str(self.workspace / "paper.typ"),
            }
        )
        current_task = self.workspace / "current_task.txt"
        current_task.write_text(
            "\n".join(
                [
                    "Gemini paper draft generated.",
                    f"State: {WorkflowState.PAPER_WRITING.value}",
                    f"Run directory: {run_dir}",
                    "Next action: Codex will perform Typst syntax repair and final validation.",
                    "",
                    "The draft has been handed off to the paper repair stage.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.context.transition_to(WorkflowState.PAPER_FIX)
        self.context.save()
        self.review_cli.print_status("paper.typ draft written; handing off to Codex repair stage.")

    def _run_paper_fix_stage(self) -> None:
        assert self.context is not None
        assert self.plan is not None
        phase = self.plan.phase_for_state(WorkflowState.PAPER_FIX)
        attempt = self.context.bump_attempt(WorkflowState.PAPER_FIX)

        run_dir = self.workspace / "runs" / WorkflowState.PAPER_FIX.value / f"{_now_stamp()}_attempt{attempt}"
        verification_phase = self.plan.phase_for_state(WorkflowState.CODING_VERIFY)
        analysis_phase = self.plan.phase_for_state(WorkflowState.DATA_ANALYSIS)
        verification_report = self._load_latest_validation_report(verification_phase, WorkflowState.CODING_VERIFY)
        analysis_report = self._load_latest_validation_report(analysis_phase, WorkflowState.DATA_ANALYSIS)
        draft_execution = self._load_paper_draft_execution()
        self.review_cli.print_status(f"[{WorkflowState.PAPER_FIX.value}] Phase: {phase.heading}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_FIX.value}] Attempt: {attempt}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_FIX.value}] Gemini draft: {draft_execution.response_path or '(missing)'}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_FIX.value}] Using verification report: {verification_report.report_path or '(missing)'}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_FIX.value}] Using analysis report: {analysis_report.report_path or '(missing)'}")

        stage_goal = (
            "Gemini has already generated the Typst paper draft. "
            "Run final Typst syntax checking on paper.typ, repair compilation, structure, "
            "or reference issues in place, and preserve the content as much as possible. "
            "Do not call Gemini again."
        )
        prompt = self.plan_parser.build_codex_prompt(
            plan=self.plan,
            phase=phase,
            state=WorkflowState.PAPER_FIX,
            workspace=self.workspace,
            context=self.context,
            stage_goal=stage_goal,
        )
        prompt_path = run_dir / "prompt.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        current_task = self.workspace / "current_task.txt"
        current_task.write_text(prompt, encoding="utf-8")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_FIX.value}] launching Codex repair attempt {attempt} in {run_dir}")

        if self.dry_run:
            self.review_cli.print_status(f"[dry-run] Would run Codex repair for {WorkflowState.PAPER_FIX.value}")
            return

        codex = self.codex_runner.run_with_status(
            workspace=self.workspace,
            prompt=prompt,
            run_dir=run_dir,
            status_cb=self.review_cli.print_status,
        )
        self.review_cli.print_status(f"[{WorkflowState.PAPER_FIX.value}] Codex finished with rc={codex.returncode}; validating output.")
        validation = self.validation_runner.validate(
            state=WorkflowState.PAPER_FIX,
            phase=phase,
            workspace=self.workspace,
            run_dir=run_dir,
            status_cb=self.review_cli.print_status,
        )
        report = self._write_paper_report(
            run_dir=run_dir,
            phase=phase,
            gemini_execution=draft_execution,
            codex=codex,
            validation=validation,
        )
        self.context.artifacts.update(
            {
                "paper_fix_run_dir": str(run_dir),
                "paper_fix_report": str(report.report_path),
                "paper_fix_validation": str(validation.report_path) if validation.report_path else "",
                "paper_report": str(report.report_path),
                "paper_typ": str(self.workspace / "paper.typ"),
            }
        )
        if codex.returncode == 0 and validation.success:
            self.context.last_feedback = ""
            self.context.transition_to(WorkflowState.PAPER_TEMPLATE_EXPORT)
            self.context.save()
            self.review_cli.print_status("paper.typ repaired successfully; moving to template export.")
            return

        feedback_parts = self._compose_retry_feedback(state=WorkflowState.PAPER_FIX, codex=codex, validation=validation)
        self.context.last_feedback = feedback_parts
        current_task.write_text(
            "\n".join(
                [
                    "Paper repair failed.",
                    f"State: {WorkflowState.PAPER_FIX.value}",
                    f"Run directory: {run_dir}",
                    "Next action: review the failure details below, then continue repair with Y or provide guidance with N.",
                    "",
                    self.context.last_feedback.rstrip(),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.context.transition_to(WorkflowState.WAIT_PAPER_REVIEW)
        self.context.save()
        self.review_cli.print_status("Paper repair failed; awaiting user guidance.")

    def _run_paper_template_export_stage(self) -> None:
        assert self.context is not None
        assert self.plan is not None
        phase = self.plan.phase_for_state(WorkflowState.PAPER_TEMPLATE_EXPORT)
        attempt = self.context.bump_attempt(WorkflowState.PAPER_TEMPLATE_EXPORT)

        run_dir = self.workspace / "runs" / WorkflowState.PAPER_TEMPLATE_EXPORT.value / f"{_now_stamp()}_attempt{attempt}"
        draft_path = self.workspace / "paper.typ"
        self.review_cli.print_status(f"[{WorkflowState.PAPER_TEMPLATE_EXPORT.value}] Phase: {phase.heading}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_TEMPLATE_EXPORT.value}] Attempt: {attempt}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_TEMPLATE_EXPORT.value}] Draft source: {draft_path}")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_TEMPLATE_EXPORT.value}] Final source: {self.workspace / 'paper_final.typ'}")
        try:
            template_root = self.paper_template_exporter._resolve_template_root(self.workspace)
            bibliography_path = self.paper_template_exporter._resolve_bibliography_path(self.workspace, template_root)
            draft_text = draft_path.read_text(encoding="utf-8")
            sections = self.paper_template_exporter._split_heading_sections(draft_text)
            if not sections:
                raise RuntimeError("paper.typ does not contain any top-level sections to export.")
            abstract_text, body_sections, abstract_found = self.paper_template_exporter._partition_draft_sections(sections)
            if not abstract_found:
                self.review_cli.print_status(
                    "[TemplateExport] Draft has no explicit Abstract heading; Codex will synthesize a fallback abstract from the manuscript content."
                )
                abstract_text = self.paper_template_exporter._fallback_abstract(body_sections)
            if not abstract_text.strip():
                raise RuntimeError("paper.typ does not contain enough content to synthesize an abstract for template export.")
        except Exception as exc:
            feedback = f"Template export setup failed: {exc}"
            self.context.last_feedback = feedback + "\n"
            current_task = self.workspace / "current_task.txt"
            current_task.write_text(
                "\n".join(
                    [
                        "Paper template export failed before Codex handoff.",
                        f"State: {WorkflowState.PAPER_TEMPLATE_EXPORT.value}",
                        f"Run directory: {run_dir}",
                        f"Failure: {exc}",
                        "Next action: review the template export issue, then continue with Y or provide guidance with N.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.context.artifacts.update(
                {
                    "paper_template_run_dir": str(run_dir),
                    "paper_template_failure": str(exc),
                }
            )
            self.context.transition_to(WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW)
            self.context.save()
            self.review_cli.print_status("Paper template export setup failed; awaiting user guidance.")
            return

        final_path = self.workspace / "paper_final.typ"
        pdf_path = self.workspace / "paper.pdf"
        manifest_path = run_dir / "template_export_manifest.json"
        section_titles = [title for title, _ in body_sections]
        manifest = {
            "workspace": str(self.workspace),
            "draft_path": str(draft_path),
            "final_path": str(final_path),
            "pdf_path": str(pdf_path),
            "template_root": str(template_root),
            "bibliography_path": bibliography_path,
            "title": str(self.metadata.get("title", DEFAULT_METADATA["title"])),
            "section_titles": section_titles,
            "abstract_preview": _shorten_text(abstract_text, 300),
            "template_reference": str(template_root / "main.typ"),
            "body_preview": _shorten_text("\n\n".join(f"= {title}" for title in section_titles), 300),
        }
        _json_dump_atomic(manifest_path, manifest)
        self.context.artifacts.update(
            {
                "paper_template_run_dir": str(run_dir),
                "paper_template_root": str(template_root),
                "paper_template_manifest": str(manifest_path),
                "paper_template_typ": str(final_path),
                "paper_final_typ": str(final_path),
                "paper_pdf": str(pdf_path),
            }
        )
        self.context.save()

        stage_goal = (
            "Use the Typst template assets in the template directory to reorganize the repaired manuscript. "
            "Create paper_final.typ as the template-formatted manuscript, keep the scientific content unchanged, "
            "and compile paper.pdf from paper_final.typ. Do not call Gemini. Do not rewrite the paper from scratch."
        )
        prompt = self.plan_parser.build_codex_prompt(
            plan=self.plan,
            phase=phase,
            state=WorkflowState.PAPER_TEMPLATE_EXPORT,
            workspace=self.workspace,
            context=self.context,
            stage_goal=stage_goal,
        )
        prompt += textwrap.dedent(
            f"""

            Template export instructions:
            - Use the template root at: {template_root}
            - Treat {draft_path} as the content source of truth.
            - Create {final_path.name} in the workspace root.
            - Preserve the paper's factual content, figures, citations, and section order.
            - Use the clear-iclr template layout and keep the manuscript compileable.
            - If the source draft does not contain an explicit Abstract heading, synthesize a concise abstract from the manuscript content instead of aborting.
            - Compile the final template source to {pdf_path.name}.
            - If you need context, inspect {manifest_path}.
            """
        ).strip()
        manifest["abstract_found"] = abstract_found
        manifest["abstract_preview"] = _shorten_text(abstract_text, 300)
        prompt += "\n\nTemplate export manifest JSON:\n" + json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"

        prompt_path = run_dir / "prompt.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        current_task = self.workspace / "current_task.txt"
        current_task.write_text(prompt, encoding="utf-8")
        self.review_cli.print_status(f"[{WorkflowState.PAPER_TEMPLATE_EXPORT.value}] launching Codex template export attempt {attempt} in {run_dir}")

        if self.dry_run:
            self.review_cli.print_status(f"[dry-run] Would run Codex template export for {WorkflowState.PAPER_TEMPLATE_EXPORT.value}")
            return

        codex = self.codex_runner.run_with_status(
            workspace=self.workspace,
            prompt=prompt,
            run_dir=run_dir / "codex",
            status_cb=self.review_cli.print_status,
        )
        self.review_cli.print_status(f"[{WorkflowState.PAPER_TEMPLATE_EXPORT.value}] Codex finished with rc={codex.returncode}; validating output.")
        execution = TemplateExportExecution(
            template_root=template_root,
            draft_path=draft_path,
            final_path=final_path,
            pdf_path=pdf_path,
            manifest_path=manifest_path,
            bibliography_path=bibliography_path,
            section_titles=section_titles,
        )
        validation = self.validation_runner.validate(
            state=WorkflowState.PAPER_TEMPLATE_EXPORT,
            phase=phase,
            workspace=self.workspace,
            run_dir=run_dir,
            template_root=template_root,
            status_cb=self.review_cli.print_status,
        )
        report = self._write_template_export_report(
            run_dir=run_dir,
            phase=phase,
            export=execution,
            codex=codex,
            validation=validation,
        )
        self.context.artifacts.update(
            {
                "paper_template_run_dir": str(run_dir),
                "paper_template_report": str(report.report_path),
                "paper_template_validation": str(validation.report_path) if validation.report_path else "",
                "paper_report": str(report.report_path),
            }
        )
        if codex.returncode == 0 and validation.success:
            self.context.last_feedback = ""
            self.context.transition_to(WorkflowState.DONE)
            self.context.save()
            self.review_cli.print_status(f"Template export completed successfully: {final_path} -> {pdf_path}")
            return

        feedback_parts = self._compose_template_export_feedback(codex=codex, export=execution, validation=validation)
        self.context.last_feedback = feedback_parts
        current_task.write_text(
            "\n".join(
                [
                    "Paper template export failed.",
                    f"State: {WorkflowState.PAPER_TEMPLATE_EXPORT.value}",
                    f"Run directory: {run_dir}",
                    "Next action: review the failure details below, then continue export with Y or provide guidance with N.",
                    "",
                    self.context.last_feedback.rstrip(),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.context.transition_to(WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW)
        self.context.save()
        self.review_cli.print_status("Paper template export failed; awaiting user guidance.")

    def _prompt_review(self, state: WorkflowState) -> ReviewDecision:
        log_path = self._review_log_path(state)
        summary_lines = self._review_summary(state)
        if state == WorkflowState.WAIT_PAPER_REVIEW:
            return self.review_cli.prompt(
                state=state,
                log_path=log_path,
                summary_lines=summary_lines,
                prompt_text="Continue repair with Y, provide guidance with N, rewind to Phase 2 with B, consult Codex with C, or quit with Q: ",
                feedback_prompt="Describe the paper formatting or content issue to fix: ",
                rewind_feedback_prompt="Describe what should be revisited in Phase 2: ",
                allow_rewind=True,
                rewind_target_state=WorkflowState.DATA_ANALYSIS,
            )
        if state == WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW:
            return self.review_cli.prompt(
                state=state,
                log_path=log_path,
                summary_lines=summary_lines,
                prompt_text="Continue export with Y, provide guidance with N, rewind to Phase 2 with B, consult Codex with C, or quit with Q: ",
                feedback_prompt="Describe the template export issue to fix: ",
                rewind_feedback_prompt="Describe what should be revisited in Phase 2: ",
                allow_rewind=True,
                rewind_target_state=WorkflowState.DATA_ANALYSIS,
            )
        if state == WorkflowState.WAIT_ANALYSIS_REVIEW:
            return self.review_cli.prompt(
                state=state,
                log_path=log_path,
                summary_lines=summary_lines,
                prompt_text="Continue with Y, provide guidance with N, rewind to Phase 1 with P1/B, consult Codex with C, or quit with Q: ",
                feedback_prompt="Describe the analysis issue to fix: ",
                rewind_feedback_prompt="Describe why this should go back to Phase 1: ",
                allow_rewind=True,
                rewind_target_state=WorkflowState.CODING_VERIFY,
            )
        return self.review_cli.prompt(state=state, log_path=log_path, summary_lines=summary_lines)

    def _active_state_for_review(self, review_state: WorkflowState) -> WorkflowState:
        if review_state == WorkflowState.WAIT_VERIFY_REVIEW:
            return WorkflowState.CODING_VERIFY
        if review_state == WorkflowState.WAIT_ANALYSIS_REVIEW:
            return WorkflowState.DATA_ANALYSIS
        if review_state == WorkflowState.WAIT_PAPER_REVIEW:
            return WorkflowState.PAPER_FIX
        if review_state == WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW:
            return WorkflowState.PAPER_TEMPLATE_EXPORT
        raise KeyError(f"Unsupported review state: {review_state.value}")

    def _review_log_path(self, state: WorkflowState) -> Path:
        if state == WorkflowState.WAIT_VERIFY_REVIEW:
            report = self.context.artifacts.get("state_coding_verify_report")
            if report:
                return Path(report)
            return self.workspace / "runs" / WorkflowState.CODING_VERIFY.value
        if state == WorkflowState.WAIT_ANALYSIS_REVIEW:
            report = self.context.artifacts.get("state_data_analysis_report")
            if report:
                return Path(report)
            return self.workspace / "runs" / WorkflowState.DATA_ANALYSIS.value
        if state == WorkflowState.WAIT_PAPER_REVIEW:
            report = self.context.artifacts.get("paper_report") or self.context.artifacts.get("paper_fix_report")
            if report:
                return Path(report)
            return self.workspace / "runs" / WorkflowState.PAPER_FIX.value
        if state == WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW:
            report = self.context.artifacts.get("paper_template_report") or self.context.artifacts.get("paper_report")
            if report:
                return Path(report)
            return self.workspace / "runs" / WorkflowState.PAPER_TEMPLATE_EXPORT.value
        return self.workspace / "logs"

    def _review_summary(self, state: WorkflowState) -> list[str]:
        if state == WorkflowState.WAIT_VERIFY_REVIEW:
            phase = self.plan.phase_for_state(WorkflowState.CODING_VERIFY)
            artifact_lines = []
            for hint in phase.artifact_hints:
                resolved = self.validation_runner._resolve_artifact_hint(hint, self.workspace)
                artifact_lines.append(
                    f"Artifact: {resolved} ({'exists' if resolved.exists() else 'missing'})"
                )
            summary = [
                f"Verification report: {self.context.artifacts.get('state_coding_verify_report', '(missing)')}",
                f"Validation report: {self.context.artifacts.get('state_coding_verify_validation', '(missing)')}",
                *artifact_lines,
            ]
            recent = [item for item in self.context.consultations if item.get("state") == state.value]
            if recent:
                last = recent[-1]
                summary.extend(
                    [
                        f"Previous consultation question: {_shorten_text(last.get('question', ''), 140)}",
                        f"Previous consultation answer: {_shorten_text(last.get('answer', ''), 220)}",
                    ]
                )
            return summary
        if state == WorkflowState.WAIT_ANALYSIS_REVIEW:
            phase = self.plan.phase_for_state(WorkflowState.DATA_ANALYSIS)
            artifact_lines = []
            for hint in phase.artifact_hints:
                resolved = self.validation_runner._resolve_artifact_hint(hint, self.workspace)
                artifact_lines.append(
                    f"Artifact: {resolved} ({'exists' if resolved.exists() else 'missing'})"
                )
            summary = [
                f"Analysis report: {self.context.artifacts.get('state_data_analysis_report', '(missing)')}",
                f"Validation report: {self.context.artifacts.get('state_data_analysis_validation', '(missing)')}",
                *artifact_lines,
            ]
            recent = [item for item in self.context.consultations if item.get("state") == state.value]
            if recent:
                last = recent[-1]
                summary.extend(
                    [
                        f"Previous consultation question: {_shorten_text(last.get('question', ''), 140)}",
                        f"Previous consultation answer: {_shorten_text(last.get('answer', ''), 220)}",
                    ]
                )
            return summary
        if state == WorkflowState.WAIT_PAPER_REVIEW:
            validation_report = self._load_latest_paper_validation_report()
            summary = [
                f"Paper report: {self.context.artifacts.get('paper_report') or self.context.artifacts.get('paper_fix_report') or '(missing)'}",
                f"Validation report: {validation_report.report_path or '(missing)'}",
                f"Paper source: {self.context.artifacts.get('paper_typ', self.workspace / 'paper.typ')}",
                *validation_report.failures,
            ]
            if validation_report.artifact_checks:
                summary.extend(validation_report.artifact_checks)
            recent = [item for item in self.context.consultations if item.get("state") == state.value]
            if recent:
                last = recent[-1]
                summary.extend(
                    [
                        f"Previous consultation question: {_shorten_text(last.get('question', ''), 140)}",
                        f"Previous consultation answer: {_shorten_text(last.get('answer', ''), 220)}",
                    ]
                )
            return summary
        if state == WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW:
            validation_report = self._load_latest_template_validation_report()
            summary = [
                f"Template export report: {self.context.artifacts.get('paper_template_report') or self.context.artifacts.get('paper_report') or '(missing)'}",
                f"Validation report: {validation_report.report_path or '(missing)'}",
                f"Final Typst source: {self.context.artifacts.get('paper_final_typ', self.workspace / 'paper_final.typ')}",
                f"Final PDF: {self.context.artifacts.get('paper_pdf', self.workspace / 'paper.pdf')}",
                f"Template root: {self.context.artifacts.get('paper_template_root', '(missing)')}",
                *validation_report.failures,
            ]
            if validation_report.artifact_checks:
                summary.extend(validation_report.artifact_checks)
            recent = [item for item in self.context.consultations if item.get("state") == state.value]
            if recent:
                last = recent[-1]
                summary.extend(
                    [
                        f"Previous consultation question: {_shorten_text(last.get('question', ''), 140)}",
                        f"Previous consultation answer: {_shorten_text(last.get('answer', ''), 220)}",
                    ]
                )
            return summary
        return []

    def _write_template_export_report(
        self,
        *,
        run_dir: Path,
        phase: PhaseSpec,
        export: TemplateExportExecution,
        codex: CodexExecution,
        validation: ValidationReport,
    ) -> StageReport:
        report = StageReport(
            stage=WorkflowState.PAPER_TEMPLATE_EXPORT,
            attempt=self.context.phase_attempts[WorkflowState.PAPER_TEMPLATE_EXPORT.value],
            run_dir=run_dir,
            prompt_path=run_dir / "prompt.txt",
            report_path=run_dir / "paper_template_report.json",
            summary="paper template export",
            details={
                "codex": {
                    "returncode": codex.returncode,
                    "modified_files": codex.modified_files,
                    "stdout_path": str(codex.stdout_path),
                    "stderr_path": str(codex.stderr_path),
                    "last_message_path": str(codex.last_message_path),
                },
                "template_root": str(export.template_root),
                "draft_path": str(export.draft_path),
                "final_path": str(export.final_path),
                "pdf_path": str(export.pdf_path),
                "manifest_path": str(export.manifest_path),
                "bibliography_path": export.bibliography_path,
                "section_titles": export.section_titles,
                "validation": {
                    "success": validation.success,
                    "checks": validation.checks,
                    "failures": validation.failures,
                    "artifact_checks": validation.artifact_checks,
                    "executed_commands": validation.executed_commands,
                },
            },
        )
        _json_dump_atomic(
            report.report_path,
            {
                "stage": WorkflowState.PAPER_TEMPLATE_EXPORT.value,
                "attempt": report.attempt,
                "run_dir": str(run_dir),
                "prompt_path": str(run_dir / "prompt.txt"),
                "summary": report.summary,
                "codex": report.details["codex"],
                "template": {
                    "root": str(export.template_root),
                    "draft_path": str(export.draft_path),
                    "final_path": str(export.final_path),
                    "pdf_path": str(export.pdf_path),
                    "manifest_path": str(export.manifest_path),
                    "bibliography_path": export.bibliography_path,
                    "section_titles": export.section_titles,
                },
                "validation": report.details["validation"],
            },
        )
        return report

    def _compose_template_export_feedback(
        self,
        *,
        codex: CodexExecution,
        export: TemplateExportExecution,
        validation: ValidationReport,
    ) -> str:
        parts = [
            "Template export stage failed.",
            f"Codex exit code: {codex.returncode}",
            f"Template root: {export.template_root}",
            f"Draft source: {export.draft_path}",
            f"Final source: {export.final_path}",
            f"Final PDF: {export.pdf_path}",
            f"Bibliography path: {export.bibliography_path}",
        ]
        if codex.last_message:
            parts.append("Codex last message:")
            parts.append(codex.last_message)
        if codex.stderr_text.strip():
            parts.append("Codex stderr:")
            parts.append(codex.stderr_text.strip()[:6000])
        if validation.failures:
            parts.append("Validation failures:")
            parts.extend(f"- {item}" for item in validation.failures)
        if validation.artifact_checks:
            parts.append("Artifact checks:")
            parts.extend(f"- {item}" for item in validation.artifact_checks)
        return "\n".join(parts).strip() + "\n"

    def _load_latest_template_validation_report(self) -> ValidationReport:
        report_hint = self.context.artifacts.get("paper_template_report", "") or self.context.artifacts.get("paper_report", "")
        if report_hint:
            report_path = Path(report_hint)
            if report_path.exists():
                data = _json_load(report_path, {})
                validation = data.get("validation") if isinstance(data, dict) else {}
                if isinstance(validation, dict):
                    return ValidationReport(
                        success=bool(validation.get("success")),
                        checks=[str(item) for item in validation.get("checks", [])],
                        failures=[str(item) for item in validation.get("failures", [])],
                        executed_commands=[str(item) for item in validation.get("executed_commands", [])],
                        artifact_checks=[str(item) for item in validation.get("artifact_checks", [])],
                        report_path=report_path,
                    )
        stage_dir = self.workspace / "runs" / WorkflowState.PAPER_TEMPLATE_EXPORT.value
        if not stage_dir.exists():
            return ValidationReport(success=False, failures=[f"No run directory for {WorkflowState.PAPER_TEMPLATE_EXPORT.value}"])
        report_paths = sorted(stage_dir.rglob("paper_template_report.json"), key=lambda item: item.stat().st_mtime if item.exists() else 0)
        if not report_paths:
            report_paths = sorted(stage_dir.rglob("validation_report.json"), key=lambda item: item.stat().st_mtime if item.exists() else 0)
        if not report_paths:
            return ValidationReport(success=False, failures=[f"No template export report for {WorkflowState.PAPER_TEMPLATE_EXPORT.value}"])
        data = _json_load(report_paths[-1], {})
        validation = data.get("validation") if isinstance(data, dict) else {}
        if not isinstance(validation, dict):
            validation = {}
        return ValidationReport(
            success=bool(validation.get("success")),
            checks=[str(item) for item in validation.get("checks", [])],
            failures=[str(item) for item in validation.get("failures", [])],
            executed_commands=[str(item) for item in validation.get("executed_commands", [])],
            artifact_checks=[str(item) for item in validation.get("artifact_checks", [])],
            report_path=report_paths[-1],
        )

    def _build_review_consult_prompt(
        self,
        *,
        review_state: WorkflowState,
        active_state: WorkflowState,
        question: str,
        summary_lines: list[str],
        consult_workspace: Path,
    ) -> str:
        phase = self.plan.phase_for_state(active_state)
        artifacts = []
        for hint in phase.artifact_hints:
            resolved = self.validation_runner._resolve_artifact_hint(hint, consult_workspace)
            artifacts.append(
                {
                    "hint": hint,
                    "resolved": str(resolved),
                    "exists": resolved.exists(),
                }
            )

        payload = {
            "workspace": str(consult_workspace),
            "review_state": review_state.value,
            "active_state": active_state.value,
            "phase_heading": phase.heading,
            "phase_body": phase.body,
            "summary_lines": summary_lines,
            "question": question,
            "last_feedback": self.context.last_feedback,
            "artifacts": artifacts,
        }
        instructions = textwrap.dedent(
            """
            You are Codex in consultation mode for FluidAgent Pro.
            This is a read-only review consultation, not a coding task.
            Do not modify files.
            Answer the human's question using evidence from the workspace files.
            If the observation is expected, explain why.
            If it is a problem, identify the likely cause and what to inspect next.
            Keep the answer concise but specific.
            """
        ).strip()
        return instructions + "\n\nContext JSON:\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def _run_review_consult(self, *, state: WorkflowState, question: str) -> None:
        assert self.context is not None
        assert self.plan is not None
        active_state = self._active_state_for_review(state)
        consult_index = sum(1 for item in self.context.consultations if item.get("state") == state.value) + 1
        run_dir = self.workspace / "runs" / state.value / f"consult_{_now_stamp()}_{consult_index}"
        run_dir.mkdir(parents=True, exist_ok=True)

        scratch_root = Path(tempfile.mkdtemp(prefix=f"fluidagent_consult_{state.name.lower()}_"))
        consult_workspace = scratch_root / "workspace"
        ignore = shutil.ignore_patterns("runs", ".agent_state.json", "__pycache__", ".mypy_cache", ".git")
        self.review_cli.print_status(f"[Consult] Preparing scratch workspace at {consult_workspace}")
        shutil.copytree(self.workspace, consult_workspace, ignore=ignore)

        summary_lines = self._review_summary(state)
        prompt = self._build_review_consult_prompt(
            review_state=state,
            active_state=active_state,
            question=question,
            summary_lines=summary_lines,
            consult_workspace=consult_workspace,
        )
        prompt_path = run_dir / "consult_prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")

        self.review_cli.print_status(f"[Consult] Question: {question}")
        self.review_cli.print_status(f"[Consult] Using phase: {self.plan.phase_for_state(active_state).heading}")
        self.review_cli.print_status(f"[Consult] Scratch workspace: {consult_workspace}")
        self.review_cli.print_status(f"[Consult] Launching Codex consultation in {run_dir / 'codex'}")

        execution = self.codex_runner.run_with_status(
            workspace=consult_workspace,
            prompt=prompt,
            run_dir=run_dir / "codex",
            status_cb=self.review_cli.print_status,
        )
        answer = execution.last_message.strip() or execution.stdout_text.strip() or "(Codex did not return a final answer.)"
        answer_path = run_dir / "consult_answer.txt"
        answer_path.write_text(answer + "\n", encoding="utf-8")
        report_path = run_dir / "consultation_report.json"
        report_payload = {
            "state": state.value,
            "active_state": active_state.value,
            "question": question,
            "answer": answer,
            "returncode": execution.returncode,
            "workspace": str(consult_workspace),
            "scratch_root": str(scratch_root),
            "prompt_path": str(prompt_path),
            "answer_path": str(answer_path),
            "run_dir": str(run_dir),
            "modified_files": execution.modified_files,
            "stdout_path": str(execution.stdout_path),
            "stderr_path": str(execution.stderr_path),
            "last_message_path": str(execution.last_message_path),
        }
        _json_dump_atomic(report_path, report_payload)

        self.context.consultations.append(
            {
                "timestamp": _now_stamp(),
                "state": state.value,
                "active_state": active_state.value,
                "question": question,
                "answer": answer,
                "run_dir": str(run_dir),
                "prompt_path": str(prompt_path),
                "answer_path": str(answer_path),
                "report_path": str(report_path),
            }
        )
        self.context.artifacts["last_consultation_report"] = str(report_path)
        self.context.artifacts["last_consultation_run_dir"] = str(run_dir)
        self.context.artifacts["last_consultation_workspace"] = str(consult_workspace)
        self.context.save()

        self.review_cli.print_status("[Consult] Codex answer:")
        for line in answer.splitlines() or [answer]:
            self.review_cli.print_status(f"[Consult] {line}")
        if execution.returncode != 0:
            self.review_cli.print_status(f"[Consult] Consultation exited with rc={execution.returncode}")
        self.review_cli.print_status(f"[Consult] Consultation complete; remaining at {state.value}")

    def _rewind_to_phase_two(self, *, source_state: WorkflowState, reason: str) -> None:
        self._rewind_to_state(
            source_state=source_state,
            target_state=WorkflowState.DATA_ANALYSIS,
            reason=reason,
        )

    def _rewind_to_phase_one(self, *, source_state: WorkflowState, reason: str) -> None:
        self._rewind_to_state(
            source_state=source_state,
            target_state=WorkflowState.CODING_VERIFY,
            reason=reason,
        )

    def _rewind_to_state(self, *, source_state: WorkflowState, target_state: WorkflowState, reason: str) -> None:
        assert self.context is not None

        target_label = target_state.value
        default_reason = f"User requested a rewind to {target_label}."
        rewind_reason = reason.strip() or default_reason
        if self.context.last_feedback.strip():
            rewind_reason = f"{rewind_reason}\n\nPrevious phase guidance:\n{self.context.last_feedback.strip()}"

        self.review_cli.print_status(f"[FSM] Rewinding from {source_state.value} to {target_label}")
        self.review_cli.print_status(f"[FSM] Rewind reason: {_shorten_text(rewind_reason, 400)}")

        if target_state == WorkflowState.CODING_VERIFY:
            self._reset_generated_workspace(hard=False, clear_all=True, purge_install=False, preserve_state=True)
        else:
            downstream_states = {
                WorkflowState.PAPER_WRITING.value,
                WorkflowState.PAPER_FIX.value,
                WorkflowState.WAIT_PAPER_REVIEW.value,
                WorkflowState.PAPER_TEMPLATE_EXPORT.value,
                WorkflowState.WAIT_PAPER_TEMPLATE_REVIEW.value,
            }
            for key in list(self.context.phase_attempts):
                if key in downstream_states:
                    self.context.phase_attempts.pop(key, None)

            paper_related_keys = [
                "paper_draft_run_dir",
                "paper_draft_request",
                "paper_draft_response",
                "paper_draft_raw_response",
                "paper_typ",
                "paper_fix_run_dir",
                "paper_fix_report",
                "paper_fix_validation",
                "paper_report",
                "paper_template_run_dir",
                "paper_template_root",
                "paper_template_manifest",
                "paper_template_typ",
                "paper_final_typ",
                "paper_pdf",
                "paper_template_report",
                "paper_template_validation",
            ]
            removed_paths: list[str] = []
            for key in paper_related_keys:
                value = self.context.artifacts.pop(key, None)
                if not value:
                    continue
                candidate = self._path_within_workspace(value)
                if candidate is not None and _delete_path(candidate):
                    removed_paths.append(_safe_relpath(candidate, self.workspace))

            if removed_paths:
                self.review_cli.print_status("[FSM] Removed downstream paper artifacts:")
                for item in removed_paths:
                    self.review_cli.print_status(f"[FSM]   {item}")

        if target_state == WorkflowState.CODING_VERIFY:
            core_artifact_keys = {"workspace", "plan_path", "metadata_path", "plan_checksum"}
            self.context.artifacts = {
                key: value for key, value in self.context.artifacts.items() if key in core_artifact_keys
            }
            self.context.phase_attempts.clear()
            self.context.consultations = []
        else:
            self.context.last_feedback = ""

        current_task = self.workspace / "current_task.txt"
        if target_state == WorkflowState.CODING_VERIFY:
            next_action = "Revisit Phase 1, repair the solver implementation, rerun verification, and only return to analysis after the solver data is consistent."
        else:
            next_action = "Revisit Phase 2, update solver/data analysis outputs, and only return to paper writing after the scientific results match the benchmark expectations."
        current_task.write_text(
            "\n".join(
                [
                    f"Rewound from {source_state.value} to {target_state.value}.",
                    f"Reason: {rewind_reason}",
                    "",
                    f"Next action: {next_action}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        self.context.last_feedback = rewind_reason.strip() + "\n"
        self.context.transition_to(target_state)
        self.context.save()

    def _write_stage_report(
        self,
        *,
        state: WorkflowState,
        attempt: int,
        run_dir: Path,
        prompt_path: Path,
        codex: CodexExecution,
        validation: ValidationReport,
    ) -> StageReport:
        report = StageReport(
            stage=state,
            attempt=attempt,
            run_dir=run_dir,
            prompt_path=prompt_path,
            report_path=run_dir / "stage_report.json",
            summary=f"{state.value} attempt {attempt}",
            details={
                "codex": {
                    "returncode": codex.returncode,
                    "modified_files": codex.modified_files,
                    "stdout_path": str(codex.stdout_path),
                    "stderr_path": str(codex.stderr_path),
                    "last_message_path": str(codex.last_message_path),
                },
                "validation": {
                    "success": validation.success,
                    "checks": validation.checks,
                    "failures": validation.failures,
                    "artifact_checks": validation.artifact_checks,
                    "executed_commands": validation.executed_commands,
                    "report_path": str(validation.report_path) if validation.report_path else "",
                },
            },
        )
        _json_dump_atomic(
            report.report_path,
            {
                "stage": state.value,
                "attempt": attempt,
                "run_dir": str(run_dir),
                "prompt_path": str(prompt_path),
                "summary": report.summary,
                "codex": report.details["codex"],
                "validation": report.details["validation"],
            },
        )
        return report

    def _write_paper_report(
        self,
        *,
        run_dir: Path,
        phase: PhaseSpec,
        gemini_execution: GeminiExecution,
        codex: CodexExecution,
        validation: ValidationReport,
    ) -> StageReport:
        report = StageReport(
            stage=WorkflowState.PAPER_FIX,
            attempt=self.context.phase_attempts[WorkflowState.PAPER_FIX.value],
            run_dir=run_dir,
            prompt_path=codex.prompt_path,
            report_path=run_dir / "paper_report.json",
            summary="paper repair",
            details={
                "gemini_request": str(gemini_execution.request_path),
                "gemini_response": str(gemini_execution.response_path),
                "gemini_raw_response": str(gemini_execution.raw_response_path),
                "codex": {
                    "returncode": codex.returncode,
                    "modified_files": codex.modified_files,
                    "stdout_path": str(codex.stdout_path),
                    "stderr_path": str(codex.stderr_path),
                    "last_message_path": str(codex.last_message_path),
                },
                "paper_path": str(self.workspace / "paper.typ"),
                "validation": {
                    "success": validation.success,
                    "checks": validation.checks,
                    "failures": validation.failures,
                    "artifact_checks": validation.artifact_checks,
                    "executed_commands": validation.executed_commands,
                },
            },
        )
        _json_dump_atomic(
            report.report_path,
            {
                "stage": WorkflowState.PAPER_FIX.value,
                "attempt": report.attempt,
                "run_dir": str(run_dir),
                "prompt_path": str(codex.prompt_path),
                "summary": report.summary,
                "gemini": {
                    "request": str(gemini_execution.request_path),
                    "response": str(gemini_execution.response_path),
                    "raw_response": str(gemini_execution.raw_response_path),
                },
                "codex": report.details["codex"],
                "paper_path": str(self.workspace / "paper.typ"),
                "validation": report.details["validation"],
            },
        )
        return report

    def _load_paper_draft_execution(self) -> GeminiExecution:
        request_hint = self.context.artifacts.get("paper_draft_request", "")
        response_hint = self.context.artifacts.get("paper_draft_response", "")
        raw_response_hint = self.context.artifacts.get("paper_draft_raw_response", "")
        if request_hint and response_hint and raw_response_hint:
            request_path = Path(request_hint)
            response_path = Path(response_hint)
            raw_response_path = Path(raw_response_hint)
            text = response_path.read_text(encoding="utf-8") if response_path.exists() else ""
            try:
                data = json.loads(text) if text else {}
            except json.JSONDecodeError:
                data = {}
            return GeminiExecution(
                request_path=request_path,
                response_path=response_path,
                raw_response_path=raw_response_path,
                text=text,
                data=data,
            )

        stage_dir = self.workspace / "runs" / WorkflowState.PAPER_WRITING.value
        if stage_dir.exists():
            run_dirs = sorted(
                [path for path in stage_dir.iterdir() if path.is_dir()],
                key=lambda item: item.stat().st_mtime if item.exists() else 0,
            )
            if run_dirs:
                latest = run_dirs[-1]
                request_path = latest / "gemini" / "gemini_request.json"
                response_path = latest / "gemini" / "gemini_response.json"
                raw_response_path = latest / "gemini" / "gemini_raw_response.txt"
                text = response_path.read_text(encoding="utf-8") if response_path.exists() else ""
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError:
                    data = {}
                return GeminiExecution(
                    request_path=request_path,
                    response_path=response_path,
                    raw_response_path=raw_response_path,
                    text=text,
                    data=data,
                )

        fallback = self.workspace / "runs" / WorkflowState.PAPER_WRITING.value / "missing"
        return GeminiExecution(
            request_path=fallback / "gemini_request.json",
            response_path=fallback / "gemini_response.json",
            raw_response_path=fallback / "gemini_raw_response.txt",
            text="",
            data={},
        )

    def _load_latest_validation_report(self, phase: PhaseSpec, stage: WorkflowState) -> ValidationReport:
        stage_dir = self.workspace / "runs" / stage.value
        if not stage_dir.exists():
            return ValidationReport(success=False, failures=[f"No run directory for {stage.value}"])
        report_paths = sorted(stage_dir.rglob("validation_report.json"), key=lambda item: item.stat().st_mtime if item.exists() else 0)
        if not report_paths:
            return ValidationReport(success=False, failures=[f"No validation report for {stage.value}"])
        data = _json_load(report_paths[-1], {})
        return ValidationReport(
            success=bool(data.get("success")),
            checks=[str(item) for item in data.get("checks", [])],
            failures=[str(item) for item in data.get("failures", [])],
            executed_commands=[str(item) for item in data.get("executed_commands", [])],
            artifact_checks=[str(item) for item in data.get("artifact_checks", [])],
            report_path=report_paths[-1],
        )

    def _load_latest_paper_validation_report(self) -> ValidationReport:
        report_hint = self.context.artifacts.get("paper_report", "") or self.context.artifacts.get("paper_fix_report", "")
        if report_hint:
            report_path = Path(report_hint)
            if report_path.exists():
                data = _json_load(report_path, {})
                validation = data.get("validation") if isinstance(data, dict) else {}
                if isinstance(validation, dict):
                    return ValidationReport(
                        success=bool(validation.get("success")),
                        checks=[str(item) for item in validation.get("checks", [])],
                        failures=[str(item) for item in validation.get("failures", [])],
                        executed_commands=[str(item) for item in validation.get("executed_commands", [])],
                        artifact_checks=[str(item) for item in validation.get("artifact_checks", [])],
                        report_path=report_path,
                    )
        stage_dir = self.workspace / "runs" / WorkflowState.PAPER_FIX.value
        if not stage_dir.exists():
            return ValidationReport(success=False, failures=[f"No run directory for {WorkflowState.PAPER_FIX.value}"])
        report_paths = sorted(stage_dir.rglob("paper_report.json"), key=lambda item: item.stat().st_mtime if item.exists() else 0)
        if not report_paths:
            return ValidationReport(success=False, failures=[f"No paper report for {WorkflowState.PAPER_FIX.value}"])
        data = _json_load(report_paths[-1], {})
        validation = data.get("validation") if isinstance(data, dict) else {}
        if not isinstance(validation, dict):
            validation = {}
        return ValidationReport(
            success=bool(validation.get("success")),
            checks=[str(item) for item in validation.get("checks", [])],
            failures=[str(item) for item in validation.get("failures", [])],
            executed_commands=[str(item) for item in validation.get("executed_commands", [])],
            artifact_checks=[str(item) for item in validation.get("artifact_checks", [])],
            report_path=report_paths[-1],
        )

    def _compose_retry_feedback(self, *, state: WorkflowState, codex: CodexExecution, validation: ValidationReport) -> str:
        parts = [
            f"Stage {state.value} failed.",
            f"Codex exit code: {codex.returncode}",
        ]
        if codex.last_message:
            parts.append("Codex last message:")
            parts.append(codex.last_message)
        if codex.stderr_text.strip():
            parts.append("Codex stderr:")
            parts.append(codex.stderr_text.strip()[:6000])
        if validation.failures:
            parts.append("Validation failures:")
            parts.extend(f"- {item}" for item in validation.failures)
        if validation.artifact_checks:
            parts.append("Artifact checks:")
            parts.extend(f"- {item}" for item in validation.artifact_checks)
        return "\n".join(parts).strip() + "\n"

    def _enter_error(self, message: str) -> None:
        assert self.context is not None
        self.context.previous_state = self.context.state
        self.context.state = WorkflowState.ERROR
        error_log = self.workspace / "logs" / "error.log"
        error_log.parent.mkdir(parents=True, exist_ok=True)
        error_log.write_text(message + "\n", encoding="utf-8")
        self.context.artifacts["error_log"] = str(error_log)
        self.context.save()
        self.review_cli.print_status(message)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="FluidAgent Pro controller")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Workspace root.")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve review checkpoints.")
    parser.add_argument("--stdio-only", action="store_true", help="Use stdin/stdout only for review prompts and do not auto-approve when launched without a TTY.")
    parser.add_argument("--dry-run", action="store_true", help="Build prompts and validate config without calling external models.")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--clear", action="store_true", help="Delete generated workspace outputs and caches, but keep src/, then exit.")
    mode_group.add_argument("--clear-hard", action="store_true", help="Delete generated workspace outputs, caches, and src/, then exit.")
    parser.add_argument("--purge-install", action="store_true", help="When clearing, also delete pip install -e artifacts such as build/, dist/, and *.egg-info.")
    parser.add_argument("--codex-model", default=None, help="Override the codex CLI model.")
    parser.add_argument("--gemini-model", default=None, help="Override the Gemini model.")
    parser.add_argument("--max-stage-attempts", type=int, default=DEFAULT_STAGE_ATTEMPTS, help="Maximum attempts per stage.")
    parser.add_argument("--codex-timeout", type=int, default=DEFAULT_CODEX_TIMEOUT, help="Codex timeout in seconds.")
    parser.add_argument("--gemini-timeout", type=int, default=DEFAULT_GEMINI_TIMEOUT, help="Gemini timeout in seconds.")
    args = parser.parse_args(argv)
    if args.purge_install and not (args.clear or args.clear_hard):
        parser.error("--purge-install requires --clear or --clear-hard")

    agent = FluidAgentPro(
        workspace=args.workspace,
        auto_approve=False if args.stdio_only else (True if args.auto_approve else None),
        force_stdio=bool(args.stdio_only),
        dry_run=args.dry_run,
        clear=bool(args.clear or args.clear_hard),
        clear_hard=bool(args.clear_hard),
        purge_install=bool(args.purge_install),
        codex_model=args.codex_model,
        gemini_model=args.gemini_model,
        max_stage_attempts=args.max_stage_attempts,
        codex_timeout=args.codex_timeout,
        gemini_timeout=args.gemini_timeout,
    )

    try:
        if args.clear or args.clear_hard:
            agent.run()
            return 0
        agent.bootstrap()
        if args.dry_run:
            agent.review_cli.print_status("[FSM] Dry run complete.")
            return 0
        agent.run()
    except Exception as exc:
        print(f">>> [FluidAgentPro] Fatal error: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    if agent.context and agent.context.state == WorkflowState.ERROR:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
