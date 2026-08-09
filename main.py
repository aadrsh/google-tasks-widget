import os
import sys
import threading
from datetime import datetime, date
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
                             QCheckBox, QScrollArea, QFrame, QHBoxLayout,
                             QSpacerItem, QSizePolicy, QPushButton, QLineEdit,
                             QComboBox, QDateEdit, QListView, QMenu, QAction,
                             QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QDate, QSize, QByteArray
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

# Import our auth & assets module
import base64
from auth import list_accounts, get_service, add_account, remove_account
from assets import EDIT_ICON_B64, DELETE_ICON_B64, PLUS_ICON_B64, REFRESH_ICON_B64

def get_b64_pixmap(b64_str):
    ba = QByteArray.fromBase64(b64_str.encode('utf-8'))
    pm = QPixmap()
    pm.loadFromData(ba)
    return pm

# Fix: QComboBox dropdown white corner issue — set the view background to match
# and add an explicit background on QScrollBar inside the popup to avoid seeping white
COMBO_STYLE = """
    QComboBox {
        background-color: #2a2d32;
        color: white;
        border: 1px solid rgba(255, 255, 255, 30);
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 11px;
    }
    QComboBox:hover {
        border: 1px solid #4da8da;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
        background-color: transparent;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #4da8da;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #1e2124;
        color: white;
        selection-background-color: #4da8da;
        selection-color: white;
        border: 1px solid rgba(255, 255, 255, 50);
        border-radius: 0px;
        padding: 2px;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        padding: 5px 8px;
        border-radius: 0px;
        min-height: 24px;
        background-color: #1e2124;
    }
    QComboBox QAbstractItemView::item:selected {
        background-color: #4da8da;
        color: white;
    }
    QComboBox QScrollBar:vertical {
        background: #1e2124;
        width: 6px;
        margin: 0px;
    }
    QComboBox QScrollBar::handle:vertical {
        background: rgba(255, 255, 255, 80);
        border-radius: 3px;
    }
    QComboBox QScrollBar::add-line:vertical,
    QComboBox QScrollBar::sub-line:vertical {
        height: 0px;
    }
"""

MENU_STYLE = """
    QMenu {
        background-color: #1e2124;
        color: white;
        border: 1px solid rgba(255, 255, 255, 30);
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 16px;
        border-radius: 4px;
        font-size: 11px;
    }
    QMenu::item:selected {
        background-color: #4da8da;
        color: white;
    }
"""

def format_due_date(due_raw, recurrence=None):
    has_repeat = bool(recurrence)
    repeat_suffix = " 🔁" if has_repeat else ""

    if not due_raw:
        if has_repeat:
            return "🔁", "#888888"
        return None, None
    try:
        due_date = datetime.strptime(due_raw[:10], "%Y-%m-%d").date()
        today = date.today()
        diff = (due_date - today).days
        formatted_day = due_date.strftime('%b %d')

        if diff < 0:
            if diff == -1:
                return f"Yesterday ({formatted_day}){repeat_suffix}", "#ff6b6b"
            else:
                return f"Overdue ({formatted_day}){repeat_suffix}", "#ff6b6b"
        elif diff == 0:
            return f"Today ({formatted_day}){repeat_suffix}", "#4da8da"
        elif diff == 1:
            return f"Tomorrow ({formatted_day}){repeat_suffix}", "#a8e6cf"
        elif diff < 7:
            day_name = due_date.strftime('%A')
            return f"{day_name} ({formatted_day}){repeat_suffix}", "#dddddd"
        else:
            return f"{formatted_day}{repeat_suffix}", "#888888"
    except Exception:
        return f"{due_raw[:10]}{repeat_suffix}", "#888888"

class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class ImageButton(QWidget):
    """Custom icon button with proper color type tracking (no string hacking)."""
    clicked = pyqtSignal()

    # button_type: 'blue' for edit/action, 'red' for delete/danger
    def __init__(self, b64_icon, button_type='blue', tooltip="", parent=None):
        super().__init__(parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(26, 26)
        self.button_type = button_type
        self.is_hover = False

        pm = get_b64_pixmap(b64_icon)
        self.pixmap = pm.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def enterEvent(self, event):
        self.is_hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.button_type == 'red':
            fill_color = QColor(255, 107, 107, 220 if self.is_hover else 90)
        else:
            fill_color = QColor(77, 168, 218, 220 if self.is_hover else 90)

        painter.setBrush(fill_color)
        painter.setPen(QColor(255, 255, 255, 60))
        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 5, 5)

        if not self.pixmap.isNull():
            x = (self.width() - self.pixmap.width()) // 2
            y = (self.height() - self.pixmap.height()) // 2
            painter.drawPixmap(x, y, self.pixmap)

