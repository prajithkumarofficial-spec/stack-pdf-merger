#!/usr/bin/env python3
"""Stack — a small, local-first desktop PDF merger for Linux."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)


BG = "#101116"
PANEL = "#191a22"
PANEL_HI = "#20212b"
INK = "#f2f1fa"
MUTED = "#9697a8"
LINE = "#2d2e3a"
ACCENT = "#9582ff"
MINT = "#78edc2"


class FileList(QListWidget):
    def __init__(self, changed):
        super().__init__()
        self.changed = changed
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setSpacing(7)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QListWidget {{ background: transparent; outline: none; }}
            QListWidget::item {{ background: {PANEL}; border: 1px solid {LINE};
                border-radius: 12px; padding: 12px 14px; color: {INK}; }}
            QListWidget::item:hover {{ background: {PANEL_HI}; border-color: #414151; }}
            QListWidget::item:selected {{ background: #29243e; border-color: {ACCENT}; }}
        """)
        self.model().rowsMoved.connect(lambda *_: self.changed())

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            self.window().add_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class MergeWorker(QObject):
    completed = Signal(bool, str)

    def __init__(self, paths, output):
        super().__init__()
        self.paths = paths
        self.output = output

    @Slot()
    def run(self):
        try:
            StackWindow.merge_files(self.paths, self.output)
        except Exception as exc:
            self.completed.emit(False, str(exc))
        else:
            self.completed.emit(True, self.output)


class StackWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stack — PDF merger")
        self.setWindowIcon(QIcon(str(Path(__file__).with_name("icon.svg"))))
        self.setMinimumSize(680, 700)
        self.resize(760, 800)
        self.setAcceptDrops(True)
        root = QWidget()
        root.setStyleSheet(f"background:{BG}; color:{INK};")
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(44, 30, 44, 30)
        page.setSpacing(0)

        top = QHBoxLayout()
        brand = QLabel("◧  STACK")
        brand.setStyleSheet(f"font-size:13px; font-weight:800; letter-spacing:2px; color:{INK}; background:transparent;")
        top.addWidget(brand)
        top.addStretch()
        local = QLabel("●  ON THIS DEVICE")
        local.setStyleSheet(f"font-size:10px; font-weight:700; letter-spacing:1px; color:{MINT}; background:transparent;")
        top.addWidget(local)
        page.addLayout(top)
        page.addSpacing(54)

        title = QLabel(f"<span style='color:{INK}'>Bring your PDFs</span><br><span style='color:{ACCENT}'>together.</span>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setStyleSheet("font-size:42px; line-height:1.1; font-weight:750; letter-spacing:-1.5px; background:transparent;")
        page.addWidget(title)
        page.addSpacing(12)
        subtitle = QLabel("Arrange your files in order, then merge them into one PDF.")
        subtitle.setStyleSheet(f"font-size:14px; color:{MUTED}; background:transparent;")
        page.addWidget(subtitle)
        page.addSpacing(19)
        steps = QLabel(f"<span style='color:{ACCENT}; font-weight:700'>01</span>  ADD FILES   <span style='color:#555663'>›</span>   <span style='color:{ACCENT}; font-weight:700'>02</span>  SET ORDER   <span style='color:#555663'>›</span>   <span style='color:{ACCENT}; font-weight:700'>03</span>  MERGE")
        steps.setTextFormat(Qt.TextFormat.RichText)
        steps.setStyleSheet(f"font-size:10px; letter-spacing:1px; color:{MUTED}; background:transparent;")
        page.addWidget(steps)
        page.addSpacing(27)

        section = QHBoxLayout()
        self.count = QLabel("YOUR FILES  ·  0")
        self.count.setStyleSheet(f"font-size:10px; font-weight:800; letter-spacing:1.3px; color:{MUTED}; background:transparent;")
        section.addWidget(self.count)
        section.addStretch()
        self.add_button = QPushButton("＋  Add PDFs")
        self.add_button.clicked.connect(self.pick_files)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.setStyleSheet(f"QPushButton {{ background:{PANEL}; color:{INK}; border:1px solid {LINE}; border-radius:10px; padding:10px 15px; font-size:12px; font-weight:650; }} QPushButton:hover {{ background:{PANEL_HI}; border-color:{ACCENT}; color:{ACCENT}; }}")
        section.addWidget(self.add_button)
        page.addLayout(section)
        page.addSpacing(12)

        self.files = FileList(self.update_count)
        self.files.itemSelectionChanged.connect(self.update_count)
        page.addWidget(self.files, 1)

        self.empty = QFrame()
        self.empty.setStyleSheet(f"QFrame {{ border:1.5px dashed #414151; border-radius:18px; background:{PANEL}; }}")
        empty_layout = QVBoxLayout(self.empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("↥")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"font-size:29px; color:{ACCENT}; background:transparent;")
        empty_layout.addWidget(icon)
        hint = QLabel("Drop your PDF files here")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"font-size:15px; font-weight:650; color:{INK}; background:transparent;")
        empty_layout.addWidget(hint)
        note = QLabel("or use Add PDFs to browse your files")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(f"font-size:12px; color:{MUTED}; background:transparent;")
        empty_layout.addWidget(note)
        self.files.setMinimumHeight(250)
        page.addWidget(self.empty)

        page.addSpacing(14)
        controls = QHBoxLayout()
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self.remove_selected)
        self.remove_button.setStyleSheet(f"QPushButton {{ background:transparent; border:0; color:{MUTED}; font-size:12px; padding:8px 0; }} QPushButton:hover {{ color:#ff858b; }}")
        controls.addWidget(self.remove_button)
        controls.addStretch()
        self.merge_button = QPushButton("Merge PDFs   →")
        self.merge_button.clicked.connect(self.merge)
        self.merge_button.setMinimumWidth(170)
        self.merge_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.merge_button.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:#171321; border:0; border-radius:11px; padding:14px 18px; font-size:13px; font-weight:800; }} QPushButton:hover {{ background:#b2a5ff; }} QPushButton:disabled {{ background:#34323e; color:#777583; }}")
        controls.addWidget(self.merge_button)
        page.addLayout(controls)
        page.addSpacing(20)
        self.footer = QLabel("PDFs stay on your device  ·  Drag to reorder  ·  No uploads")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer.setStyleSheet(f"font-size:11px; color:{MUTED}; background:transparent;")
        page.addWidget(self.footer)
        self.merge_thread = None
        self.merge_worker = None
        self.update_count()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        self.add_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
        event.acceptProposedAction()

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add PDF files", "", "PDF files (*.pdf)")
        self.add_paths(paths)

    def add_paths(self, paths):
        existing = {self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())}
        for raw in paths:
            path = Path(raw).expanduser()
            if path.suffix.lower() != ".pdf" or not path.is_file() or str(path) in existing:
                continue
            item = QListWidgetItem(f"▤    {path.name}\n       {path.parent}  ·  {self.format_size(path.stat().st_size)}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setSizeHint(item.sizeHint().__class__(item.sizeHint().width(), 62))
            item.setToolTip(str(path))
            self.files.addItem(item)
            existing.add(str(path))
        self.update_count()

    @staticmethod
    def format_size(size):
        if size < 1_000_000:
            return f"{max(1, size // 1000)} KB"
        return f"{size / 1_000_000:.1f} MB"

    def update_count(self):
        count = self.files.count()
        self.count.setText(f"YOUR FILES  ·  {count}")
        self.empty.setVisible(count == 0)
        self.files.setVisible(count > 0)
        self.merge_button.setEnabled(count >= 2)
        self.remove_button.setEnabled(self.files.currentItem() is not None)

    def remove_selected(self):
        row = self.files.currentRow()
        if row >= 0:
            self.files.takeItem(row)
        self.update_count()

    def merge(self):
        paths = [self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())]
        if len(paths) < 2:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save merged PDF", str(Path(paths[0]).parent / "merged.pdf"), "PDF files (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        out = Path(path)
        if any(Path(p).resolve() == out.resolve() for p in paths):
            QMessageBox.warning(self, "Choose another destination", "The output file cannot replace one of the PDFs being merged.")
            return
        self._set_busy(True)
        self.merge_thread = QThread(self)
        self.merge_worker = MergeWorker(paths, str(out))
        self.merge_worker.moveToThread(self.merge_thread)
        self.merge_thread.started.connect(self.merge_worker.run)
        self.merge_worker.completed.connect(self._merge_completed)
        self.merge_worker.completed.connect(self.merge_thread.quit)
        self.merge_worker.completed.connect(self.merge_worker.deleteLater)
        self.merge_thread.finished.connect(self.merge_thread.deleteLater)
        self.merge_thread.finished.connect(self._merge_thread_finished)
        self.merge_thread.start()

    def _set_busy(self, busy):
        self.add_button.setEnabled(not busy)
        self.remove_button.setEnabled(not busy and self.files.currentItem() is not None)
        self.files.setEnabled(not busy)
        self.merge_button.setEnabled(not busy and self.files.count() >= 2)
        self.merge_button.setText("Merging…" if busy else "Merge PDFs   →")
        self.footer.setText("Merging locally · You can keep using your desktop" if busy
                            else "PDFs stay on your device  ·  Drag to reorder  ·  No uploads")

    def _merge_completed(self, success, detail):
        self._set_busy(False)
        if not success:
            QMessageBox.critical(self, "Could not merge PDFs", detail)
            return
        out = Path(detail)
        answer = QMessageBox.information(
            self, "Your PDFs are together", f"Saved {out.name}\n\n{out}",
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Close,
            QMessageBox.StandardButton.Open,
        )
        if answer == QMessageBox.StandardButton.Open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(out)))

    def _merge_thread_finished(self):
        self.merge_thread = None
        self.merge_worker = None

    def closeEvent(self, event):
        if self.merge_thread is not None and self.merge_thread.isRunning():
            QMessageBox.information(self, "Merge in progress", "Keep Stack open until the local merge finishes.")
            event.ignore()
            return
        super().closeEvent(event)

    @staticmethod
    def merge_files(paths, output):
        if shutil.which("pdfunite"):
            result = subprocess.run(["pdfunite", *paths, output], capture_output=True, text=True)
            if result.returncode == 0:
                return
            raise RuntimeError((result.stderr or result.stdout or "pdfunite could not read one of the files.").strip())
        try:
            from pypdf import PdfWriter
        except ImportError as exc:
            raise RuntimeError("Install Poppler (pdfunite) or run `python -m pip install -r requirements.txt` to enable merging.") from exc
        writer = PdfWriter()
        try:
            for source in paths:
                writer.append(source)
            with open(output, "wb") as stream:
                writer.write(stream)
        finally:
            writer.close()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Stack PDF Merger")
    app.setOrganizationName("Stack")
    app.setFont(QFont("Inter", 10))
    app.setStyle("Fusion")
    window = StackWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
