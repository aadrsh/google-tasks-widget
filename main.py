import os
import sys
import threading
from datetime import datetime, date
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QCheckBox, QScrollArea, QFrame, QHBoxLayout, 
                             QSpacerItem, QSizePolicy, QPushButton, QLineEdit, 
                             QComboBox, QDateEdit, QListView)

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
        border: 1px solid rgba(255, 255, 255, 30);
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }
"""
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QDate
from PyQt5.QtGui import QFont, QIcon

# Import our auth module
from auth import list_accounts, get_service

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
        
        if diff < 0:
            if diff == -1:
                return f"Yesterday{repeat_suffix}", "#ff6b6b"
            else:
                return f"Overdue ({due_date.strftime('%b %d')}){repeat_suffix}", "#ff6b6b"
        elif diff == 0:
            return f"Today{repeat_suffix}", "#4da8da"
        elif diff == 1:
            return f"Tomorrow{repeat_suffix}", "#a8e6cf"
        elif diff < 7:
            return f"{due_date.strftime('%A')}{repeat_suffix}", "#dddddd"
        else:
            return f"{due_date.strftime('%b %d')}{repeat_suffix}", "#888888"
    except Exception:
        return f"{due_raw[:10]}{repeat_suffix}", "#888888"

class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

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
        self.services = {} # Mapping of account_name -> service
        self.all_tasks_data = []
        self.task_containers = [] # [(container_widget, title_text, notes_text)]
        self.account_lists_map = [] # [(account_name, list_id, list_title)]
        
        self.initUI()
        
        # Timer to refresh tasks every 5 minutes
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_tasks)
        self.timer.start(300000) 
        
        self.fetch_tasks()

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowStaysOnBottomHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, 380, 650)
        
        # Set Custom Icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        
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
        
        # Header
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
        
        res_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
        
        # Add Task toggle button
        self.add_btn = QPushButton()
        self.add_btn.setIcon(QIcon(os.path.join(res_dir, 'plus.svg')))
        self.add_btn.setFixedSize(30, 30)
        self.add_btn.setToolTip("Create New Task")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da8da; border-radius: 15px;
            }
            QPushButton:hover { background-color: #3b82a6; }
        """)
        self.add_btn.clicked.connect(self.toggle_add_panel)
        header_layout.addWidget(self.add_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(QIcon(os.path.join(res_dir, 'refresh.svg')))
        self.refresh_btn.setFixedSize(30, 30)
        self.refresh_btn.setToolTip("Refresh Tasks")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; border-radius: 15px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 30); }
        """)
        self.refresh_btn.clicked.connect(self.fetch_tasks)
        header_layout.addWidget(self.refresh_btn)
        
        self.inner_layout.addLayout(header_layout)
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search tasks...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(0, 0, 0, 80);
                color: white; border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 8px; padding: 5px 10px; font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #4da8da; }
        """)
        self.search_input.textChanged.connect(self.filter_tasks)
        self.inner_layout.addWidget(self.search_input)
        
        # Collapsible Add Task Form Panel
        self.create_panel = QFrame()
        self.create_panel.setVisible(False)
        self.create_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 100);
                border-radius: 10px; padding: 10px; margin-top: 5px; margin-bottom: 5px;
            }
        """)
        panel_layout = QVBoxLayout(self.create_panel)
        panel_layout.setSpacing(6)
        
        panel_title = QLabel("Create New Task")
        panel_title.setStyleSheet("color: #4da8da; font-weight: bold; font-size: 12px;")
        panel_layout.addWidget(panel_title)
        
        self.new_task_title = QLineEdit()
        self.new_task_title.setPlaceholderText("Task title...")
        self.new_task_title.setStyleSheet("background: rgba(255,255,255,15); color: white; border-radius: 5px; padding: 4px;")
        panel_layout.addWidget(self.new_task_title)
        
        self.new_task_notes = QLineEdit()
        self.new_task_notes.setPlaceholderText("Notes / Description (optional)...")
        self.new_task_notes.setStyleSheet("background: rgba(255,255,255,15); color: white; border-radius: 5px; padding: 4px;")
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
        self.due_date_picker.setStyleSheet("background: #2a2d32; color: white; border: 1px solid rgba(255,255,255,30); border-radius: 6px; padding: 3px;")
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
        
        # Submit Button
        self.save_task_btn = QPushButton("Save Task")
        self.save_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da8da; color: white; font-weight: bold;
                border-radius: 6px; padding: 6px; margin-top: 4px;
            }
            QPushButton:hover { background-color: #3b82a6; }
        """)
        self.save_task_btn.clicked.connect(self.submit_new_task)
        panel_layout.addWidget(self.save_task_btn)
        
        self.inner_layout.addWidget(self.create_panel)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 50);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 100);
                border-radius: 4px;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.tasks_layout = QVBoxLayout(self.scroll_content)
        self.tasks_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.scroll_content)
        self.inner_layout.addWidget(self.scroll)
        
        # Compliance Footer
        disclaimer_lbl = QLabel("Unofficial client • Not affiliated with Google LLC")
        disclaimer_lbl.setAlignment(Qt.AlignCenter)
        disclaimer_lbl.setStyleSheet("color: #666666; font-size: 8px; margin-top: 4px;")
        self.inner_layout.addWidget(disclaimer_lbl)
        
        self.main_layout.addWidget(self.bg_frame)
        self.setLayout(self.main_layout)

    def toggle_add_panel(self):
        is_vis = self.create_panel.isVisible()
        self.create_panel.setVisible(not is_vis)
        self.add_btn.setText("-" if not is_vis else "+")

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
        self.clear_tasks_layout()
        
        # Load all services dynamically
        accounts = list_accounts()
        if not accounts:
            lbl = QLabel("No accounts configured.\\nUse `google-tasks-cli add-account <name>` to add one.")
            lbl.setStyleSheet("color: #ff9999;")
            lbl.setWordWrap(True)
            self.tasks_layout.addWidget(lbl)
            self.refresh_btn.setEnabled(True)
            return

        self.services = {}
        for acc in accounts:
            service = get_service(acc)
            if service:
                self.services[acc] = service
        
        if not self.services:
            lbl = QLabel("Authentication error for all accounts.\\nPlease re-authenticate using the CLI.")
            lbl.setStyleSheet("color: #ff9999;")
            lbl.setWordWrap(True)
            self.tasks_layout.addWidget(lbl)
            self.refresh_btn.setEnabled(True)
            return

        lbl = QLabel(f"Syncing {len(self.services)} account(s)...")
        lbl.setStyleSheet("color: #aaaaaa; font-style: italic;")
        self.tasks_layout.addWidget(lbl)
        
        worker = ApiWorker(self._api_fetch_all)
        worker.signals.finished.connect(self._on_fetch_success)
        worker.signals.error.connect(self._on_fetch_error)
        worker.start()

    def _api_fetch_all(self):
        all_accounts_data = []
        self.account_lists_map = []
        
        for account_name, service in self.services.items():
            account_data = {'account': account_name, 'lists': []}
            results = service.tasklists().list(maxResults=10).execute()
            lists = results.get('items', [])
            
            for tasklist in lists:
                self.account_lists_map.append((account_name, tasklist['id'], f"{account_name} - {tasklist['title']}"))
                tasks_res = service.tasks().list(tasklist=tasklist['id'], showHidden=False, maxResults=50).execute()
                tasks = tasks_res.get('items', [])
                
                # Filter pending tasks
                pending = [t for t in tasks if t.get('status') != 'completed']
                if pending:
                    account_data['lists'].append({
                        'list_id': tasklist['id'],
                        'title': tasklist['title'],
                        'tasks': pending
                    })
            if account_data['lists']:
                all_accounts_data.append(account_data)
                
        return all_accounts_data

    def _on_fetch_error(self, error_str):
        self.clear_tasks_layout()
        lbl = QLabel(f"Error: {error_str}")
        lbl.setStyleSheet("color: #ff6b6b;")
        lbl.setWordWrap(True)
        self.tasks_layout.addWidget(lbl)
        self.refresh_btn.setEnabled(True)

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
            self.refresh_btn.setEnabled(True)
            return

        for acc_data in all_accounts_data:
            # Top level Account Header
            acc_lbl = QLabel(f"👤 {acc_data['account']}")
            acc_lbl.setFont(QFont('Segoe UI', 13, QFont.Bold))
            acc_lbl.setStyleSheet("color: #ffb347; margin-top: 15px; border-bottom: 1px solid rgba(255,255,255,30);")
            self.tasks_layout.addWidget(acc_lbl)
            
            for group in acc_data['lists']:
                # Group Header
                lbl = QLabel(group['title'])
                lbl.setFont(QFont('Segoe UI', 11, QFont.Bold))
                lbl.setStyleSheet("color: #4da8da; margin-top: 8px; margin-bottom: 2px;")
                self.tasks_layout.addWidget(lbl)
                
                # Tasks
                for task in group['tasks']:
                    task_container = QWidget()
                    task_layout = QVBoxLayout(task_container)
                    task_layout.setContentsMargins(0, 0, 0, 8)
                    task_layout.setSpacing(2)
                    
                    if task.get('parent'):
                        task_layout.setContentsMargins(20, 0, 0, 8)

                    # Top row: Checkbox, Due Date, and Delete Button
                    top_row = QWidget()
                    top_layout = QHBoxLayout(top_row)
                    top_layout.setContentsMargins(0,0,0,0)

                    cb = QCheckBox(task['title'])
                    cb.setFont(QFont('Segoe UI', 11))
                    cb.setStyleSheet("""
                        QCheckBox { color: white; spacing: 10px; }
                        QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 2px solid #555; }
                        QCheckBox::indicator:unchecked:hover { border: 2px solid #888; }
                        QCheckBox::indicator:checked { background-color: #4da8da; border: 2px solid #4da8da; }
                    """)
                    if task.get('parent'):
                        cb.setStyleSheet(cb.styleSheet() + "QCheckBox { color: #dddddd; }")
                        
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
                        date_lbl.setStyleSheet(f"color: {date_color}; font-size: 10px; font-weight: bold;")
                        top_layout.addWidget(date_lbl, alignment=Qt.AlignRight)
                        
                    # Delete Task Button
                    del_btn = QPushButton()
                    del_btn.setIcon(QIcon(os.path.join(res_dir, 'delete.svg')))
                    del_btn.setFixedSize(22, 22)
                    del_btn.setToolTip("Delete task")
                    del_btn.setStyleSheet("""
                        QPushButton { background: transparent; border: none; padding: 2px; }
                        QPushButton:hover { background: rgba(255, 107, 107, 40); border-radius: 4px; }
                    """)
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
                        notes_lbl.setStyleSheet("color: #aaaaaa; font-size: 10px; margin-left: 26px;")
                        task_layout.addWidget(notes_lbl)

                    # Links row
                    if task.get('links'):
                        for link in task['links']:
                            link_url = link.get('link')
                            link_desc = link.get('description', 'Attachment')
                            link_lbl = QLabel(f'<a href="{link_url}" style="color: #4da8da; text-decoration: none;">🔗 {link_desc}</a>')
                            link_lbl.setOpenExternalLinks(True)
                            link_lbl.setStyleSheet("margin-left: 26px; font-size: 10px;")
                            task_layout.addWidget(link_lbl)

                    self.tasks_layout.addWidget(task_container)
                    self.task_containers.append((task_container, task['title'].lower(), notes_text.lower()))
        
        self.tasks_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.refresh_btn.setEnabled(True)

    def filter_tasks(self, query):
        query = query.lower().strip()
        for container, title, notes in list(self.task_containers):
            try:
                if not query or query in title or query in notes:
                    container.setVisible(True)
                else:
                    container.setVisible(False)
            except RuntimeError:
                pass

    def submit_new_task(self):
        title = self.new_task_title.text().strip()
        if not title:
            return
            
        selected_data = self.list_selector.currentData()
        if not selected_data:
            return
            
        acc_name, list_id = selected_data
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
        self.save_task_btn.setText("Saving...")
        
        task_body = {
            'title': title,
            'due': due_date_str
        }
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

    def _on_create_success(self, result):
        self.new_task_title.clear()
        self.new_task_notes.clear()
        self.save_task_btn.setEnabled(True)
        self.save_task_btn.setText("Save Task")
        self.toggle_add_panel()
        self.fetch_tasks()

    def on_task_checked(self, checked):
        cb = self.sender()
        if checked:
            cb.setStyleSheet(cb.styleSheet() + "QCheckBox { color: #555555; text-decoration: line-through; }")
            cb.setEnabled(False)
            
            container = cb.property('container')
            if container:
                container.setEnabled(False)
                        
            account_name = cb.property('account')
            task_id = cb.property('task_id')
            list_id = cb.property('list_id')
            
            worker = ApiWorker(self._api_complete_task, account_name, list_id, task_id)
            worker.start()
            
    def _api_complete_task(self, account_name, list_id, task_id):
        try:
            service = self.services.get(account_name)
            if service:
                task = service.tasks().get(tasklist=list_id, task=task_id).execute()
                task['status'] = 'completed'
                service.tasks().update(tasklist=list_id, task=task_id, body=task).execute()
        except Exception:
            pass

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
