import sys
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QTableWidget, QTableWidgetItem,
    QTabWidget, QSplitter, QGroupBox, QGridLayout, QHeaderView,
    QFileDialog, QMessageBox, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from parser import parse_program
from simulator import Simulator


CLR_ISSUED  = QColor("#fff3cd")
CLR_EXECUTE = QColor("#cce5ff")
CLR_WRITE   = QColor("#d4edda")
CLR_IDLE    = QColor("#f8f9fa")


def _item(text: str, bg: QColor | None = None) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    if bg:
        it.setBackground(bg)
    return it


def _make_table(headers: list[str]) -> QTableWidget:
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.verticalHeader().setDefaultSectionSize(22)
    t.verticalHeader().setVisible(False)
    return t


# ── main window ───────────────────────────────────────────────────────────
class FemTomasGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.sim: Simulator | None = None
        self._raw_payload: dict | None = None
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._do_step)

        self.setWindowTitle("femTomas — Tomasulo Algorithm Simulator")
        self.resize(1500, 900)
        self._build_ui()
        self._apply_stylesheet()

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("toolbar")
        toolbar_widget.setFixedHeight(52)
        toolbar_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tb_lay = QHBoxLayout(toolbar_widget)
        tb_lay.setContentsMargins(10, 8, 10, 8)
        tb_lay.setSpacing(8)

        self.btn_open  = self._btn("📂  Open JSON",  self._load_json_file)
        self.btn_parse = self._btn("⚙  Parse Text",  self._load_from_text)
        self.btn_step  = self._btn("⏭  Step",        self._do_step,    enabled=False)
        self.btn_run   = self._btn("▶  Run",          self._toggle_run, enabled=False)
        self.btn_reset = self._btn("↺  Reset",        self._reset,      enabled=False)

        self.lbl_cycle = QLabel("Cycle: —")
        self.lbl_cycle.setFont(QFont("Menlo", 13, QFont.Weight.Bold))

        tb_lay.addWidget(self.btn_open)
        tb_lay.addWidget(self.btn_parse)
        tb_lay.addSpacing(12)
        tb_lay.addWidget(self.btn_step)
        tb_lay.addWidget(self.btn_run)
        tb_lay.addWidget(self.btn_reset)
        tb_lay.addSpacing(20)
        tb_lay.addWidget(self.lbl_cycle)
        tb_lay.addStretch()

        outer.addWidget(toolbar_widget)

        # ── status bar ───────────────────────────────────────────────────────
        self.lbl_status = QLabel("  Load a JSON program file or paste JSON into the editor, then click Parse.")
        self.lbl_status.setObjectName("statusBar")
        self.lbl_status.setFixedHeight(28)
        self.lbl_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        outer.addWidget(self.lbl_status)

        # ── main splitter (takes ALL remaining space) ─────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([480, 1020])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        outer.addWidget(splitter, 1)   # ← stretch=1 fills the window

    # ── left panel ───────────────────────────────────────────────────────────
    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setObjectName("leftPanel")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 8, 6, 8)
        lay.setSpacing(8)

        # JSON editor
        grp_input = QGroupBox("Program Input  (JSON)")
        gi = QVBoxLayout(grp_input)
        gi.setSpacing(6)
        self.txt_json = QTextEdit()
        self.txt_json.setFont(QFont("Menlo", 10))
        self.txt_json.setMinimumHeight(160)
        self.txt_json.setMaximumHeight(220)
        self.txt_json.setPlaceholderText(
            '{\n'
            '  "instructions": [\n'
            '    {"pc": 0, "text": "ADD r1, r2, r3"},\n'
            '    {"pc": 1, "text": "MUL r4, r1, r2"}\n'
            '  ],\n'
            '  "memory": [\n'
            '    {"address": 100, "value": 42}\n'
            '  ]\n'
            '}'
        )
        gi.addWidget(self.txt_json)
        lay.addWidget(grp_input)

        # Instruction timing table
        grp_timing = QGroupBox("Instruction Timing Table")
        gt = QVBoxLayout(grp_timing)
        self.tbl_timing = _make_table(["PC", "Instruction", "Issued", "Exec Start", "Exec End", "Write"])
        gt.addWidget(self.tbl_timing)
        lay.addWidget(grp_timing, 1)   # stretch so it grows

        # Performance metrics
        grp_m = QGroupBox("Performance Metrics")
        gm = QGridLayout(grp_m)
        gm.setSpacing(6)
        mono = QFont("Menlo", 10)
        self.lbl_cycles   = QLabel("Total Cycles: —")
        self.lbl_ipc      = QLabel("IPC: —")
        self.lbl_instr    = QLabel("Instructions Done: —")
        self.lbl_branches = QLabel("Branches: —")
        self.lbl_mispred  = QLabel("Mispredictions: —")
        self.lbl_mispct   = QLabel("Misprediction %: —")
        for lbl in (self.lbl_cycles, self.lbl_ipc, self.lbl_instr,
                    self.lbl_branches, self.lbl_mispred, self.lbl_mispct):
            lbl.setFont(mono)
        gm.addWidget(self.lbl_cycles,   0, 0)
        gm.addWidget(self.lbl_ipc,      0, 1)
        gm.addWidget(self.lbl_instr,    1, 0)
        gm.addWidget(self.lbl_branches, 1, 1)
        gm.addWidget(self.lbl_mispred,  2, 0)
        gm.addWidget(self.lbl_mispct,   2, 1)
        lay.addWidget(grp_m)

        return w

    # ── right panel (tabs) ───────────────────────────────────────────────────
    def _build_right_panel(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # Tab 1 – Reservation Stations
        self.tbl_rs = _make_table(
            ["Station", "Busy", "Op", "Vj", "Vk", "Qj", "Qk",
             "Address", "Rem Cycles", "Stage"]
        )
        tabs.addTab(self.tbl_rs, "🗂  Reservation Stations")

        # Tab 2 – Registers
        reg_w = QWidget()
        rl = QVBoxLayout(reg_w)
        rl.setContentsMargins(10, 8, 10, 8)
        rl.setSpacing(10)

        grp_rf = QGroupBox("Register File  (current values)")
        grf = QVBoxLayout(grp_rf)
        self.tbl_rf = QTableWidget(1, 8)
        self.tbl_rf.setHorizontalHeaderLabels([f"R{i}" for i in range(8)])
        self.tbl_rf.setVerticalHeaderLabels(["Value"])
        self.tbl_rf.setFixedHeight(68)
        self.tbl_rf.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_rf.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_rf.setAlternatingRowColors(True)
        grf.addWidget(self.tbl_rf)
        rl.addWidget(grp_rf)

        grp_rs = QGroupBox("Register Status  (pending producer station)")
        grs = QVBoxLayout(grp_rs)
        self.tbl_reg_status = QTableWidget(1, 8)
        self.tbl_reg_status.setHorizontalHeaderLabels([f"R{i}" for i in range(8)])
        self.tbl_reg_status.setVerticalHeaderLabels(["Producer"])
        self.tbl_reg_status.setFixedHeight(68)
        self.tbl_reg_status.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_reg_status.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_reg_status.setAlternatingRowColors(True)
        grs.addWidget(self.tbl_reg_status)
        rl.addWidget(grp_rs)
        rl.addStretch()
        tabs.addTab(reg_w, "📋  Registers")

        # Tab 3 – Memory
        mem_w = QWidget()
        ml = QVBoxLayout(mem_w)
        ml.setContentsMargins(0, 0, 0, 0)
        self.tbl_mem = _make_table(["Address (dec)", "Address (hex)", "Value (dec)", "Value (hex)"])
        ml.addWidget(self.tbl_mem)
        tabs.addTab(mem_w, "💾  Memory")

        return tabs

    def _load_json_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Program JSON", "", "JSON Files (*.json);;All Files (*)"
        )
        if path:
            with open(path, "r", encoding="utf-8") as fh:
                self.txt_json.setPlainText(fh.read())
            self._load_from_text()

    def _load_from_text(self):
        text = self.txt_json.toPlainText().strip()
        if not text:
            self._status("⚠  Editor is empty — paste JSON or open a file.")
            return
        try:
            payload = json.loads(text)
            instrs, mem_init = parse_program(payload)
            self._raw_payload = payload
            self.sim = Simulator(instrs, mem_init)
            n = len(instrs)
            self.btn_step.setEnabled(True)
            self.btn_run.setEnabled(True)
            self.btn_reset.setEnabled(True)
            self._status(f"✅  Loaded {n} instruction{'s' if n != 1 else ''}. "
                         "Press  Step  to advance one cycle, or  Run  to animate.")
            self._refresh_all()
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON Parse Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _do_step(self):
        if self.sim is None or self.sim.is_done():
            self._auto_timer.stop()
            self.btn_run.setText("▶  Run")
            self._status("🏁  Simulation complete!")
            self._refresh_metrics()
            return
        self.sim.step()
        self._refresh_all()
        if self.sim.is_done():
            self._auto_timer.stop()
            self.btn_run.setText("▶  Run")
            self._status("🏁  Simulation complete!")

    def _toggle_run(self):
        if self._auto_timer.isActive():
            self._auto_timer.stop()
            self.btn_run.setText("▶  Run")
        else:
            self._auto_timer.start(300)
            self.btn_run.setText("⏸  Pause")

    def _reset(self):
        self._auto_timer.stop()
        self.btn_run.setText("▶  Run")
        if self._raw_payload:
            try:
                instrs, mem_init = parse_program(self._raw_payload)
                self.sim = Simulator(instrs, mem_init)
                self._status("↺  Reset complete. Press Step or Run to begin again.")
                self._refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _refresh_all(self):
        if self.sim is None:
            return
        self.lbl_cycle.setText(f"Cycle: {self.sim.cycle}")
        self._refresh_timing()
        self._refresh_rs()
        self._refresh_registers()
        self._refresh_memory()
        if self.sim.is_done():
            self._refresh_metrics()

    def _refresh_timing(self):
        rows = self.sim.instructions
        self.tbl_timing.setRowCount(len(rows))
        for r, instr in enumerate(rows):
            bg = (CLR_WRITE   if instr.completed   else
                  CLR_EXECUTE if instr.start_cycle  else
                  CLR_ISSUED  if instr.issued_cycle else None)
            for c, v in enumerate([
                instr.pc,
                instr.raw_text,
                instr.issued_cycle  or "—",
                instr.start_cycle   or "—",
                instr.finish_cycle  or "—",
                instr.write_cycle   or "—",
            ]):
                self.tbl_timing.setItem(r, c, _item(v, bg))

    def _refresh_rs(self):
        slots = list(self.sim.get_all_slots())
        self.tbl_rs.setRowCount(len(slots))
        stage_color = {"ISSUE": CLR_ISSUED, "EXECUTE": CLR_EXECUTE, "WRITE": CLR_WRITE}

        for r, slot in enumerate(slots):
            # Keep your existing background logic
            bg = stage_color.get(slot.stage, CLR_IDLE) if slot.busy else CLR_IDLE

            vals = [
                slot.name,
                "Yes" if slot.busy else "No",
                (slot.instruction.mnemonic.upper() if slot.instruction else "—") if slot.busy else "—",
                slot.Vj if slot.Vj is not None else "—",
                slot.Vk if slot.Vk is not None else "—",
                slot.Qj or "—",
                slot.Qk or "—",
                slot.address if slot.address is not None else "—",
                slot.rem_cycles if (slot.busy and slot.rem_cycles is not None) else "—",
                slot.stage if slot.busy else "—",
            ]

            for c, v in enumerate(vals):
                # 1. Create the item using your helper
                item = _item(v, bg)

                # 2. If the slot is NOT busy, set the text (Foreground) to gray
                if not slot.busy:
                    item.setForeground(QColor("gray"))

                # 3. Add the item to the table
                self.tbl_rs.setItem(r, c, item)

    def _refresh_registers(self):
        for i in range(8):
            reg = f"r{i}"
            self.tbl_rf.setItem(0, i, _item(self.sim.registers.values[i]))
            producer = self.sim.registers.current_producer(reg)
            self.tbl_reg_status.setItem(
                0, i, _item(producer or "—", CLR_ISSUED if producer else None)
            )

    def _refresh_memory(self):
        entries = sorted(self.sim.memory.storage.items())
        self.tbl_mem.setRowCount(len(entries))
        for r, (addr, val) in enumerate(entries):
            self.tbl_mem.setItem(r, 0, _item(addr))
            self.tbl_mem.setItem(r, 1, _item(hex(addr)))
            self.tbl_mem.setItem(r, 2, _item(val))
            self.tbl_mem.setItem(r, 3, _item(hex(val & 0xFFFF)))

    def _refresh_metrics(self):
        sim = self.sim
        cycles   = sim.cycle
        done     = sim.completed_count
        ipc      = done / cycles if cycles else 0.0
        branches = sim.branch_count
        mis      = sim.mispredictions
        mispct   = mis / branches * 100 if branches else 0.0
        self.lbl_cycles.setText(f"Total Cycles: {cycles}")
        self.lbl_ipc.setText(f"IPC: {ipc:.3f}")
        self.lbl_instr.setText(f"Instructions Done: {done}")
        self.lbl_branches.setText(f"Branches: {branches}")
        self.lbl_mispred.setText(f"Mispredictions: {mis}")
        self.lbl_mispct.setText(f"Misprediction %: {mispct:.1f}%")


    def _status(self, msg: str):
        self.lbl_status.setText(f"  {msg}")

    @staticmethod
    def _btn(label: str, slot, enabled: bool = True) -> QPushButton:
        b = QPushButton(label)
        b.setEnabled(enabled)
        b.clicked.connect(slot)
        b.setMinimumWidth(120)
        b.setFixedHeight(34)
        return b

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #f0f2f5;
            }
            QWidget#toolbar {
                background-color: #1e1e2e;
                border-bottom: 2px solid #0d6efd;
            }
            QWidget#toolbar QLabel {
                color: #ffffff;
            }
            QWidget#leftPanel {
                background-color: #f0f2f5;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 4px;
                color: #495057;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover  { background-color: #0b5ed7; }
            QPushButton:pressed { background-color: #0a58ca; }
            QPushButton:disabled { background-color: #6c757d; color: #ced4da; }
            QTableWidget {
                background-color: white;
                gridline-color: #dee2e6;
                border: none;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #343a40;
                color: white;
                padding: 5px 4px;
                font-weight: bold;
                font-size: 11px;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #ced4da;
                background-color: white;
            }
            QTabBar::tab {
                padding: 7px 18px;
                font-weight: bold;
                font-size: 12px;
                background-color: #e9ecef;
                border: 1px solid #ced4da;
                border-bottom: none;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0d6efd;
                color: #0d6efd;
            }
            QLabel#statusBar {
                background-color: #e9ecef;
                color: #495057;
                border-bottom: 1px solid #ced4da;
                font-size: 12px;
                padding-left: 6px;
            }
            QTextEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 11px;
            }
            QSplitter::handle {
                background-color: #ced4da;
                width: 3px;
            }
        """)
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = FemTomasGUI()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()