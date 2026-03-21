from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PySide6.QtCore import QProcess, QProcessEnvironment, QSettings, Qt, QUrl, Signal, QObject
    from PySide6.QtGui import QDesktopServices, QFontDatabase, QTextCursor
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QFileDialog,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QStackedWidget,
        QStatusBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - exercised in GUI-only environments
    raise SystemExit(
        "PySide6 is required for the GUI. Install it with `pip install .[gui]`."
    ) from exc


STATE_EVENT_PATTERNS = (
    re.compile(r"(?m)^\s*>>> \[FluidAgentPro\] \[Bootstrap\].*?Resume state: (STATE_[A-Z_]+)\b"),
    re.compile(r"(?m)^\s*>>> \[FluidAgentPro\] \[Review\] Waiting for .*? at (STATE_[A-Z_]+)\b"),
    re.compile(r"(?m)^\s*>>> \[FluidAgentPro\] \[FSM\].*?(?:->|to) (STATE_[A-Z_]+)\b"),
)
APP_ORG = "FluidAgentPro"
APP_NAME = "FluidAgentPro"


@dataclass
class LaunchOptions:
    workspace: Path
    clear: bool = False
    clear_hard: bool = False
    purge_install: bool = False


class WorkflowProcess(QObject):
    output_received = Signal(str)
    state_changed = Signal(str)
    mode_changed = Signal(str)
    started = Signal()
    finished = Signal(int)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._drain_output)
        self.process.started.connect(self.started.emit)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)
        self._mode = "singleline"
        self._job_kind = "workflow"

    @property
    def running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def job_kind(self) -> str:
        return self._job_kind

    def start(self, options: LaunchOptions) -> None:
        if self.running:
            raise RuntimeError("Workflow is already running.")

        if options.clear_hard and options.purge_install:
            self._job_kind = "clear-hard-install"
        elif options.clear_hard:
            self._job_kind = "clear-hard"
        elif options.clear and options.purge_install:
            self._job_kind = "clear-install"
        elif options.clear:
            self._job_kind = "clear"
        else:
            self._job_kind = "workflow"
        args = [
            "-m",
            "fluid_agent_pro",
            "--workspace",
            str(options.workspace),
            "--stdio-only",
        ]
        if options.clear_hard:
            args.append("--clear-hard")
        elif options.clear:
            args.append("--clear")
        if options.purge_install:
            args.append("--purge-install")

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(options.workspace))
        self.process.start(sys.executable, args)

    def stop(self) -> None:
        if not self.running:
            return
        self.process.terminate()

    def kill(self) -> None:
        if self.running:
            self.process.kill()

    def send_text(self, text: str, *, multiline: bool = False) -> None:
        if not self.running:
            return
        payload = text.rstrip("\n")
        if not payload:
            return
        if not multiline and "\n" in payload:
            payload = payload.splitlines()[0]
        if multiline:
            payload += "\n\n"
        else:
            payload += "\n"
        self.process.write(payload.encode("utf-8"))
        self.process.waitForBytesWritten(1000)

    def _drain_output(self) -> None:
        chunk = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not chunk:
            return
        self.output_received.emit(chunk)
        for pattern in STATE_EVENT_PATTERNS:
            for match in pattern.finditer(chunk):
                self.state_changed.emit(match.group(1))
        self._update_mode_from_output(chunk)

    def _update_mode_from_output(self, chunk: str) -> None:
        if "Enter your question for Codex." in chunk or "Finish with a blank line." in chunk:
            self._set_mode("multiline")
            return
        if "Selected action: CONSULT" in chunk:
            self._set_mode("multiline")
            return
        if (
            "Continue repair with Y" in chunk
            or "Continue export with Y" in chunk
            or "Continue with Y, provide guidance with N, rewind to Phase 1 with P1" in chunk
            or "Approve with Y, reject with N" in chunk
        ):
            self._set_mode("singleline")
            return
        if "Describe the paper formatting or content issue to fix:" in chunk:
            self._set_mode("singleline")
            return
        if "Describe what should be revisited in Phase 2:" in chunk:
            self._set_mode("singleline")
            return
        if "Describe why this should go back to Phase 1:" in chunk:
            self._set_mode("singleline")
            return
        if "Enter reviewer feedback:" in chunk:
            self._set_mode("singleline")
            return
        if "Selected action: REJECT" in chunk or "Selected action: APPROVE" in chunk or "Selected action: QUIT" in chunk:
            self._set_mode("singleline")

    def _set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self.mode_changed.emit(mode)

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self.finished.emit(exit_code)

    def _on_error(self, _error: QProcess.ProcessError) -> None:
        self.failed.emit(self.process.errorString())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FluidAgent Pro")
        self.settings = QSettings(APP_ORG, APP_NAME)
        self.bridge = WorkflowProcess(self)
        self.current_mode = "singleline"
        self.current_state = "idle"
        self.review_state_hint = "idle"
        self.back_action_token = ""
        self._build_ui()
        self._update_review_controls()
        self._restore_state()
        self._connect_bridge()

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        workspace_row = QGridLayout()
        workspace_row.setHorizontalSpacing(8)
        workspace_row.setVerticalSpacing(6)

        self.workspace_edit = QLineEdit()
        self.workspace_edit.setPlaceholderText("Choose the project workspace")
        browse_workspace = QPushButton("Browse")
        browse_workspace.clicked.connect(self._browse_workspace)
        open_workspace = QPushButton("Open")
        open_workspace.clicked.connect(self._open_workspace)

        workspace_row.addWidget(QLabel("Workspace"), 0, 0)
        workspace_row.addWidget(self.workspace_edit, 0, 1, 1, 3)
        workspace_row.addWidget(browse_workspace, 0, 4)
        workspace_row.addWidget(open_workspace, 0, 5)
        workspace_hint = QLabel(
            "Workspace should contain research_plan.md and a paper-template/clear-iclr or template/clear-iclr folder."
        )
        workspace_hint.setWordWrap(True)

        self.state_label = QLabel("State: idle")
        self.mode_label = QLabel("Input mode: single-line")
        self.prompt_label = QLabel("Prompt: waiting")
        self.prompt_label.setWordWrap(True)

        control_row = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.clear_workspace_button = QPushButton("Clear Workspace")
        self.clear_include_src_check = QCheckBox("Include src/")
        self.clear_include_src_check.setToolTip("Use when you want to remove generated source code as well.")
        self.clear_purge_install_check = QCheckBox("Purge editable-install files")
        self.clear_purge_install_check.setToolTip("Deletes build/, dist/, and *.egg-info so pip install -e must be rerun.")
        self.y_button = QPushButton("Y")
        self.n_button = QPushButton("N")
        self.b_button = QPushButton("Back")
        self.b_button.setToolTip("Rewind from a review checkpoint.")
        self.c_button = QPushButton("C")
        self.q_button = QPushButton("Q")
        control_row.addWidget(self.start_button)
        control_row.addWidget(self.stop_button)
        control_row.addWidget(self.clear_workspace_button)
        control_row.addWidget(self.clear_include_src_check)
        control_row.addWidget(self.clear_purge_install_check)
        control_row.addStretch(1)
        control_row.addWidget(self.y_button)
        control_row.addWidget(self.n_button)
        control_row.addWidget(self.b_button)
        control_row.addWidget(self.c_button)
        control_row.addWidget(self.q_button)

        self.start_button.clicked.connect(self._start_workflow)
        self.stop_button.clicked.connect(self._stop_workflow)
        self.clear_workspace_button.clicked.connect(self._clear_workspace)
        self.y_button.clicked.connect(lambda: self._send_quick("Y"))
        self.n_button.clicked.connect(lambda: self._send_quick("N"))
        self.b_button.clicked.connect(self._send_back_action)
        self.c_button.clicked.connect(lambda: self._send_quick("C"))
        self.q_button.clicked.connect(lambda: self._send_quick("Q"))

        meta_row = QGridLayout()
        meta_row.addWidget(self.state_label, 0, 0)
        meta_row.addWidget(self.mode_label, 0, 1)
        meta_row.addWidget(self.prompt_label, 1, 0, 1, 2)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

        self.input_stack = QStackedWidget()
        self.single_input = QLineEdit()
        self.single_input.setPlaceholderText("Type Y / N / P1 / B / P2 / C / Q, or a short reply, then send.")
        self.single_input.returnPressed.connect(self._send_current_input)
        self.multi_input = QPlainTextEdit()
        self.multi_input.setPlaceholderText("Type multi-line feedback or a Codex question here.")
        self.multi_input.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.input_stack.addWidget(self.single_input)
        self.input_stack.addWidget(self.multi_input)

        send_row = QHBoxLayout()
        send_button = QPushButton("Send")
        send_button.clicked.connect(self._send_current_input)
        input_clear_button = QPushButton("Clear Input")
        input_clear_button.clicked.connect(self._clear_input)
        send_row.addWidget(send_button)
        send_row.addWidget(input_clear_button)
        send_row.addStretch(1)

        layout.addLayout(workspace_row)
        layout.addWidget(workspace_hint)
        layout.addLayout(control_row)
        layout.addLayout(meta_row)
        layout.addWidget(self.log_view, stretch=1)
        layout.addWidget(self.input_stack)
        layout.addLayout(send_row)

        self.setCentralWidget(central)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")

    def _connect_bridge(self) -> None:
        self.bridge.output_received.connect(self._append_output)
        self.bridge.state_changed.connect(self._set_state_label)
        self.bridge.mode_changed.connect(self._set_input_mode)
        self.bridge.started.connect(self._on_started)
        self.bridge.finished.connect(self._on_finished)
        self.bridge.failed.connect(self._on_failed)

    def _restore_state(self) -> None:
        workspace = self.settings.value("workspace", str(Path.cwd()), type=str)
        self.workspace_edit.setText(workspace or str(Path.cwd()))
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.settings.setValue("workspace", self.workspace_edit.text().strip() or str(Path.cwd()))
        self.settings.setValue("geometry", self.saveGeometry())
        if self.bridge.running:
            choice = QMessageBox.question(
                self,
                "FluidAgent Pro",
                "The workflow is still running. Stop it and close the window?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.bridge.stop()
            self.bridge.kill()
        super().closeEvent(event)

    def _browse_workspace(self) -> None:
        start_dir = self.workspace_edit.text().strip() or str(Path.cwd())
        selected = QFileDialog.getExistingDirectory(self, "Select workspace", start_dir)
        if selected:
            self.workspace_edit.setText(selected)

    def _open_workspace(self) -> None:
        workspace = self._workspace_path()
        if workspace is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(workspace)))

    def _workspace_path(self) -> Path | None:
        raw = self.workspace_edit.text().strip()
        if not raw:
            QMessageBox.warning(self, "FluidAgent Pro", "Please select a workspace first.")
            return None
        workspace = Path(raw).expanduser().resolve()
        return workspace

    def _start_workflow(self) -> None:
        if self.bridge.running:
            QMessageBox.information(self, "FluidAgent Pro", "The workflow is already running.")
            return
        workspace = self._workspace_path()
        if workspace is None:
            return
        workspace.mkdir(parents=True, exist_ok=True)
        options = LaunchOptions(
            workspace=workspace,
        )
        self.log_view.clear()
        self.status_bar.showMessage(f"Starting workflow in {workspace}")
        self.bridge.start(options)

    def _clear_workspace(self) -> None:
        if self.bridge.running:
            QMessageBox.information(self, "FluidAgent Pro", "Stop the current process before clearing the workspace.")
            return
        workspace = self._workspace_path()
        if workspace is None:
            return
        include_src = self.clear_include_src_check.isChecked()
        purge_install = self.clear_purge_install_check.isChecked()
        mode_text = "including src/" if include_src else "without src/"
        install_text = "and purging editable-install files" if purge_install else "and keeping editable-install files"
        confirmation = QMessageBox.question(
            self,
            "FluidAgent Pro",
            f"Clear generated outputs and caches from this workspace {mode_text} {install_text}?\n\n"
            f"Workspace:\n{workspace}\n\n"
            "This keeps research_plan.md, readme.md, metadata.json, references.bib, and paper-template/ intact.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return
        options = LaunchOptions(workspace=workspace, clear=not include_src, clear_hard=include_src, purge_install=purge_install)
        self.log_view.clear()
        self._append_output(f"[GUI] Clearing workspace: {workspace} ({mode_text}, {install_text})\n")
        self.status_bar.showMessage(f"Clearing workspace in {workspace} ({mode_text}, {install_text})")
        self.bridge.start(options)

    def _stop_workflow(self) -> None:
        if not self.bridge.running:
            return
        self.status_bar.showMessage("Stopping workflow...")
        self.bridge.stop()

    def _send_quick(self, token: str) -> None:
        if not self.bridge.running:
            return
        self._append_output(f"[GUI] Sending quick action: {token}\n")
        self.status_bar.showMessage(f"Sending {token}...")
        self.bridge.send_text(token, multiline=False)
        self._clear_input()

    def _send_back_action(self) -> None:
        if not self.back_action_token:
            return
        self._send_quick(self.back_action_token)

    def _send_current_input(self) -> None:
        if not self.bridge.running:
            return
        if self.current_mode == "multiline":
            text = self.multi_input.toPlainText().strip("\n")
            if not text.strip():
                return
            self.bridge.send_text(text, multiline=True)
        else:
            text = self.single_input.text().strip()
            if not text:
                return
            self.bridge.send_text(text, multiline=False)
        self._clear_input()

    def _clear_input(self) -> None:
        self.single_input.clear()
        self.multi_input.clear()

    def _append_output(self, text: str) -> None:
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.log_view.setTextCursor(cursor)
        self.log_view.ensureCursorVisible()
        self._sync_review_state_from_output(text)

    def _sync_review_state_from_output(self, text: str) -> None:
        prompt_hints = (
            (
                "STATE_WAIT_ANALYSIS_REVIEW",
                "Continue with Y, provide guidance with N, rewind to Phase 1 with P1",
            ),
            (
                "STATE_WAIT_ANALYSIS_REVIEW",
                "Describe why this should go back to Phase 1:",
            ),
            (
                "STATE_WAIT_PAPER_REVIEW",
                "Continue repair with Y, provide guidance with N, rewind to Phase 2 with B",
            ),
            (
                "STATE_WAIT_PAPER_REVIEW",
                "Describe what should be revisited in Phase 2:",
            ),
            (
                "STATE_WAIT_PAPER_TEMPLATE_REVIEW",
                "Continue export with Y, provide guidance with N, rewind to Phase 2 with B",
            ),
            (
                "STATE_WAIT_PAPER_TEMPLATE_REVIEW",
                "Describe what should be revisited in Phase 2:",
            ),
        )
        for state, marker in prompt_hints:
            if marker in text:
                self.review_state_hint = state
                self.current_state = state
                self.state_label.setText(f"State: {state}")
                self.prompt_label.setText(f"Prompt: {marker}")
                self._update_review_controls()
                self.status_bar.showMessage(state)
                return

    def _set_state_label(self, state: str) -> None:
        self.state_label.setText(f"State: {state}")
        self.current_state = state
        self.review_state_hint = state if state.startswith("STATE_WAIT_") else "idle"
        self._update_review_controls()
        self.status_bar.showMessage(state)

    def _update_review_controls(self) -> None:
        effective_state = self.current_state
        if effective_state not in {
            "STATE_WAIT_ANALYSIS_REVIEW",
            "STATE_WAIT_PAPER_REVIEW",
            "STATE_WAIT_PAPER_TEMPLATE_REVIEW",
        } and self.review_state_hint in {
            "STATE_WAIT_ANALYSIS_REVIEW",
            "STATE_WAIT_PAPER_REVIEW",
            "STATE_WAIT_PAPER_TEMPLATE_REVIEW",
        }:
            effective_state = self.review_state_hint
        if effective_state == "STATE_WAIT_ANALYSIS_REVIEW":
            can_rewind = True
            self.back_action_token = "P1"
            self.b_button.setText("Back P1")
            self.b_button.setToolTip("Rewind from Phase 2 review back to Phase 1.")
        elif effective_state in {"STATE_WAIT_PAPER_REVIEW", "STATE_WAIT_PAPER_TEMPLATE_REVIEW"}:
            can_rewind = True
            self.back_action_token = "P2"
            self.b_button.setText("Back P2")
            self.b_button.setToolTip("Rewind from Phase 3 review back to Phase 2.")
        else:
            can_rewind = False
            self.back_action_token = ""
            self.b_button.setText("Back")
            self.b_button.setToolTip("Rewind from a review checkpoint.")
        self.b_button.setEnabled(can_rewind)

    def _set_input_mode(self, mode: str) -> None:
        self.current_mode = mode
        self.mode_label.setText(f"Input mode: {mode}")
        self.input_stack.setCurrentIndex(1 if mode == "multiline" else 0)
        if mode == "multiline":
            self.multi_input.setFocus()
        else:
            self.single_input.setFocus()

    def _on_started(self) -> None:
        self.current_state = "idle"
        self.review_state_hint = "idle"
        self._update_review_controls()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.clear_workspace_button.setEnabled(False)
        self.clear_include_src_check.setEnabled(False)
        self.clear_purge_install_check.setEnabled(False)
        label = {
            "clear-hard-install": "Clear+src+install",
            "clear-hard": "Clear+src",
            "clear-install": "Clear+install",
            "clear": "Clear",
        }.get(self.bridge.job_kind, "Workflow")
        self.status_bar.showMessage(f"{label} started.")
        self._append_output(f"[GUI] {label} started.\n")

    def _on_finished(self, exit_code: int) -> None:
        self.current_state = "idle"
        self.review_state_hint = "idle"
        self._update_review_controls()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.clear_workspace_button.setEnabled(True)
        self.clear_include_src_check.setEnabled(True)
        self.clear_purge_install_check.setEnabled(True)
        label = {
            "clear-hard-install": "Clear+src+install",
            "clear-hard": "Clear+src",
            "clear-install": "Clear+install",
            "clear": "Clear",
        }.get(self.bridge.job_kind, "Workflow")
        self.status_bar.showMessage(f"{label} finished with exit code {exit_code}.")
        self._append_output(f"\n[GUI] {label} finished with exit code {exit_code}.\n")

    def _on_failed(self, message: str) -> None:
        self.current_state = "idle"
        self.review_state_hint = "idle"
        self._update_review_controls()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.clear_workspace_button.setEnabled(True)
        self.clear_include_src_check.setEnabled(True)
        self.clear_purge_install_check.setEnabled(True)
        self.status_bar.showMessage(message)
        self._append_output(f"\n[GUI] {message}\n")


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv or sys.argv)
    app.setOrganizationName(APP_ORG)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
