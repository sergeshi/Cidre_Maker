from __future__ import annotations
import json
import sys
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QPlainTextEdit, QSplitter, QTabWidget, QVBoxLayout,
    QWidget, QScrollArea, QGridLayout, QDoubleSpinBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from model import APP_VERSION, TYPES, STATUSES, batch_search_text, load_data, new_batch, save_data, stats, predicted_abv, classic_tirage, duplicate_json
from advanced import AdvancedPanel

APP_DIR = Path.home() / ".cidremaker"
DEFAULT_DATA = APP_DIR / "cider_data.json"

STYLES = """
QMainWindow, QWidget { background:#101419; color:#edf1f5; font-family:'Segoe UI Variable','Segoe UI',sans-serif; font-size:13px; }
QFrame#sidebar, QFrame#hero, QFrame#metric { background:#171e25; border:1px solid #2a3540; border-radius:16px; }
QFrame#metric { background:#182129; border:1px solid #2a3942; }
QFrame#metric:hover { border-color:#54766f; }
QLabel#brand { color:#e7c078; font-size:21px; font-weight:850; letter-spacing:2px; }
QLabel#sectionTitle { color:#f2f4f7; font-size:15px; font-weight:750; }
QLabel#eyebrow { color:#86b9aa; font-size:10px; font-weight:800; letter-spacing:1.5px; }
QLabel#muted { color:#9299a8; }
QLabel#metricValue { font-size:27px; font-weight:800; color:#e7c078; }
QLineEdit, QComboBox, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTableWidget {
 background:#131a20; color:#edf1f5; border:1px solid #303d47; border-radius:10px; padding:8px; selection-background-color:#42675f;
}
QComboBox QAbstractItemView { background:#182129; color:#edf1f5; selection-background-color:#31534c; border:1px solid #35464e; }
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border:1px solid #82b6a7; }
QPushButton { background:#1b252d; border:1px solid #35434c; border-radius:10px; padding:10px 14px; font-weight:650; }
QPushButton:hover { border-color:#82b6a7; background:#23343a; }
QPushButton:pressed { background:#101a20; }
QPushButton:disabled { color:#68737c; background:#151b20; border-color:#242e35; }
QPushButton#primary { background:#a9d2c2; color:#10221f; border-color:#a9d2c2; font-weight:850; }
QPushButton#primary:hover { background:#c0e1d4; border-color:#c0e1d4; }
QPushButton#complete { background:#24483f; color:#bde6d7; border-color:#3e7162; font-weight:800; }
QPushButton#danger { color:#f18c8c; border-color:#643a40; }
QListWidget { background:transparent; border:0; outline:0; }
QListWidget::item { padding:12px 10px; margin:3px 0; border:1px solid transparent; border-radius:9px; }
QListWidget::item:selected { background:#21352f; border:1px solid #527b6d; color:#d9f0e6; }
QListWidget::item:hover:!selected { background:#1b252c; border:1px solid #2e3d45; }
QTabWidget::pane { border:1px solid #2c3b43; border-radius:14px; top:-1px; background:#141b21; }
QTabBar::tab { background:#1b252c; color:#aebbc2; padding:11px 17px; margin-right:5px; border-top-left-radius:9px; border-top-right-radius:9px; }
QTabBar::tab:selected { background:#a9d2c2; color:#10221f; font-weight:800; }
QTabBar::tab:hover:!selected { background:#26353b; }
QHeaderView::section { background:#1c282f; color:#c4d0d5; padding:9px; border:0; border-bottom:1px solid #34434a; }
QTableWidget { gridline-color:#29363e; alternate-background-color:#172128; }
QScrollArea { border:0; }
QStatusBar { color:#9da4b2; }
"""