class ApiWorker(threading.Thread):
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.daemon = True

    def run(self):
        try:
            result = self.target(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))

class GoogleTasksWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.services = {}  # Mapping of account_name -> service
        self.all_tasks_data = []
        self.task_containers = []  # [(container_widget, title_text, notes_text, account_name)]
        self.account_lists_map = []  # [(account_name, list_id, list_title)]
        self.show_completed = False
        self.selected_account_filter = "All Accounts"
        self.res_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

        # Edit-mode state — set when the user clicks an Edit button
        self._edit_mode = False
        self._editing_task_id = None
        self._editing_account = None
        self._editing_list_id = None

        self.initUI()

        # Timer to refresh tasks every 60 seconds (was 5 minutes — now 1 min for snappier UX)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_tasks)
        self.timer.start(60000)

        self.fetch_tasks()

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowStaysOnBottomHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, 400, 680)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("BgFrame")
        self.bg_frame.setStyleSheet("""
            #BgFrame {
                background-color: rgba(30, 33, 36, 230);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)

        self.inner_layout = QVBoxLayout(self.bg_frame)
        self.inner_layout.setContentsMargins(15, 15, 15, 15)
        self.inner_layout.setSpacing(8)

        # ── Header ──────────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(0)

        self.title = QLabel("Tasks Widget")
        self.title.setFont(QFont('Segoe UI', 16, QFont.Bold))
        self.title.setStyleSheet("color: white;")
        title_box.addWidget(self.title)

        subtitle = QLabel("Unofficial client for Google Tasks")
        subtitle.setStyleSheet("color: #888888; font-size: 9px; font-style: italic;")
        title_box.addWidget(subtitle)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Fix: Use ONLY icon OR text — not both — to avoid double-icon rendering.
        # We draw the icon manually inside the button via stylesheet background trick,
        # OR simply set the text with unicode and no icon at all.
        # Here we use text-only buttons with a unicode symbol so there's no duplication.
        self.add_btn = QPushButton("＋  Add")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da8da; color: white; font-weight: bold;
                border-radius: 6px; padding: 5px 12px; font-size: 11px;
                border: none;
            }
            QPushButton:hover { background-color: #3b82a6; }
            QPushButton:pressed { background-color: #2d6a8a; }
        """)
        self.add_btn.clicked.connect(self.toggle_add_panel)
        header_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("↻  Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 20); color: white;
                border: 1px solid rgba(255, 255, 255, 30); border-radius: 6px;
                padding: 5px 12px; font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 40); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 60); }
            QPushButton:disabled { color: #555555; }
        """)
        self.refresh_btn.clicked.connect(self.fetch_tasks)
        header_layout.addWidget(self.refresh_btn)

        # 3-Dot Options Menu Button (⋮)
        self.options_btn = QPushButton("⋮")
        self.options_btn.setFixedSize(28, 28)
        self.options_btn.setToolTip("Options & Accounts")
        self.options_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: white; font-size: 16px; font-weight: bold;
                border-radius: 6px; border: 1px solid rgba(255, 255, 255, 30);
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 30); }
        """)
        self.options_btn.clicked.connect(self.show_options_menu)
        header_layout.addWidget(self.options_btn)

        self.inner_layout.addLayout(header_layout)

        # ── Filter Row ───────────────────────────────────────────────────────
        filter_row = QHBoxLayout()

        self.account_switcher = QComboBox()
        self.account_switcher.setView(QListView())
        self.account_switcher.setStyleSheet(COMBO_STYLE)
        self.account_switcher.addItem("All Accounts")
        self.account_switcher.currentTextChanged.connect(self.on_account_filter_changed)
        filter_row.addWidget(self.account_switcher)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(0, 0, 0, 80);
                color: white; border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 6px; padding: 5px 8px; font-size: 11px;
            }
            QLineEdit:focus { border: 1px solid #4da8da; }
        """)
        self.search_input.textChanged.connect(self.filter_tasks)
        filter_row.addWidget(self.search_input)

        self.completed_toggle_btn = QPushButton("Completed")
        self.completed_toggle_btn.setCheckable(True)
        self.completed_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 15); color: #aaaaaa;
                border: 1px solid rgba(255, 255, 255, 20); border-radius: 6px;
                padding: 5px 8px; font-size: 11px; font-weight: bold;
            }
            QPushButton:checked {
                background-color: #4da8da; color: white; border: 1px solid #4da8da;
            }
        """)
        self.completed_toggle_btn.clicked.connect(self.toggle_completed_view)
        filter_row.addWidget(self.completed_toggle_btn)

        self.inner_layout.addLayout(filter_row)

        # ── Collapsible Add Task Panel ────────────────────────────────────────
        self.create_panel = QFrame()
        self.create_panel.setVisible(False)
        self.create_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 100);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 15);
            }
        """)
        panel_layout = QVBoxLayout(self.create_panel)
        panel_layout.setContentsMargins(12, 10, 12, 10)
        panel_layout.setSpacing(6)

        self.panel_title_lbl = QLabel("Create New Task")
        self.panel_title_lbl.setStyleSheet("color: #4da8da; font-weight: bold; font-size: 12px;")
        panel_layout.addWidget(self.panel_title_lbl)

        self.new_task_title = QLineEdit()
        self.new_task_title.setPlaceholderText("Task title...")
        self.new_task_title.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,12); color: white;
                border: 1px solid rgba(255,255,255,20); border-radius: 5px; padding: 5px 8px;
                font-size: 11px;
            }
            QLineEdit:focus { border: 1px solid #4da8da; }
        """)
        panel_layout.addWidget(self.new_task_title)

        self.new_task_notes = QLineEdit()
        self.new_task_notes.setPlaceholderText("Notes / Description (optional)...")
        self.new_task_notes.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,12); color: white;
                border: 1px solid rgba(255,255,255,20); border-radius: 5px; padding: 5px 8px;
                font-size: 11px;
            }
            QLineEdit:focus { border: 1px solid #4da8da; }
        """)
        panel_layout.addWidget(self.new_task_notes)

        # Account / List Dropdown
        self.list_selector = QComboBox()
        self.list_selector.setView(QListView())
        self.list_selector.setStyleSheet(COMBO_STYLE)
        panel_layout.addWidget(self.list_selector)

        # Due Date & Repeat Row
        date_repeat_layout = QHBoxLayout()

        date_lbl = QLabel("Due:")
        date_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        date_repeat_layout.addWidget(date_lbl)

        self.due_date_picker = QDateEdit()
        self.due_date_picker.setDate(QDate.currentDate())
        self.due_date_picker.setCalendarPopup(True)
        self.due_date_picker.setStyleSheet("""
            QDateEdit {
                background: #2a2d32; color: white;
                border: 1px solid rgba(255,255,255,30); border-radius: 6px; padding: 3px 6px;
                font-size: 11px;
            }
            QDateEdit::drop-down {
                border: none; width: 16px; background: transparent;
            }
            QDateEdit::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #4da8da;
            }
        """)
        date_repeat_layout.addWidget(self.due_date_picker)

        repeat_lbl = QLabel("Repeat:")
        repeat_lbl.setStyleSheet("color: #aaa; font-size: 11px; margin-left: 5px;")
        date_repeat_layout.addWidget(repeat_lbl)

        self.repeat_selector = QComboBox()
        self.repeat_selector.setView(QListView())
        self.repeat_selector.addItems(["None", "Daily", "Weekly", "Monthly"])
        self.repeat_selector.setStyleSheet(COMBO_STYLE)
        date_repeat_layout.addWidget(self.repeat_selector)

        panel_layout.addLayout(date_repeat_layout)

        # Cancel + Save buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.cancel_task_btn = QPushButton("Cancel")
        self.cancel_task_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,12); color: #cccccc;
                border: 1px solid rgba(255,255,255,25); border-radius: 6px;
                padding: 7px; font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(255,255,255,25); color: white; }
        """)
        self.cancel_task_btn.clicked.connect(self._close_panel)
        btn_row.addWidget(self.cancel_task_btn)

        self.save_task_btn = QPushButton("Save Task")
        self.save_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da8da; color: white; font-weight: bold;
                border-radius: 6px; padding: 7px; border: none; font-size: 11px;
            }
            QPushButton:hover { background-color: #3b82a6; }
            QPushButton:disabled { background-color: #3a5a70; color: #aaa; }
        """)
        self.save_task_btn.clicked.connect(self.submit_new_task)
        btn_row.addWidget(self.save_task_btn)

        panel_layout.addLayout(btn_row)

        self.inner_layout.addWidget(self.create_panel)

        # ── Scroll Area ───────────────────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 50);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 80);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical { background: none; }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.tasks_layout = QVBoxLayout(self.scroll_content)
        self.tasks_layout.setAlignment(Qt.AlignTop)
        self.tasks_layout.setSpacing(0)

        self.scroll.setWidget(self.scroll_content)
        self.inner_layout.addWidget(self.scroll)

        # Compliance Footer
        disclaimer_lbl = QLabel("Unofficial client • Not affiliated with Google LLC")
        disclaimer_lbl.setAlignment(Qt.AlignCenter)
        disclaimer_lbl.setStyleSheet("color: #555555; font-size: 8px; margin-top: 2px;")
        self.inner_layout.addWidget(disclaimer_lbl)

        self.main_layout.addWidget(self.bg_frame)

    def show_options_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)

        add_acc_act = QAction("➕ Add New Account...", self)
        add_acc_act.triggered.connect(self.on_add_account_clicked)
        menu.addAction(add_acc_act)

        remove_acc_act = QAction("➖ Remove Account...", self)
        remove_acc_act.triggered.connect(self.on_remove_account_clicked)
        menu.addAction(remove_acc_act)

        menu.addSeparator()

        refresh_act = QAction("🔄 Refresh All Tasks", self)
        refresh_act.triggered.connect(self.fetch_tasks)
        menu.addAction(refresh_act)

        about_act = QAction("ℹ️ About & Compliance", self)
        about_act.triggered.connect(self.on_about_clicked)
        menu.addAction(about_act)

        menu.exec_(self.options_btn.mapToGlobal(self.options_btn.rect().bottomLeft()))

    def on_add_account_clicked(self):
        account_name, ok = QInputDialog.getText(self, "Add Account", "Enter account nickname (e.g. work, personal):")
        if ok and account_name.strip():
            account_name = account_name.strip()
            QMessageBox.information(
                self, "Browser Authentication",
                f"Opening browser for Google OAuth login for '{account_name}'..."
            )
            worker = ApiWorker(add_account, account_name)
            worker.signals.finished.connect(lambda res: self.fetch_tasks())
            worker.signals.error.connect(lambda err: QMessageBox.warning(self, "Auth Error", f"Failed to authenticate: {err}"))
            worker.start()

    def on_remove_account_clicked(self):
        accounts = list_accounts()
        if not accounts:
            QMessageBox.information(self, "Remove Account", "No configured accounts to remove.")
            return

        account_name, ok = QInputDialog.getItem(
            self, "Remove Account", "Select account to remove:", accounts, 0, False
        )
        if ok and account_name:
            if remove_account(account_name):
                QMessageBox.information(self, "Account Removed", f"Account '{account_name}' removed.")
                self.fetch_tasks()

    def on_about_clicked(self):
        QMessageBox.about(
            self, "About Tasks Widget",
            "<b>Tasks Widget (Unofficial)</b> v1.0<br>"
            "A lightweight, transparent Linux desktop widget and MCP server for Google Tasks.<br><br>"
            "<i>Legal Disclaimer:</i> This project is an independent, non-official client and is not affiliated, endorsed, or supported by Google LLC."
        )

    def on_account_filter_changed(self, text):
        self.selected_account_filter = text
        self.filter_tasks(self.search_input.text())

    def toggle_completed_view(self, checked):
        self.show_completed = checked
        self.fetch_tasks()

    def toggle_add_panel(self):
        is_vis = self.create_panel.isVisible()
        self.create_panel.setVisible(not is_vis)
        if not is_vis:
            # Panel just became visible — opening fresh (create mode)
            self._enter_create_mode()
        else:
            # Panel just became hidden — reset everything
            self._reset_panel()

    def _enter_create_mode(self):
        """Switch the form panel into 'Create New Task' mode."""
        self._edit_mode = False
        self._editing_task_id = None
        self._editing_account = None
        self._editing_list_id = None
        self.panel_title_lbl.setText("Create New Task")
        self.panel_title_lbl.setStyleSheet("color: #4da8da; font-weight: bold; font-size: 12px;")
        self.save_task_btn.setText("Save Task")
        self.add_btn.setText("✕  Close")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,20); color: white; font-weight: bold;
                border-radius: 6px; padding: 5px 12px; font-size: 11px;
                border: 1px solid rgba(255,255,255,30);
            }
            QPushButton:hover { background-color: rgba(255,255,255,40); }
        """)

    def _enter_edit_mode(self, task_data, account_name, list_id):
        """Switch the form panel into 'Edit Task' mode."""
        self._edit_mode = True
        self._editing_task_id = task_data['id']
        self._editing_account = account_name
        self._editing_list_id = list_id
        self.panel_title_lbl.setText("Edit Task")
        self.panel_title_lbl.setStyleSheet("color: #ffb347; font-weight: bold; font-size: 12px;")
        self.save_task_btn.setText("Update Task")
        self.save_task_btn.setEnabled(True)
        self.add_btn.setText("✕  Close")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,20); color: white; font-weight: bold;
                border-radius: 6px; padding: 5px 12px; font-size: 11px;
                border: 1px solid rgba(255,255,255,30);
            }
            QPushButton:hover { background-color: rgba(255,255,255,40); }
        """)
        self.create_panel.setVisible(True)

        # Populate fields
        self.new_task_title.setText(task_data.get('title', ''))
        self.new_task_notes.setText(task_data.get('notes', ''))
        for idx in range(self.list_selector.count()):
            data = self.list_selector.itemData(idx)
            if data == (account_name, list_id):
                self.list_selector.setCurrentIndex(idx)
                break

    def _reset_panel(self):
        """Reset the form to its default create-mode state and hide it."""
        self._edit_mode = False
        self._editing_task_id = None
        self._editing_account = None
        self._editing_list_id = None
        self.new_task_title.clear()
        self.new_task_notes.clear()
        self.due_date_picker.setDate(QDate.currentDate())
        self.repeat_selector.setCurrentIndex(0)
        self.panel_title_lbl.setText("Create New Task")
        self.panel_title_lbl.setStyleSheet("color: #4da8da; font-weight: bold; font-size: 12px;")
        self.save_task_btn.setText("Save Task")
        self.save_task_btn.setEnabled(True)
        self.add_btn.setText("＋  Add")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da8da; color: white; font-weight: bold;
                border-radius: 6px; padding: 5px 12px; font-size: 11px;
                border: none;
            }
            QPushButton:hover { background-color: #3b82a6; }
            QPushButton:pressed { background-color: #2d6a8a; }
        """)

    def _close_panel(self):
        """Close and reset the panel without taking any action — used by Cancel button."""
        self.create_panel.setVisible(False)
        self._reset_panel()


    def clear_tasks_layout(self):
        self.task_containers = []
        while self.tasks_layout.count():
            child = self.tasks_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def fetch_tasks(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("↻  Syncing...")
        self.clear_tasks_layout()

        # Load all services dynamically
        accounts = list_accounts()

        # Populate Account Switcher Dropdown
        current_acc_selection = self.account_switcher.currentText()
        self.account_switcher.blockSignals(True)
        self.account_switcher.clear()
        self.account_switcher.addItem("All Accounts")
        for acc in accounts:
            self.account_switcher.addItem(f"👤 {acc}")
        idx = self.account_switcher.findText(current_acc_selection)
        if idx >= 0:
            self.account_switcher.setCurrentIndex(idx)
        self.account_switcher.blockSignals(False)

        if not accounts:
            lbl = QLabel("No accounts configured.\nUse 3-dot (⋮) menu → Add New Account.")
            lbl.setStyleSheet("color: #ff9999;")
            lbl.setWordWrap(True)
            self.tasks_layout.addWidget(lbl)
            self._restore_refresh_btn()
            return

        self.services = {}
        for acc in accounts:
            service = get_service(acc)
            if service:
                self.services[acc] = service

        if not self.services:
            lbl = QLabel("Authentication error for all accounts.\nPlease re-authenticate using 3-dot (⋮) menu.")
            lbl.setStyleSheet("color: #ff9999;")
            lbl.setWordWrap(True)
            self.tasks_layout.addWidget(lbl)
            self._restore_refresh_btn()
            return

        lbl = QLabel(f"Syncing {len(self.services)} account(s)...")
        lbl.setStyleSheet("color: #aaaaaa; font-style: italic;")
        self.tasks_layout.addWidget(lbl)

        worker = ApiWorker(self._api_fetch_all)
        worker.signals.finished.connect(self._on_fetch_success)
        worker.signals.error.connect(self._on_fetch_error)
        worker.start()

    def _restore_refresh_btn(self):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("↻  Refresh")

    def _api_fetch_all(self):
        all_accounts_data = []
        self.account_lists_map = []

        for account_name, service in self.services.items():
            account_data = {'account': account_name, 'lists': []}
            results = service.tasklists().list(maxResults=10).execute()
            lists = results.get('items', [])

            for tasklist in lists:
                self.account_lists_map.append((account_name, tasklist['id'], f"{account_name} - {tasklist['title']}"))
                tasks_res = service.tasks().list(
                    tasklist=tasklist['id'],
                    showHidden=self.show_completed,
                    showCompleted=self.show_completed,
                    maxResults=100
                ).execute()
                tasks = tasks_res.get('items', [])

                # Filter tasks based on toggle
                if not self.show_completed:
                    filtered_tasks = [t for t in tasks if t.get('status') != 'completed']
                else:
                    filtered_tasks = tasks

                if filtered_tasks:
                    ordered_tasks = self._organize_subtask_hierarchy(filtered_tasks)
                    account_data['lists'].append({
                        'list_id': tasklist['id'],
                        'title': tasklist['title'],
                        'tasks': ordered_tasks
                    })
            if account_data['lists']:
                all_accounts_data.append(account_data)

        return all_accounts_data

    def _organize_subtask_hierarchy(self, tasks):
        parents = [t for t in tasks if not t.get('parent')]
        children = [t for t in tasks if t.get('parent')]

        ordered = []
        for p in parents:
            ordered.append(p)
            subtasks = [c for c in children if c.get('parent') == p['id']]
            ordered.extend(subtasks)

        remaining = [c for c in children if c not in ordered]
        ordered.extend(remaining)
        return ordered

    def _on_fetch_error(self, error_str):
        self.clear_tasks_layout()
        lbl = QLabel(f"Error: {error_str}")
        lbl.setStyleSheet("color: #ff6b6b;")
        lbl.setWordWrap(True)
        self.tasks_layout.addWidget(lbl)
        self._restore_refresh_btn()

    def _on_fetch_success(self, all_accounts_data):
        self.clear_tasks_layout()
        self.all_tasks_data = all_accounts_data

        # Populate List Selector
        self.list_selector.clear()
        for acc_name, list_id, label in self.account_lists_map:
            self.list_selector.addItem(label, userData=(acc_name, list_id))

        if not all_accounts_data:
            lbl = QLabel("All caught up! 🎉")
            lbl.setStyleSheet("color: #a8e6cf; font-size: 16px; margin-top: 20px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.tasks_layout.addWidget(lbl)
            self._restore_refresh_btn()
            return

        for acc_data in all_accounts_data:
            account_name = acc_data['account']

            # Top level Account Header
            acc_lbl = QLabel(f"👤 {account_name}")
            acc_lbl.setFont(QFont('Segoe UI', 12, QFont.Bold))
            acc_lbl.setStyleSheet("color: #ffb347; margin-top: 12px; padding-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,25);")
            acc_lbl.setProperty('account', account_name)
            self.tasks_layout.addWidget(acc_lbl)

            for group in acc_data['lists']:
                # Group Header
                group_lbl = QLabel(group['title'])
                group_lbl.setFont(QFont('Segoe UI', 11, QFont.Bold))
                group_lbl.setStyleSheet("color: #4da8da; margin-top: 8px; margin-bottom: 4px;")
                group_lbl.setProperty('account', account_name)
                self.tasks_layout.addWidget(group_lbl)

                # Tasks
                for task in group['tasks']:
                    task_container = self._build_task_widget(task, acc_data, group)
                    self.tasks_layout.addWidget(task_container)
                    notes_text = task.get('notes', '')
                    self.task_containers.append((
                        task_container,
                        task['title'].lower(),
                        notes_text.lower(),
                        account_name
                    ))

        self.tasks_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self._restore_refresh_btn()
        self.filter_tasks(self.search_input.text())

    def _build_task_widget(self, task, acc_data, group):
        """Build and return a complete task container widget."""
        task_container = QWidget()
        task_container.setStyleSheet("background: transparent;")
        task_layout = QVBoxLayout(task_container)

        is_subtask = bool(task.get('parent'))
        left_margin = 20 if is_subtask else 0
        task_layout.setContentsMargins(left_margin, 0, 0, 8)
        task_layout.setSpacing(2)

        # ── Top row ─────────────────────────────────────────────────────────
        top_row = QWidget()
        top_row.setStyleSheet("background: transparent;")
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        title_prefix = "↳ " if is_subtask else ""
        is_completed = (task.get('status') == 'completed')

        cb = QCheckBox(f"{title_prefix}{task['title']}")
        cb.setFont(QFont('Segoe UI', 11))
        cb.setChecked(is_completed)
        cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        cb_style = """
            QCheckBox { color: white; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 2px solid #555; background: transparent; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #888; }
            QCheckBox::indicator:checked { background-color: #4da8da; border: 2px solid #4da8da; }
            QCheckBox::indicator:checked:after { color: white; }
        """
        if is_completed:
            cb_style += " QCheckBox { color: #666666; text-decoration: line-through; }"
        elif is_subtask:
            cb_style += " QCheckBox { color: #dddddd; }"

        cb.setStyleSheet(cb_style)
        cb.setProperty('account', acc_data['account'])
        cb.setProperty('task_id', task['id'])
        cb.setProperty('list_id', group['list_id'])
        cb.setProperty('container', task_container)
        cb.clicked.connect(self.on_task_checked)
        top_layout.addWidget(cb)

        due_raw = task.get('due')
        recurrence = task.get('recurrence')
        date_text, date_color = format_due_date(due_raw, recurrence)

        if date_text:
            date_lbl = QLabel(date_text)
            date_lbl.setStyleSheet(f"color: {date_color}; font-size: 10px; font-weight: bold; background: transparent;")
            date_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
            top_layout.addWidget(date_lbl, alignment=Qt.AlignVCenter | Qt.AlignRight)

        # Edit Task Button — use button_type='blue' (no string hacking)
        edit_btn = ImageButton(
            EDIT_ICON_B64,
            button_type='blue',
            tooltip="Edit task details"
        )
        edit_btn.setProperty('task_data', task)
        edit_btn.setProperty('account', acc_data['account'])
        edit_btn.setProperty('list_id', group['list_id'])
        edit_btn.clicked.connect(self.on_edit_task)
        top_layout.addWidget(edit_btn)

        # Delete Task Button
        del_btn = ImageButton(
            DELETE_ICON_B64,
            button_type='red',
            tooltip="Delete task"
        )
        del_btn.setProperty('account', acc_data['account'])
        del_btn.setProperty('task_id', task['id'])
        del_btn.setProperty('list_id', group['list_id'])
        del_btn.setProperty('container', task_container)
        del_btn.clicked.connect(self.on_delete_task)
        top_layout.addWidget(del_btn)

        task_layout.addWidget(top_row)

        # Description row
        notes_text = task.get('notes', '')
        if notes_text:
            notes_lbl = QLabel(notes_text)
            notes_lbl.setWordWrap(True)
            notes_lbl.setStyleSheet("color: #aaaaaa; font-size: 10px; margin-left: 24px; background: transparent;")
            task_layout.addWidget(notes_lbl)

        # Links row
        if task.get('links'):
            for link in task['links']:
                link_url = link.get('link')
                link_desc = link.get('description', 'Attachment')
                link_lbl = QLabel(f'<a href="{link_url}" style="color: #4da8da; text-decoration: none;">🔗 {link_desc}</a>')
                link_lbl.setOpenExternalLinks(True)
                link_lbl.setStyleSheet("margin-left: 24px; font-size: 10px; background: transparent;")
                task_layout.addWidget(link_lbl)

        return task_container

    def filter_tasks(self, query):
        query = query.lower().strip()
        selected_acc = self.selected_account_filter.replace("👤 ", "").strip()

        for container, title, notes, account in list(self.task_containers):
            try:
                matches_search = (not query or query in title or query in notes)
                matches_account = (selected_acc == "All Accounts" or account == selected_acc)
                container.setVisible(matches_search and matches_account)
            except RuntimeError:
                pass

    def submit_new_task(self):
        title = self.new_task_title.text().strip()
        if not title:
            return

        notes = self.new_task_notes.text().strip()
        due_date_str = self.due_date_picker.date().toString("yyyy-MM-dd") + "T00:00:00.000Z"

        repeat_option = self.repeat_selector.currentText()
        recurrence = None
        if repeat_option == "Daily":
            recurrence = ["RRULE:FREQ=DAILY"]
        elif repeat_option == "Weekly":
            recurrence = ["RRULE:FREQ=WEEKLY"]
        elif repeat_option == "Monthly":
            recurrence = ["RRULE:FREQ=MONTHLY"]

        self.save_task_btn.setEnabled(False)

        if self._edit_mode:
            # ── UPDATE existing task ─────────────────────────────────────────
            self.save_task_btn.setText("Updating...")
            task_body = {'title': title, 'due': due_date_str}
            if notes:
                task_body['notes'] = notes
            else:
                task_body['notes'] = ''  # Clear notes if field is empty
            if recurrence:
                task_body['recurrence'] = recurrence

            worker = ApiWorker(
                self._api_update_task,
                self._editing_account,
                self._editing_list_id,
                self._editing_task_id,
                task_body
            )
            worker.signals.finished.connect(self._on_update_success)
            worker.signals.error.connect(self._on_fetch_error)
            worker.start()
        else:
            # ── CREATE new task ──────────────────────────────────────────────
            selected_data = self.list_selector.currentData()
            if not selected_data:
                self.save_task_btn.setEnabled(True)
                return

            acc_name, list_id = selected_data
            self.save_task_btn.setText("Saving...")

            task_body = {'title': title, 'due': due_date_str}
            if notes:
                task_body['notes'] = notes
            if recurrence:
                task_body['recurrence'] = recurrence

            worker = ApiWorker(self._api_create_task, acc_name, list_id, task_body)
            worker.signals.finished.connect(self._on_create_success)
            worker.signals.error.connect(self._on_fetch_error)
            worker.start()

    def _api_create_task(self, account_name, list_id, task_body):
        try:
            service = self.services.get(account_name)
            if service:
                return service.tasks().insert(tasklist=list_id, body=task_body).execute()
        except Exception:
            pass
        return None

    def _api_update_task(self, account_name, list_id, task_id, patch_body):
        try:
            service = self.services.get(account_name)
            if service:
                # Fetch the current task first to preserve fields we're not editing
                existing = service.tasks().get(tasklist=list_id, task=task_id).execute()
                existing.update(patch_body)
                return service.tasks().update(
                    tasklist=list_id, task=task_id, body=existing
                ).execute()
        except Exception:
            pass
        return None

    def _on_update_success(self, result):
        self.create_panel.setVisible(False)
        self._reset_panel()
        self.fetch_tasks()

    def _on_create_success(self, result):
        self.create_panel.setVisible(False)
        self._reset_panel()
        self.fetch_tasks()

    def on_task_checked(self, checked):
        cb = self.sender()
        account_name = cb.property('account')
        task_id = cb.property('task_id')
        list_id = cb.property('list_id')
        container = cb.property('container')

        if checked:
            # Visually mark as done immediately
            cb.setStyleSheet(cb.styleSheet() + " QCheckBox { color: #555555; text-decoration: line-through; }")

            # When not showing completed tasks, auto-hide the container after a short delay
            if not self.show_completed and container:
                hide_timer = QTimer(self)
                hide_timer.setSingleShot(True)
                hide_timer.timeout.connect(lambda: self._hide_completed_task(container))
                hide_timer.start(800)  # 0.8 second delay so user sees the check animate

        else:
            cb.setStyleSheet(cb.styleSheet().replace("color: #555555; text-decoration: line-through;", ""))

        status = 'completed' if checked else 'needsAction'
        worker = ApiWorker(self._api_toggle_task_status, account_name, list_id, task_id, status)
        worker.start()

    def _hide_completed_task(self, container):
        """Smoothly hide (and remove) a completed task row without a full refresh."""
        try:
            container.setVisible(False)
            self.task_containers = [item for item in self.task_containers if item[0] != container]
            container.deleteLater()
        except RuntimeError:
            pass  # Widget already deleted

    def _api_toggle_task_status(self, account_name, list_id, task_id, status):
        try:
            service = self.services.get(account_name)
            if service:
                task = service.tasks().get(tasklist=list_id, task=task_id).execute()
                task['status'] = status
                service.tasks().update(tasklist=list_id, task=task_id, body=task).execute()
        except Exception:
            pass

    def on_edit_task(self):
        btn = self.sender()
        task_data = btn.property('task_data')
        account_name = btn.property('account')
        list_id = btn.property('list_id')
        self._enter_edit_mode(task_data, account_name, list_id)

    def on_delete_task(self):
        btn = self.sender()
        if not btn or not btn.isEnabled():
            return

        btn.setEnabled(False)
        account_name = btn.property('account')
        task_id = btn.property('task_id')
        list_id = btn.property('list_id')
        container = btn.property('container')

        if container:
            container.setVisible(False)
            self.task_containers = [item for item in self.task_containers if item[0] != container]
            container.deleteLater()

        worker = ApiWorker(self._api_delete_task, account_name, list_id, task_id)
        worker.start()

    def _api_delete_task(self, account_name, list_id, task_id):
        try:
            service = self.services.get(account_name)
            if service:
                service.tasks().delete(tasklist=list_id, task=task_id).execute()
        except Exception:
            pass

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ex = GoogleTasksWidget()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
