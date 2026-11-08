#!/usr/bin/env python3
"""Stack — a small, local-first desktop PDF merger for Linux."""

from __future__ import annotations

import os
import tempfile
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)
from pypdf import PdfReader, PdfWriter


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


class PdfWorker(QObject):
    completed = Signal(bool, str)

    def __init__(self, task):
        super().__init__()
        self.task = task

    @Slot()
    def run(self):
        try:
            result = self.task()
        except Exception as exc:
            self.completed.emit(False, str(exc))
        else:
            self.completed.emit(True, str(result))


class StackWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stack — PDF Workbench")
        self.setWindowIcon(QIcon(str(Path(__file__).with_name("icon.svg"))))
        self.setMinimumSize(760, 760)
        self.resize(940, 920)
        self.setAcceptDrops(True)
        root = QWidget()
        root.setStyleSheet(f"background:{BG}; color:{INK};")
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(34, 24, 34, 24)
        page.setSpacing(0)

        top = QHBoxLayout()
        brand = QLabel("◧  STACK  /  PDF WORKBENCH")
        brand.setStyleSheet(f"font-size:13px; font-weight:800; letter-spacing:2px; color:{INK}; background:transparent;")
        top.addWidget(brand)
        top.addStretch()
        local = QLabel("●  ON THIS DEVICE")
        local.setStyleSheet(f"font-size:10px; font-weight:700; letter-spacing:1px; color:{MINT}; background:transparent;")
        top.addWidget(local)
        page.addLayout(top)
        page.addSpacing(34)

        title = QLabel(f"<span style='color:{INK}'>Make more of</span><br><span style='color:{ACCENT}'>your PDFs.</span>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setStyleSheet("font-size:42px; line-height:1.1; font-weight:750; letter-spacing:-1.5px; background:transparent;")
        page.addWidget(title)
        page.addSpacing(12)
        subtitle = QLabel("Merge, extract, split, rotate, optimize, and protect — all on this device.")
        subtitle.setStyleSheet(f"font-size:14px; color:{MUTED}; background:transparent;")
        page.addWidget(subtitle)
        page.addSpacing(19)
        steps = QLabel(f"<span style='color:{ACCENT}; font-weight:700'>01</span>  ADD A PDF   <span style='color:#555663'>›</span>   <span style='color:{ACCENT}; font-weight:700'>02</span>  CHOOSE A TOOL   <span style='color:#555663'>›</span>   <span style='color:{ACCENT}; font-weight:700'>03</span>  SAVE A COPY")
        steps.setTextFormat(Qt.TextFormat.RichText)
        steps.setStyleSheet(f"font-size:10px; letter-spacing:1px; color:{MUTED}; background:transparent;")
        page.addWidget(steps)
        page.addSpacing(20)

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
        self.file_stack = QStackedWidget()
        self.file_stack.addWidget(self.files)
        self.file_stack.addWidget(self.empty)
        page.addWidget(self.file_stack, 1)

        tools_title = QLabel("QUICK TOOLS  ·  SELECT ONE PDF")
        tools_title.setStyleSheet(f"font-size:10px; font-weight:800; letter-spacing:1.3px; color:{MUTED}; background:transparent;")
        page.addSpacing(16)
        page.addWidget(tools_title)
        page.addSpacing(8)
        tool_row = QHBoxLayout()
        tool_row.setSpacing(8)
        self.tool_buttons = []
        for label, action in (("Extract pages", self.extract_pages), ("Split into pages", self.split_pages),
                              ("Rotate", self.rotate_pages), ("Optimize", self.optimize_pdf), ("Protect", self.protect_pdf)):
            button = QPushButton(label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(f"QPushButton {{ background:{PANEL}; color:{INK}; border:1px solid {LINE}; border-radius:9px; padding:9px 11px; font-size:11px; font-weight:650; }} QPushButton:hover {{ background:{PANEL_HI}; border-color:{ACCENT}; color:{ACCENT}; }}")
            button.clicked.connect(action)
            tool_row.addWidget(button)
            self.tool_buttons.append(button)
        page.addLayout(tool_row)

        page.addSpacing(14)
        controls = QHBoxLayout()
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self.remove_selected)
        self.remove_button.setStyleSheet(f"QPushButton {{ background:transparent; border:0; color:{MUTED}; font-size:12px; padding:8px 0; }} QPushButton:hover {{ color:#ff858b; }}")
        controls.addWidget(self.remove_button)
        controls.addStretch()
        self.merge_button = QPushButton("Merge files   →")
        self.merge_button.clicked.connect(self.merge)
        self.merge_button.setMinimumWidth(170)
        self.merge_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.merge_button.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:#171321; border:0; border-radius:11px; padding:14px 18px; font-size:13px; font-weight:800; }} QPushButton:hover {{ background:#b2a5ff; }} QPushButton:disabled {{ background:#34323e; color:#777583; }}")
        controls.addWidget(self.merge_button)
        page.addLayout(controls)
        page.addSpacing(20)
        self.footer = QLabel("Originals stay untouched  ·  Drag to reorder  ·  No uploads")
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
        self.file_stack.setCurrentWidget(self.empty if count == 0 else self.files)
        self.merge_button.setEnabled(count >= 2)
        self.remove_button.setEnabled(self.files.currentItem() is not None)
        for button in self.tool_buttons:
            button.setEnabled(self.files.currentItem() is not None)

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
        passwords = {}
        for source in paths:
            password = self.ask_source_password(source)
            if password is None:
                return
            passwords[source] = password
        self.start_task("Merging files…", lambda: self.merge_files(paths, str(out), passwords), self._merge_completed)

    def selected_pdf(self):
        item = self.files.currentItem()
        if item is None:
            QMessageBox.information(self, "Select a PDF", "Choose one PDF in the file list first.")
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def ask_source_password(self, path):
        try:
            reader = PdfReader(path, strict=False)
            encrypted = reader.is_encrypted
            reader.close()
        except Exception as exc:
            QMessageBox.critical(self, "Could not read PDF", str(exc))
            return None
        if not encrypted:
            return ""
        password, accepted = QInputDialog.getText(self, "Unlock PDF", f"Enter the password for {Path(path).name}:", QLineEdit.EchoMode.Password)
        return password if accepted else None

    @staticmethod
    def open_reader(path, password=""):
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted and not reader.decrypt(password):
            reader.close()
            raise ValueError(f"The password for {Path(path).name} was not accepted.")
        return reader

    @staticmethod
    def page_indexes(spec, total):
        indexes = []
        for raw in spec.split(","):
            token = raw.strip().lower()
            if not token:
                continue
            if "-" in token:
                left, right = token.split("-", 1)
                start = int(left) if left else 1
                end = total if right in ("", "end", "last") else int(right)
            else:
                start = end = int(token)
            if start < 1 or end < start or end > total:
                raise ValueError(f"Page range {raw.strip()!r} is outside 1–{total}.")
            indexes.extend(range(start - 1, end))
        if not indexes:
            raise ValueError("Enter at least one page, such as 1-3, 5, 8-end.")
        return indexes

    @staticmethod
    def safe_write(writer, output, inputs=()):
        output = Path(output).expanduser().resolve()
        if any(Path(source).expanduser().resolve() == output for source in inputs):
            raise ValueError("Choose a new destination. Original PDFs are never overwritten.")
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
        os.close(fd)
        try:
            with open(temporary, "wb") as stream:
                writer.write(stream)
            os.replace(temporary, output)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return str(output)

    def page_range_dialog(self, path, title):
        password = self.ask_source_password(path)
        if password is None:
            return None
        try:
            reader = self.open_reader(path, password)
            count = len(reader.pages)
            reader.close()
        except Exception as exc:
            QMessageBox.critical(self, "Could not open PDF", str(exc))
            return None
        spec, accepted = QInputDialog.getText(self, title, f"Pages (1–{count}) · examples: 1-3, 5, 8-end", text=f"1-{count}")
        return (spec, password) if accepted else None

    def extract_pages(self):
        path = self.selected_pdf()
        if not path: return
        answer = self.page_range_dialog(path, "Extract pages")
        if answer is None: return
        spec, password = answer
        output, _ = QFileDialog.getSaveFileName(self, "Save extracted pages", str(Path(path).with_name(f"{Path(path).stem}-pages.pdf")), "PDF files (*.pdf)")
        if not output: return
        if not output.lower().endswith(".pdf"): output += ".pdf"
        self.start_task("Extracting pages…", lambda: self.write_selected_pages(path, output, spec, password))

    def write_selected_pages(self, path, output, spec, password=""):
        reader = self.open_reader(path, password); writer = PdfWriter()
        try:
            for index in self.page_indexes(spec, len(reader.pages)):
                writer.add_page(reader.pages[index])
            writer.add_metadata({"/Title": f"Pages from {Path(path).name}"})
            return self.safe_write(writer, output, [path])
        finally:
            reader.close(); writer.close()

    def split_pages(self):
        path = self.selected_pdf()
        if not path: return
        password = self.ask_source_password(path)
        if password is None: return
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder for split pages", str(Path(path).parent))
        if not folder: return
        self.start_task("Splitting PDF…", lambda: self.split_pdf(path, folder, password))

    def split_pdf(self, path, folder, password=""):
        reader = self.open_reader(path, password); outputs = []
        try:
            paths = [Path(folder) / f"{Path(path).stem}-page-{number:03}.pdf" for number in range(1, len(reader.pages) + 1)]
            conflict = next((target for target in paths if target.exists()), None)
            if conflict:
                raise FileExistsError(f"A split output already exists: {conflict}")
            for target, page in zip(paths, reader.pages):
                writer = PdfWriter(); writer.add_page(page)
                outputs.append(self.safe_write(writer, target, [path])); writer.close()
        finally:
            reader.close()
        return f"{len(outputs)} pages saved in {folder}"

    def rotate_pages(self):
        path = self.selected_pdf()
        if not path: return
        answer = self.page_range_dialog(path, "Rotate pages")
        if answer is None: return
        spec, password = answer
        degrees, accepted = QInputDialog.getItem(self, "Rotate pages", "Clockwise rotation", ["90°", "180°", "270°"], 0, False)
        if not accepted: return
        output, _ = QFileDialog.getSaveFileName(self, "Save rotated PDF", str(Path(path).with_name(f"{Path(path).stem}-rotated.pdf")), "PDF files (*.pdf)")
        if not output: return
        if not output.lower().endswith(".pdf"): output += ".pdf"
        self.start_task("Rotating pages…", lambda: self.rotate_pdf(path, output, spec, int(degrees[:-1]), password))

    def rotate_pdf(self, path, output, spec, degrees, password=""):
        reader = self.open_reader(path, password); writer = PdfWriter()
        try:
            selected = set(self.page_indexes(spec, len(reader.pages)))
            for index, page in enumerate(reader.pages):
                if index in selected: page.rotate(degrees)
                writer.add_page(page)
            return self.safe_write(writer, output, [path])
        finally:
            reader.close(); writer.close()

    def optimize_pdf(self):
        path = self.selected_pdf()
        if not path: return
        output, _ = QFileDialog.getSaveFileName(self, "Save optimized PDF", str(Path(path).with_name(f"{Path(path).stem}-optimized.pdf")), "PDF files (*.pdf)")
        if not output: return
        if not output.lower().endswith(".pdf"): output += ".pdf"
        password = self.ask_source_password(path)
        if password is None: return
        self.start_task("Optimizing PDF…", lambda: self.optimize_pdf_file(path, output, password))

    def optimize_pdf_file(self, path, output, password=""):
        reader = self.open_reader(path, password); writer = PdfWriter()
        try:
            writer.append(reader)
            for page in writer.pages: page.compress_content_streams()
            writer.compress_identical_objects(remove_identicals=True, remove_unreferenced=True)
            return self.safe_write(writer, output, [path])
        finally:
            reader.close(); writer.close()

    def protect_pdf(self):
        path = self.selected_pdf()
        if not path: return
        source_password = self.ask_source_password(path)
        if source_password is None: return
        password, accepted = QInputDialog.getText(self, "Protect PDF", "New password for the output PDF:", QLineEdit.EchoMode.Password)
        if not accepted: return
        if len(password) < 4:
            QMessageBox.warning(self, "Choose a longer password", "Use at least four characters for the PDF password.")
            return
        confirm, accepted = QInputDialog.getText(self, "Confirm password", "Enter the new password again:", QLineEdit.EchoMode.Password)
        if not accepted: return
        if password != confirm:
            QMessageBox.warning(self, "Passwords do not match", "Enter the same password twice.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save protected PDF", str(Path(path).with_name(f"{Path(path).stem}-protected.pdf")), "PDF files (*.pdf)")
        if not output: return
        if not output.lower().endswith(".pdf"): output += ".pdf"
        self.start_task("Protecting PDF…", lambda: self.protect_pdf_file(path, output, source_password, password))

    def protect_pdf_file(self, path, output, source_password, new_password):
        reader = self.open_reader(path, source_password); writer = PdfWriter()
        try:
            writer.append(reader); writer.encrypt(user_password=new_password, algorithm="AES-256")
            return self.safe_write(writer, output, [path])
        finally:
            reader.close(); writer.close()

    def start_task(self, busy_text, task, completed=None):
        self._set_busy(True)
        self.merge_thread = QThread(self)
        self.merge_worker = PdfWorker(task)
        self.merge_worker.moveToThread(self.merge_thread)
        self.merge_thread.started.connect(self.merge_worker.run)
        self.merge_worker.completed.connect(completed or self.operation_completed)
        self.merge_worker.completed.connect(self.merge_thread.quit)
        self.merge_worker.completed.connect(self.merge_worker.deleteLater)
        self.merge_thread.finished.connect(self.merge_thread.deleteLater)
        self.merge_thread.finished.connect(self._merge_thread_finished)
        self.merge_button.setText(busy_text)
        self.merge_thread.start()

    def operation_completed(self, success, detail):
        self._set_busy(False)
        if not success:
            QMessageBox.critical(self, "PDF action failed", detail)
            return
        result = Path(detail)
        if result.is_file():
            answer = QMessageBox.information(self, "PDF saved", f"Saved {result.name}\n\n{result}", QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Close, QMessageBox.StandardButton.Open)
            if answer == QMessageBox.StandardButton.Open:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(result)))
        else:
            QMessageBox.information(self, "PDFs ready", detail, QMessageBox.StandardButton.Ok)

    def _set_busy(self, busy):
        self.add_button.setEnabled(not busy)
        self.remove_button.setEnabled(not busy and self.files.currentItem() is not None)
        self.files.setEnabled(not busy)
        self.merge_button.setEnabled(not busy and self.files.count() >= 2)
        for button in self.tool_buttons:
            button.setEnabled(not busy and self.files.currentItem() is not None)
        self.merge_button.setText("Working…" if busy else "Merge files   →")
        self.footer.setText("Working locally · You can keep using your desktop" if busy
                            else "Originals stay untouched  ·  Drag to reorder  ·  No uploads")

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
            QMessageBox.information(self, "PDF task in progress", "Keep Stack open until the local PDF task finishes.")
            event.ignore()
            return
        super().closeEvent(event)

    @staticmethod
    def merge_files(paths, output, passwords=None):
        passwords = passwords or {}
        writer = PdfWriter()
        readers = []
        try:
            for source in paths:
                reader = StackWindow.open_reader(source, passwords.get(source, "")); readers.append(reader)
                writer.append(reader)
            return StackWindow.safe_write(writer, output, paths)
        finally:
            for reader in readers: reader.close()
            writer.close()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Stack PDF Workbench")
    app.setOrganizationName("Stack")
    app.setFont(QFont("Inter", 10))
    app.setStyle("Fusion")
    window = StackWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