def field(label: str, value, parent=None):
    if isinstance(value, bool):
        w = QComboBox()
        w.addItem("Нет", False); w.addItem("Да", True)
        w.setCurrentIndex(1 if value else 0)
        w.value = lambda: w.currentData()
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        w = QDoubleSpinBox()
        w.setRange(-1000000, 1000000); w.setDecimals(4); w.setSingleStep(0.1)
        w.setValue(float(value))
        w.value = w.value
    else:
        w = QLineEdit(str(value if value is not None else ""))
        w.value = w.text
    w.setObjectName("field_" + label.replace(" ", "_"))
    return w

class BatchEditor(QWidget):
    def __init__(self, batch, on_changed):
        super().__init__()
        self.batch = batch
        self.on_changed = on_changed
        root = QVBoxLayout(self); root.setContentsMargins(16, 16, 16, 16)
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)
        self.controls = {}
        self._build_fields()
        self.raw = QPlainTextEdit()
        self.raw.setPlaceholderText("Полный JSON объекта партии — для редактирования дополнительных полей и структур.")
        self.tabs.addTab(self.raw, "JSON / расширенно")
        self.refresh()

    def _build_fields(self):
        definitions = [
            ("Партия", [("name","Название"),("code","Код"),("type","Тип"),("status","Статус"),("createdDate","Дата создания")]),
            ("1 · Сырьё", [("stage1.date","Дата отжима"),("stage1.region","Регион"),("stage1.varieties","Сорта / купаж"),("stage1.volume","Объём, л"),("stage1.brix","Начальный Brix"),("stage1.actualAbv","Факт. ABV, %"),("stage1.ph","pH"),("stage1.ta","TA, г/л")]),
            ("2 · Брожение", [("stage2.tempStart","Температура старта, °C"),("stage2.yeast","Штамм дрожжей"),("stage2.yeastDate","Дата внесения дрожжей"),("stage2.startDate","Начало брожения"),("stage2.rackingDate","Снятие с осадка")]),
            ("3 · Розлив", [("stage3.volume","Объём для розлива, л"),("stage3.desiredPressure","Целевое давление, bar"),("stage3.bottleSize","Объём бутылки, л"),("stage3.liqueurPerBottle","Ликёра на бутылку, мл"),("stage3.liqueurSugarConcentration","Сахар в ликёре, г/л"),("stage3.date","Дата розлива"),("stage3.autolysis","Начало автолиза"),("stage3.cap","Укупорка")]),
            ("4 · Выдержка", [("stage4.disgorging","Дегоржаж / финиш"),("stage4.agingMonths","Выдержка, мес"),("stage4.leesAging","Выдержка на толстом осадке"),("stage4.leesMonths","Месяцев на толстом осадке"),("stage4.batonnage","Батонаж"),("stage4.finalCap","Финальная укупорка"),("stage4.finalCode","Финальный код")]),
            ("5 · Контроль", [("stage5.tastingDate","Дата дегустации"),("stage5.sparkling","Игристость 1–5"),("stage5.tasteNotes","Дегустационные заметки"),("stage5.packDate","Дата упаковки"),("generalNotes","Общие заметки")]),
        ]
        for title, items in definitions:
            page = QWidget(); outer = QVBoxLayout(page); outer.setContentsMargins(14,14,14,14)
            form = QFormLayout(); form.setHorizontalSpacing(16); form.setVerticalSpacing(12)
            for key, label in items:
                initial = self._get_path(self.batch, key)
                if key == "type":
                    w = QComboBox()
                    for k, v in TYPES.items(): w.addItem(v, k)
                    w.currentIndexChanged.connect(lambda _=0, k=key: self._form_changed())
                elif key == "status":
                    w = QComboBox()
                    for k, v in STATUSES.items(): w.addItem(v, k)
                    w.currentIndexChanged.connect(lambda _=0, k=key: self._form_changed())
                else:
                    w = field(label, initial)
                    if isinstance(w, QLineEdit): w.textChanged.connect(self._form_changed)
                    elif isinstance(w, QComboBox): w.currentIndexChanged.connect(self._form_changed)
                    else: w.valueChanged.connect(self._form_changed)
                self.controls[key] = w
                form.addRow(label, w)
            outer.addLayout(form); outer.addStretch(1)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page)
            self.tabs.addTab(scroll, title)

    @staticmethod
    def _get_path(obj, path):
        cur = obj
        for part in path.split("."):
            if not isinstance(cur, dict): return ""
            cur = cur.get(part, "")
        return cur

    @staticmethod
    def _set_path(obj, path, value):
        parts = path.split("."); cur = obj
        for part in parts[:-1]:
            if not isinstance(cur.get(part), dict): cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value

    def refresh(self):
        for key, w in self.controls.items():
            value = self._get_path(self.batch, key)
            w.blockSignals(True)
            if key in ("type", "status"):
                idx = w.findData(value)
                w.setCurrentIndex(idx if idx >= 0 else 0)
            elif isinstance(w, QLineEdit): w.setText(str(value if value is not None else ""))
            elif isinstance(w, QComboBox): w.setCurrentIndex(1 if bool(value) else 0)
            else:
                try: w.setValue(float(value or 0))
                except (ValueError, TypeError): w.setValue(0)
            w.blockSignals(False)
        self.raw.blockSignals(True); self.raw.setPlainText(duplicate_json(self.batch)); self.raw.blockSignals(False)

    def _form_changed(self, *_):
        for key, w in self.controls.items():
            if key in ("type", "status"): value = w.currentData()
            elif isinstance(w, QLineEdit): value = w.text()
            elif isinstance(w, QComboBox): value = w.currentData()
            else: value = w.value()
            old = self._get_path(self.batch, key)
            if isinstance(old, (int, float)) and not isinstance(old, bool):
                try: value = int(value) if isinstance(old, int) else float(value)
                except (ValueError, TypeError): value = 0
            self._set_path(self.batch, key, value)
        self.batch["stage1"]["predictedAbv"] = f'{predicted_abv(self.batch["stage1"].get("brix", 0)):.2f}'
        self.raw.blockSignals(True); self.raw.setPlainText(duplicate_json(self.batch)); self.raw.blockSignals(False)
        self.on_changed()

    def apply_raw(self):
        try:
            value = json.loads(self.raw.toPlainText())
            if not isinstance(value, dict): raise ValueError("Корень должен быть JSON-объектом партии.")
            for key in ("id", "stage1", "stage2", "stage3", "stage4", "stage5"):
                if key not in value: raise ValueError(f"Не найдено обязательное поле: {key}")
            self.batch.clear(); self.batch.update(value)
            self.refresh(); self.on_changed()
            return True
        except Exception as exc:
            QMessageBox.warning(self, "Некорректный JSON", str(exc))
            return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CIDREMAKER · Desktop")
        self.resize(1440, 900); self.setMinimumSize(1100, 720)
        self.data = {"appVersion": APP_VERSION, "dataSchemaVersion": "2.3", "batches": []}
        self.path = DEFAULT_DATA; self.current_id = None; self.dirty = False
        self._autosave = QTimer(self); self._autosave.setSingleShot(True); self._autosave.setInterval(850); self._autosave.timeout.connect(self.save)
        self._ensure_database()
        self._build_ui(); self._build_menu()
        self.open_path(DEFAULT_DATA, quiet=True)
        self.statusBar().showMessage("Готово · локальные данные остаются на вашем компьютере")

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        outer = QVBoxLayout(central); outer.setContentsMargins(18,16,18,12); outer.setSpacing(14)
        top = QHBoxLayout()
        brand = QLabel("◉  CIDREMAKER"); brand.setObjectName("brand"); top.addWidget(brand)
        subtitle = QLabel("Журнал производства сидра"); subtitle.setObjectName("muted"); top.addWidget(subtitle)
        top.addStretch()
        year_label = QLabel("ГОД"); year_label.setObjectName("eyebrow"); top.addWidget(year_label)
        self.year_filter = QComboBox(); self.year_filter.setMinimumWidth(105); self.year_filter.currentIndexChanged.connect(self.update_metrics); top.addWidget(self.year_filter)
        self.file_label = QLabel("Локальная база · автосохранение"); self.file_label.setObjectName("muted"); top.addWidget(self.file_label)
        outer.addLayout(top)
        split = QSplitter(Qt.Horizontal); outer.addWidget(split, 1)
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); side = QVBoxLayout(sidebar); side.setContentsMargins(12,14,12,12)
        side_head = QHBoxLayout(); title = QLabel("ПАРТИИ"); title.setStyleSheet("font-weight:800; letter-spacing:1px; color:#aeb4c1")
        side_head.addWidget(title); side_head.addStretch()
        add = QPushButton("+ Новая"); add.setObjectName("primary"); add.clicked.connect(self.add_batch); side_head.addWidget(add)
        side.addLayout(side_head)
        self.search = QLineEdit(); self.search.setPlaceholderText("Поиск по названию, коду, сортам…"); self.search.textChanged.connect(self.render_list); side.addWidget(self.search)
        filters = QHBoxLayout()
        self.type_filter = QComboBox(); self.type_filter.addItem("Все типы", "")
        for k,v in TYPES.items(): self.type_filter.addItem(v,k)
        self.type_filter.currentIndexChanged.connect(self.render_list); filters.addWidget(self.type_filter)
        self.status_filter = QComboBox(); self.status_filter.addItem("Все статусы", "")
        for k,v in STATUSES.items(): self.status_filter.addItem(v,k)
        self.status_filter.currentIndexChanged.connect(self.render_list); filters.addWidget(self.status_filter)
        side.addLayout(filters)
        self.list = QListWidget(); self.list.currentItemChanged.connect(self.select_item); side.addWidget(self.list,1)
        actions = QHBoxLayout()
        dup = QPushButton("Дублировать"); dup.clicked.connect(self.duplicate_batch); actions.addWidget(dup)
        delete = QPushButton("Удалить"); delete.setObjectName("danger"); delete.clicked.connect(self.delete_batch); actions.addWidget(delete)
        side.addLayout(actions)
        split.addWidget(sidebar)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(12)
        self.metrics = QHBoxLayout(); rv.addLayout(self.metrics)
        self.editor = BatchEditor({}, self.mark_dirty)
        self.work_tabs = QTabWidget()
        self.work_tabs.addTab(self.editor, "Карточка партии")
        self.advanced = AdvancedPanel(lambda: self.data.get("batches", []), self._current, lambda: self.path, self.mark_dirty, self.select_batch_id)
        self.work_tabs.addTab(self.advanced, "Календарь · графики · инструменты")
        rv.addWidget(self.work_tabs,1)
        bottom = QHBoxLayout()
        self.dirty_label = QLabel("●  Все изменения сохранены"); self.dirty_label.setObjectName("muted"); bottom.addWidget(self.dirty_label)
        bottom.addStretch()
        self.complete_btn = QPushButton("✓  Завершить партию"); self.complete_btn.setObjectName("complete"); self.complete_btn.clicked.connect(self.complete_batch); bottom.addWidget(self.complete_btn)
        export = QPushButton("Экспорт / бэкап"); export.clicked.connect(self.export_dialog); bottom.addWidget(export)
        self.apply_json = QPushButton("Применить JSON"); self.apply_json.clicked.connect(self.apply_raw); bottom.addWidget(self.apply_json)
        split.addWidget(right); split.setSizes([320, 1060])

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("Файл")
        for title, callback in [("Импортировать партии…", self.import_dialog), ("Экспортировать бэкап…", self.export_dialog), ("Сохранить сейчас", self.save)]:
            action = QAction(title, self); action.triggered.connect(callback); file_menu.addAction(action)
        file_menu.addSeparator()
        exit_action = QAction("Выход", self); exit_action.triggered.connect(self.close); file_menu.addAction(exit_action)

    def _metric(self, value, label):
        frame = QFrame(); frame.setObjectName("metric"); layout = QVBoxLayout(frame); layout.setContentsMargins(14,12,14,12)
        v = QLabel(str(value)); v.setObjectName("metricValue"); l = QLabel(label.upper()); l.setObjectName("muted")
        layout.addWidget(v); layout.addWidget(l); return frame

    def update_metrics(self):
        while self.metrics.count():
            item = self.metrics.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        s = stats(self.data)
        batches = self.data.get("batches", [])
        def volume(batch):
            raw = (batch.get("stage1") or {}).get("volume")
            if raw in (None, ""): raw = batch.get("volumeInitial") or batch.get("volumeCurrent") or 0
            try: return max(0.0, float(raw or 0))
            except (TypeError, ValueError): return 0.0
        total_l = sum(volume(b) for b in batches)
        open_l = sum(volume(b) for b in batches if b.get("status") != "done" and not b.get("completedAt"))
        year = self.year_filter.currentData() if hasattr(self, "year_filter") else str(datetime.now().year)
        year_l = sum(volume(b) for b in batches if self._batch_year(b) == str(year))
        cards = [(f"{open_l:.1f} л", "в работе"), (f"{total_l:.1f} л", "всего объёма"), (f"{year_l:.1f} л", f"за {year} год"), (s["total"],"партий"), (s["active"]+s["aging"]+s["planned"],"не завершено"), (s["done"],"завершено")]
        for val, label in cards: self.metrics.addWidget(self._metric(val,label))

    def render_list(self, *_):
        current = self.current_id
        self.list.blockSignals(True); self.list.clear()
        query = self.search.text().casefold().strip()
        typ = self.type_filter.currentData(); status = self.status_filter.currentData()
        batches = self.data.get("batches", [])
        batches = [b for b in batches if (not query or query in batch_search_text(b)) and (not typ or b.get("type")==typ) and (not status or b.get("status")==status)]
        batches.sort(key=lambda b: (str(b.get("createdAt","")), str(b.get("name","")).casefold()), reverse=True)
        for b in batches:
            name = b.get("name") or "(без названия)"
            subtitle = f'{TYPES.get(b.get("type"), b.get("type","—"))}  ·  {STATUSES.get(b.get("status"), b.get("status","—"))}  ·  {((b.get("stage1") or {}).get("volume") or 0)} л'
            item = QListWidgetItem(f"{name}\\n{subtitle}")
            item.setData(Qt.UserRole, b.get("id")); item.setToolTip(str(b.get("code","")))
            self.list.addItem(item)
            if b.get("id") == current: self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if self.list.count() and self.list.currentItem() is None: self.list.setCurrentRow(0)
        self._refresh_year_options()
        self.update_metrics()

    def select_item(self, item, _previous=None):
        if item is None: return
        batch = next((b for b in self.data["batches"] if b.get("id")==item.data(Qt.UserRole)), None)
        if batch:
            self.current_id = batch.get("id"); self.editor.batch = batch; self.editor.refresh()
            if hasattr(self, "advanced"):
                self.advanced.refresh()
            if hasattr(self, "complete_btn"):
                completed = batch.get("status") == "done" or bool(batch.get("completedAt"))
                self.complete_btn.setEnabled(not completed)
                self.complete_btn.setText("✓  Партия завершена" if completed else "✓  Завершить партию")

    def _current(self):
        return next((b for b in self.data["batches"] if b.get("id")==self.current_id), None)

    def mark_dirty(self):
        self.dirty = True; self.dirty_label.setText("●  Сохранение…")
        self.dirty_label.setStyleSheet("color:#e4b45c")
        self.update_metrics()
        if hasattr(self, "advanced"):
            self.advanced.refresh_data()
        if hasattr(self, "_autosave"): self._autosave.start()

    def select_batch_id(self, batch_id):
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == batch_id:
                self.list.setCurrentRow(i)
                return
        batch = next((b for b in self.data.get("batches", []) if b.get("id") == batch_id), None)
        if batch:
            self.current_id = batch_id; self.editor.batch = batch; self.editor.refresh()
            if hasattr(self, "advanced"): self.advanced.refresh()

    def add_batch(self):
        b = new_batch(); self.data["batches"].insert(0,b); self.current_id = b["id"]
        self.render_list()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole)==self.current_id: self.list.setCurrentRow(i); break
        self.editor.batch = b; self.editor.refresh(); self.mark_dirty()
        if hasattr(self, "advanced"): self.advanced.refresh()

    def duplicate_batch(self):
        b = self._current()
        if not b: return
        clone = deepcopy(b); clone["id"] = new_batch()["id"]; clone["name"] = (b.get("name") or "Партия") + " · копия"
        clone["code"] = ""; clone["createdAt"] = datetime.now(timezone.utc).isoformat(); clone["createdDate"] = datetime.now().date().isoformat()
        self.data["batches"].insert(0,clone); self.current_id=clone["id"]; self.render_list(); self.editor.batch=clone; self.editor.refresh(); self.mark_dirty()
        if hasattr(self, "advanced"): self.advanced.refresh()

    def delete_batch(self):
        b = self._current()
        if not b: return
        if QMessageBox.question(self,"Удалить партию",f'Удалить «{b.get("name","(без названия)")}»?') != QMessageBox.Yes: return
        self.data["batches"] = [x for x in self.data["batches"] if x.get("id") != self.current_id]
        self.current_id = self.data["batches"][0].get("id") if self.data["batches"] else None
        self.render_list()
        if self._current(): self.editor.batch=self._current(); self.editor.refresh()
        else: self.editor.batch={}; self.editor.refresh()
        self.mark_dirty()

    def save(self):
        if not self.path: self.path = DEFAULT_DATA
        try:
            if self._current():
                self._current()["updatedAt"] = datetime.now(timezone.utc).isoformat()
            self.data["appVersion"] = APP_VERSION
            save_data(self.path,self.data); self.dirty=False
            self.dirty_label.setText("✓  Сохранено"); self.dirty_label.setStyleSheet("color:#8fbe80")
            self.statusBar().showMessage("База данных автоматически сохранена",3500)
            self.render_list()
        except Exception as exc:
            QMessageBox.critical(self,"Ошибка сохранения",str(exc))

    def open_path(self,path,quiet=False):
        try:
            data=load_data(path)
            self.data=data; self.path=Path(path); self.file_label.setText("Автобаза · " + self.path.name)
            self.current_id=(data["batches"][0].get("id") if data["batches"] else None)
            self.editor.batch=self._current() or {}; self.editor.refresh()
            self.dirty=False; self.render_list()
            if hasattr(self, "advanced"):
                self.advanced.refresh()
            if not quiet: self.statusBar().showMessage(f'Открыт журнал: {self.path}',5000)
        except Exception as exc:
            if not quiet: QMessageBox.critical(self,"Не удалось открыть JSON",str(exc))

    def _ensure_database(self):
        """Seed the private user database and merge bundled batches without overwriting edits."""
        seed = Path(__file__).with_name("cider_data.json")
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if DEFAULT_DATA.exists():
            data = load_data(DEFAULT_DATA)
        elif seed.exists():
            data = {"appVersion": APP_VERSION, "dataSchemaVersion": "2.3", "batches": []}
        else:
            data = {"appVersion": APP_VERSION, "dataSchemaVersion": "2.3", "batches": []}
        if seed.exists():
            bundled = load_data(seed).get("batches", [])
            seen = set()
            unique = []
            for batch in data.get("batches", []):
                key = batch.get("id") or f'{batch.get("code", "")}|{batch.get("name", "")}'
                if key not in seen:
                    seen.add(key); unique.append(batch)
            for batch in bundled:
                key = batch.get("id") or f'{batch.get("code", "")}|{batch.get("name", "")}'
                if key not in seen:
                    seen.add(key); unique.append(batch)
            data["batches"] = unique
        data["appVersion"] = APP_VERSION
        save_data(DEFAULT_DATA, data)

    @staticmethod
    def _batch_year(batch):
        for value in ((batch.get("stage1") or {}).get("date"), batch.get("createdDate"), batch.get("createdAt"), batch.get("completedAt")):
            if value:
                return str(value)[:4]
        return ""

    def _refresh_year_options(self):
        if not hasattr(self, "year_filter"): return
        selected = str(self.year_filter.currentData() or datetime.now().year)
        years = {self._batch_year(b) for b in self.data.get("batches", [])}
        years.discard("")
        years.add(str(datetime.now().year))
        self.year_filter.blockSignals(True); self.year_filter.clear()
        for year in sorted(years, reverse=True): self.year_filter.addItem(year, year)
        index = self.year_filter.findData(selected)
        self.year_filter.setCurrentIndex(index if index >= 0 else self.year_filter.findData(str(datetime.now().year)))
        self.year_filter.blockSignals(False)

    def complete_batch(self):
        batch = self._current()
        if not batch or batch.get("status") == "done" or batch.get("completedAt"): return
        answer = QMessageBox.question(self, "Завершить партию", f'Отметить «{batch.get("name", "Без названия")}» как завершённую?\n\nОна останется в журнале и календаре.', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if answer != QMessageBox.Yes: return
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()
        batch["status"] = "done"; batch["completedAt"] = today; batch["completionDate"] = today
        batch["statusReason"] = "Завершена вручную"; batch["statusUpdatedAt"] = now.isoformat(); batch["updatedAt"] = now.isoformat()
        history = batch.setdefault("stageHistory", [])
        if not any(isinstance(x, dict) and x.get("stage") == "done" and x.get("date") == today for x in history):
            history.append({"stage":"done","date":today})
        self.editor.refresh(); self.render_list(); self.mark_dirty()
        if hasattr(self, "advanced"): self.advanced.refresh()
        self.complete_btn.setEnabled(False); self.complete_btn.setText("✓  Партия завершена")

    def import_dialog(self):
        path,_=QFileDialog.getOpenFileName(self,"Импортировать партии","", "JSON (*.json)")
        if not path: return
        try:
            imported=load_data(path); existing={b.get("id") for b in self.data["batches"]}
            count=0
            for b in imported["batches"]:
                clone=deepcopy(b)
                if not clone.get("id") or clone["id"] in existing:
                    clone["id"]=new_batch()["id"]
                existing.add(clone["id"]); self.data["batches"].append(clone); count+=1
            self.render_list(); self.mark_dirty()
            QMessageBox.information(self,"Импорт завершён",f"Добавлено партий: {count}")
        except Exception as exc: QMessageBox.critical(self,"Ошибка импорта",str(exc))

    def export_dialog(self):
        path,_=QFileDialog.getSaveFileName(self,"Экспортировать журнал","cider_data_backup.json","JSON (*.json)")
        if not path: return
        try:
            save_data(path,self.data); self.statusBar().showMessage(f"Экспортировано: {path}",5000)
        except Exception as exc: QMessageBox.critical(self,"Ошибка экспорта",str(exc))

    def apply_raw(self):
        if self.editor.apply_raw():
            self.current_id=self.editor.batch.get("id")
            self.render_list(); self.dirty=True
            if hasattr(self, "advanced"):
                self.advanced.refresh()
            self.dirty_label.setText("●  Есть несохранённые изменения")

    def closeEvent(self,event):
        if self.dirty:
            self.save()
            if self.dirty: event.ignore(); return
        event.accept()

def main():
    app=QApplication(sys.argv); app.setStyle("Fusion"); app.setFont(QFont("Segoe UI",10)); app.setStyleSheet(STYLES)
    window=MainWindow(); window.show(); sys.exit(app.exec())

if __name__ == "__main__": main()
