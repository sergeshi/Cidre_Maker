from __future__ import annotations
import math
import shutil
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPointF, QDate
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPixmap, QTextCharFormat
from calculations import _num, calculate_petnat, solera_recalculate

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton,
    QCalendarWidget, QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout,
    QDoubleSpinBox, QComboBox, QLineEdit, QTextEdit, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QGridLayout, QSpinBox, QInputDialog
)

BG = QColor("#171a20")
PANEL = QColor("#20242d")
GOLD = QColor("#d9a54e")
TEXT = QColor("#e9eaf0")
MUTED = QColor("#9299a8")
GREEN = QColor("#8fbe80")
RED = QColor("#e77d7d")
BLUE = QColor("#78a9d6")
TYPE_LABELS = {"classic":"Классик", "petnat":"Петнат", "still":"Тихий", "solera":"Коль Фандо"}
STATUS_LABELS = {"planned":"План", "active":"Брожение", "aging":"Выдержка", "done":"Готово", "attention":"Внимание"}

def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None

class FermentationChart(QWidget):
    def __init__(self, get_batch, parent=None):
        super().__init__(parent); self.get_batch = get_batch; self.setMinimumHeight(280)
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), BG)
        b=self.get_batch() or {}; ms=(b.get("stage2") or {}).get("measurements",[]) or []
        pts=[]
        for m in ms:
            d=_date(m.get("date")); val=m.get("refractometerBrix")
            if val in (None,""): val=m.get("brix")
            if val in (None,""): val=m.get("density")
            try: v=float(val)
            except (TypeError,ValueError): continue
            if d: pts.append((d,v,m))
        pts.sort(key=lambda x:x[0])
        area=self.rect().adjusted(58,28,-24,-48)
        p.setPen(QColor("#303642"))
        for i in range(5):
            y=area.top()+area.height()*i/4
            p.drawLine(int(area.left()),int(y),int(area.right()),int(y))
        p.setPen(QColor("#aab0bd")); p.setFont(QFont("Segoe UI",9))
        if len(pts)<2:
            p.drawText(area, Qt.AlignCenter, "Добавьте минимум два замера с датой и Brix / плотностью")
            return
        vals=[x[1] for x in pts]; lo=min(vals); hi=max(vals)
        if hi==lo: hi+=1; lo-=1
        lo-=.08*(hi-lo); hi+=.08*(hi-lo)
        p.setPen(QColor("#9299a8"))
        for i in range(5):
            val=hi-(hi-lo)*i/4; y=area.top()+area.height()*i/4
            p.drawText(4,int(y-6),48,14,f"{val:.1f}")
        def pos(i,v):
            return QPointF(area.left()+area.width()*i/(len(pts)-1),area.bottom()-area.height()*(v-lo)/(hi-lo))
        p.setPen(QPen(GOLD,3))
        for i in range(len(pts)-1): p.drawLine(pos(i,pts[i][1]),pos(i+1,pts[i+1][1]))
        for i,(d,v,m) in enumerate(pts):
            q=pos(i,v); p.setBrush(GOLD); p.setPen(QPen(BG,1)); p.drawEllipse(q,4,4)
        p.setPen(QColor("#aab0bd"))
        p.drawText(int(area.left()),self.height()-14,pts[0][0].isoformat())
        p.drawText(int(area.right()-100),self.height()-14,100,18,Qt.AlignRight,pts[-1][0].isoformat())

class TimelineWidget(QWidget):
    def __init__(self, get_batches, on_select, parent=None):
        super().__init__(parent); self.get_batches=get_batches; self.on_select=on_select; self.rows=[]; self.setMinimumHeight(220)
    def refresh(self):
        self.rows=[]
        for b in self.get_batches() or []:
            s1=b.get("stage1") or {}; s2=b.get("stage2") or {}; s3=b.get("stage3") or {}; s4=b.get("stage4") or {}; s5=b.get("stage5") or {}
            spans=[]
            def add(label,a,z,color):
                da=_date(a); dz=_date(z) or date.today()
                if da: spans.append((label,da,max(da,dz),QColor(color)))
            add("Отжим",s1.get("date"),s2.get("startDate") or s1.get("date"),"#8b9ab0")
            add("Брожение",s2.get("startDate"),s2.get("rackingDate") or s3.get("date"),"#6fae91")
            add("Розлив / ферментация",s3.get("date"),s4.get("disgorging") or s4.get("rackingDatePet") or s4.get("rackingDate") or s5.get("packDate"),"#d9a54e")
            add("Готово",s5.get("packDate"),s5.get("packDate"),"#78a9d6")
            if spans: self.rows.append((b,spans))
        self.setMinimumHeight(max(220, 44 + len(self.rows)*48)); self.updateGeometry(); self.update()
    def mousePressEvent(self,event):
        row=max(0,int((event.position().y()-40)//48))
        if row<len(self.rows): self.on_select(self.rows[row][0].get("id"))
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.fillRect(self.rect(),BG)
        all_dates=[d for _,spans in self.rows for _,a,z,_ in spans for d in (a,z)]
        today=date.today(); all_dates.extend([today])
        if not all_dates:
            p.setPen(TEXT);p.drawText(self.rect(),Qt.AlignCenter,"Нет дат для построения timeline");return
        lo=min(all_dates);hi=max(all_dates)
        if lo==hi: hi=lo.fromordinal(lo.toordinal()+1)
        days=max(1,(hi-lo).days); left=230; right=self.width()-18; width=max(20,right-left)
        p.setPen(QColor("#4a505d"));p.setFont(QFont("Segoe UI",9))
        for i in range(7):
            x=left+width*i/6;p.drawLine(int(x),24,int(x),self.height())
            d=lo.fromordinal(lo.toordinal()+round(days*i/6));p.drawText(int(x-34),18,d.strftime("%d.%m.%y"))
        todayx=left+width*(today-lo).days/days
        p.setPen(QPen(RED,1,Qt.DashLine));p.drawLine(int(todayx),22,int(todayx),self.height())
        for ri,(b,spans) in enumerate(self.rows):
            y=34+ri*48
            p.setPen(TEXT);p.setFont(QFont("Segoe UI",9,QFont.Bold));p.drawText(8,y+15,(b.get("name") or "Без названия")[:27])
            p.setPen(MUTED);p.setFont(QFont("Segoe UI",8));p.drawText(8,y+30,STATUS_LABELS.get(b.get("status"),b.get("status","—")))
            for label,a,z,c in spans:
                x1=left+width*(a-lo).days/days;x2=left+width*(z-lo).days/days
                p.setPen(Qt.NoPen);p.setBrush(c);p.drawRoundedRect(QRectF(x1,y,x2-x1+max(4,3),20),5,5)
                if x2-x1>65:
                    p.setPen(QColor("#111318"));p.drawText(QRectF(x1+4,y,x2-x1-4,20),Qt.AlignVCenter|Qt.AlignLeft,label)

class AdvancedPanel(QWidget):
    def __init__(self, get_data, get_batch, get_path, on_changed, on_select, parent=None):
        super().__init__(parent)
        self.get_data=get_data;self.get_batch=get_batch;self.get_path=get_path;self.on_changed=on_changed;self.on_select=on_select
        root=QVBoxLayout(self);root.setContentsMargins(8,8,8,8)
        self.tabs=QTabWidget();root.addWidget(self.tabs)
        self.calendar=QCalendarWidget();self.calendar.setGridVisible(True);self.calendar.selectionChanged.connect(self._show_day)
        calpage=QWidget();cl=QVBoxLayout(calpage);cl.addWidget(QLabel("События производства: отжим, брожение, снятие с осадка, розлив, дегоржаж и упаковка"));cl.addWidget(self.calendar)
        self.day_table=QTableWidget(0,4);self.day_table.setHorizontalHeaderLabels(["Событие","Партия","Тип","Статус"]);self.day_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.day_table.cellDoubleClicked.connect(self._open_day_row);cl.addWidget(self.day_table)
        self.tabs.addTab(calpage,"Календарь")
        tlpage=QWidget();tl=QVBoxLayout(tlpage);tl.addWidget(QLabel("Производственные этапы по датам. Нажмите на строку, чтобы открыть партию."));self.timeline=TimelineWidget(self.get_data,self.on_select);tl.addWidget(self.timeline)
        self.tabs.addTab(tlpage,"Timeline")
        chartpage=QWidget();ch=QVBoxLayout(chartpage);self.chart_title=QLabel("График брожения");ch.addWidget(self.chart_title);self.chart=FermentationChart(self.get_batch);ch.addWidget(self.chart,1)
        self.measure_table=QTableWidget(0,4);self.measure_table.setHorizontalHeaderLabels(["Дата","Brix / плотность","Температура","Заметка"]);self.measure_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);ch.addWidget(self.measure_table)
        self.tabs.addTab(chartpage,"График")
        petpage=QWidget();pv=QVBoxLayout(petpage);pv.addWidget(QLabel("Pet-Nat · расчёт остаточного сахара и ориентировочного давления"))
        self.pet_fields={};form=QFormLayout()
        specs=[("originalBrix","Начальный Brix",12),("refractometerBrix","Текущий Brix рефрактометра",0),("hydrometerSG","Текущий SG ареометра",1.01),("measurementAlcohol","Измеренный ABV, %",0),("estimatedResidualSugar","Остаточный сахар, г/л (-1 = автооценка)",-1),("desiredPressure","Целевое давление",5),("maxBottlePressure","Допустимое давление бутылки, bar",4.5),("safetyMargin","Запас безопасности, %",15)]
        for key,label,default in specs:
            w=QDoubleSpinBox();w.setRange(-1 if key=="estimatedResidualSugar" else 0,1000);w.setDecimals(4);w.setValue(default);w.valueChanged.connect(self._pet_calc);self.pet_fields[key]=w;form.addRow(label,w)
        self.pressure_unit=QComboBox();self.pressure_unit.addItems(["bar","atm"]);self.pressure_unit.currentTextChanged.connect(self._pet_calc);form.addRow("Единица целевого давления",self.pressure_unit)
        pv.addLayout(form);self.pet_result=QLabel();self.pet_result.setWordWrap(True);self.pet_result.setTextInteractionFlags(Qt.TextSelectableByMouse);pv.addWidget(self.pet_result)
        savepet=QPushButton("Сохранить расчёт в партию");savepet.clicked.connect(self._save_petnat);pv.addWidget(savepet);pv.addStretch(1);self.tabs.addTab(petpage,"Pet-Nat")
        solpage=QWidget();sv=QVBoxLayout(solpage);sv.addWidget(QLabel("Solera · журнал отбора и пополнения. Операции хранятся в stage3.operations."))
        self.sol_summary=QLabel();sv.addWidget(self.sol_summary)
        self.sol_table=QTableWidget(0,7);self.sol_table.setHorizontalHeaderLabels(["Дата","Тип","Отобрано, л","Добавлено, л","Источник","Возраст источника","Заметка"]);self.sol_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);sv.addWidget(self.sol_table,1)
        sb=QHBoxLayout();addop=QPushButton("+ Операция");addop.clicked.connect(self._add_solera);delop=QPushButton("Удалить выбранную");delop.clicked.connect(self._delete_solera);saveop=QPushButton("Сохранить правки");saveop.clicked.connect(self.commit_solera_edits);sb.addWidget(addop);sb.addWidget(delop);sb.addWidget(saveop);sv.addLayout(sb);self.tabs.addTab(solpage,"Solera")
        labelpage=QWidget();lv=QVBoxLayout(labelpage);lv.addWidget(QLabel("Фото этикетки хранится в папке pix рядом с выбранным JSON-журналом."))
        self.image_preview=QLabel("Фото не выбрано");self.image_preview.setAlignment(Qt.AlignCenter);self.image_preview.setMinimumHeight(220);self.image_preview.setStyleSheet("background:#20242d;border:1px solid #343a47;border-radius:10px;");lv.addWidget(self.image_preview,1)
        self.image_name=QLabel("—");self.image_name.setWordWrap(True);lv.addWidget(self.image_name)
        buttons=QHBoxLayout();up=QPushButton("Загрузить фото");up.clicked.connect(self._upload_label);rm=QPushButton("Удалить фото");rm.clicked.connect(self._delete_label);buttons.addWidget(up);buttons.addWidget(rm);lv.addLayout(buttons);self.tabs.addTab(labelpage,"Этикетка")
        self.refresh()
    def refresh(self):
        self.refresh_data(); self._pet_load()
    def refresh_data(self):
        self._refresh_calendar();self.timeline.refresh();self._refresh_chart();self._refresh_solera();self._refresh_label()
    def _events(self):
        events=[]
        for b in self.get_data() or []:
            st1=b.get("stage1") or {};st2=b.get("stage2") or {};st3=b.get("stage3") or {};st4=b.get("stage4") or {};st5=b.get("stage5") or {}
            for d,label in [(st1.get("date"),"Отжим"),(st2.get("startDate"),"Начало брожения"),(st2.get("rackingDate"),"Снятие с осадка"),(st3.get("date"),"Розлив"),(st4.get("disgorging") or st4.get("rackingDatePet") or st4.get("rackingDate"),"Финиш / дегоржаж"),(st5.get("tastingDate"),"Дегустация"),(st5.get("packDate"),"Упаковка")]:
                d=_date(d)
                if d: events.append((d,label,b))
            completed = b.get("completionDate") or b.get("completedAt")
            if not completed:
                completed = next((item.get("date") for item in reversed(b.get("stageHistory",[]) or []) if isinstance(item,dict) and item.get("stage") == "done"), None)
            completed = _date(completed)
            if completed: events.append((completed,"Завершение партии",b))
            for m in st2.get("measurements",[]) or []:
                d=_date(m.get("date"))
                if d: events.append((d,"Замер",b))
            for n in st2.get("nutrients",[]) or []:
                d=_date(n.get("date"))
                if d: events.append((d,"Подкормка",b))
            for op in st3.get("operations",[]) or []:
                d=_date(op.get("date"))
                if d: events.append((d,"Операция Solera",b))
            for op in st4.get("batonnageSchedule",[]) or []:
                d=_date(op.get("date") if isinstance(op,dict) else op)
                if d: events.append((d,"Батонаж",b))
        return events
    def _refresh_calendar(self):
        events=self._events(); bydate={}
        for d,label,b in events: bydate.setdefault(d,[]).append((label,b))
        self._calendar_events=bydate
        for d,items in bydate.items():
            fmt=QTextCharFormat();fmt.setBackground(QColor("#5a4727"));fmt.setForeground(QColor("#f4d38c"));self.calendar.setDateTextFormat(QDate(d.year,d.month,d.day),fmt)
        self._show_day()
    def _show_day(self):
        d=self.calendar.selectedDate().toPython();items=self._calendar_events.get(d,[])
        self.day_table.setRowCount(len(items))
        for i,(label,b) in enumerate(items):
            vals=[label,b.get("name","Без названия"),TYPE_LABELS.get(b.get("type"),b.get("type","")),STATUS_LABELS.get(b.get("status"),b.get("status",""))]
            for j,v in enumerate(vals):
                cell=QTableWidgetItem(str(v));cell.setData(Qt.UserRole,b.get("id"));self.day_table.setItem(i,j,cell)
    def _open_day_row(self,row,col):
        item=self.day_table.item(row,1)
        if item and item.data(Qt.UserRole):self.on_select(item.data(Qt.UserRole))
    def _refresh_chart(self):
        b=self.get_batch() or {};self.chart_title.setText(f"График брожения · {b.get('name','Без названия')}")
        ms=(b.get("stage2") or {}).get("measurements",[]) or [];self.measure_table.setRowCount(len(ms))
        for i,m in enumerate(ms):
            density=m.get("refractometerBrix") or m.get("brix") or m.get("density","")
            for j,v in enumerate([m.get("date",""),density,m.get("temp",""),m.get("note","")]):self.measure_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.chart.update()
    def _pet_load(self):
        b=self.get_batch() or {};s=(b.get("stage3") or {})
        mapping={"originalBrix":(b.get("stage1") or {}).get("brix",12),"refractometerBrix":s.get("refractometerBrix",0),"hydrometerSG":s.get("hydrometerSG",1.01),"measurementAlcohol":s.get("measurementAlcohol",0),"estimatedResidualSugar":(-1 if s.get("estimatedResidualSugar") in (None, "") else s.get("estimatedResidualSugar",-1)),"desiredPressure":s.get("desiredPressure",5),"maxBottlePressure":s.get("maxBottlePressure",4.5),"safetyMargin":s.get("safetyMargin",15)}
        for k,v in mapping.items():
            self.pet_fields[k].blockSignals(True);self.pet_fields[k].setValue(_num(v));self.pet_fields[k].blockSignals(False)
        self.pressure_unit.setCurrentText(s.get("pressureUnit","bar") or "bar");self._pet_calc()
    def _pet_calc(self):
        s={k:w.value() for k,w in self.pet_fields.items()};s["pressureUnit"]=self.pressure_unit.currentText()
        r=calculate_petnat(s)
        fmt=lambda x: f"{x:.2f}" if isinstance(x,(float,int)) and math.isfinite(x) else "—"
        self.pet_result.setText(f"Оценочный ABV: {fmt(r['estimatedABV'])}%\nКорректированный Brix-equivalent: {fmt(r['correctedBrix'])}\nОстаточный сахар: {fmt(r['residualSugar'])} г/л\nОценочное давление: {fmt(r['pressureBar'])} bar\nСахар для целевого давления: {fmt(r['targetSugar'])} г/л\n\n" + "\n".join("⚠ "+x for x in r["warnings"]))
    def _save_petnat(self):
        b=self.get_batch()
        if not b:return
        s=b.setdefault("stage3",{})
        for k,w in self.pet_fields.items():s[k]=w.value()
        s["pressureUnit"]=self.pressure_unit.currentText()
        r=calculate_petnat(s)
        for k in ("correctedSG","correctedBrix","estimatedABV","targetSugar"):s[k]=r.get(k)
        s["petnatWarnings"]=r["warnings"];b["updatedAt"]=datetime.now().astimezone().isoformat();self.on_changed();QMessageBox.information(self,"Pet-Nat","Параметры расчёта сохранены. Проверьте предупреждения и характеристики бутылок.")
    def _refresh_solera(self):
        b=self.get_batch() or {};s=b.get("stage3") or {};ops=s.get("operations",[]) or []
        volume,age=solera_recalculate(s);self.sol_summary.setText(f"Текущий расчётный объём: {volume:.2f} л · средний возраст: {age:.2f} лет")
        self.sol_table.setRowCount(len(ops))
        for i,op in enumerate(ops):
            vals=[op.get("date",""),op.get("type","withdraw-fill"),op.get("removed",0),op.get("added",0),op.get("source",""),op.get("sourceAgeYears",0),op.get("note","")]
            for j,v in enumerate(vals):
                cell=QTableWidgetItem(str(v));cell.setData(Qt.UserRole,i);self.sol_table.setItem(i,j,cell)
            if op.get("warning"):
                for j in range(7):self.sol_table.item(i,j).setBackground(QColor("#5b292d"))
    def _add_solera(self):
        b=self.get_batch()
        if not b:return
        s=b.setdefault("stage3",{});s.setdefault("operations",[]).append({"date":date.today().isoformat(),"type":"withdraw-fill","removed":0,"added":0,"source":"","sourceAgeYears":0,"note":""})
        self._refresh_solera();self.on_changed()
        row=len(s["operations"])-1
        self.sol_table.selectRow(row);self.sol_table.editItem(self.sol_table.item(row,0))
    def _delete_solera(self):
        b=self.get_batch()
        if not b:return
        row=self.sol_table.currentRow();ops=(b.get("stage3") or {}).get("operations",[])
        if row<0 or row>=len(ops):return
        del ops[row];self._refresh_solera();self.on_changed()
    def commit_solera_edits(self):
        b=self.get_batch()
        if not b:return
        ops=(b.get("stage3") or {}).get("operations",[])
        for i,op in enumerate(ops):
            if i>=self.sol_table.rowCount():break
            vals=[self.sol_table.item(i,j).text() if self.sol_table.item(i,j) else "" for j in range(7)]
            op.update({"date":vals[0],"type":vals[1],"removed":_num(vals[2]),"added":_num(vals[3]),"source":vals[4],"sourceAgeYears":_num(vals[5]),"note":vals[6]})
        solera_recalculate(b["stage3"]);self.sol_summary.setText(f"Текущий расчётный объём: {b['stage3']['volume']:.2f} л · средний возраст: {b['stage3']['averageAgeYears']:.2f} лет")
        self.on_changed()
    def _image_dir(self):
        path=self.get_path()
        base=Path(path).parent if path else Path.home()/".cidremaker"
        return base/"pix"
    def _refresh_label(self):
        b=self.get_batch() or {};name=b.get("labelImage","");self.image_name.setText(name or "Фото не выбрано")
        if not name:
            self.image_preview.setPixmap(QPixmap());self.image_preview.setText("Фото не выбрано");return
        path=self._image_dir()/name
        if not path.exists():
            self.image_preview.setPixmap(QPixmap());self.image_preview.setText(f"Файл не найден:\n{path}");return
        pix=QPixmap(str(path))
        if pix.isNull():self.image_preview.setText("Формат изображения не поддерживается");return
        self.image_preview.setPixmap(pix.scaled(720,360,Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def _upload_label(self):
        b=self.get_batch()
        if not b:return
        path,_=QFileDialog.getOpenFileName(self,"Выбрать фото этикетки","","Изображения (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:return
        try:
            folder=self._image_dir();folder.mkdir(parents=True,exist_ok=True)
            ext=Path(path).suffix.lower() or ".jpg";name=f"label_{b.get('id','batch')}{ext}"
            shutil.copy2(path,folder/name);b["labelImage"]=name;b["updatedAt"]=datetime.now().astimezone().isoformat()
            self._refresh_label();self.on_changed()
        except Exception as exc:QMessageBox.critical(self,"Не удалось сохранить этикетку",str(exc))
    def _delete_label(self):
        b=self.get_batch()
        if not b or not b.get("labelImage"):return
        name=b["labelImage"];path=self._image_dir()/name
        if QMessageBox.question(self,"Удалить фото","Удалить файл этикетки и ссылку из партии?")!=QMessageBox.Yes:return
        try:
            if path.exists():path.unlink()
            b["labelImage"]="";self._refresh_label();self.on_changed()
        except Exception as exc:QMessageBox.critical(self,"Не удалось удалить этикетку",str(exc))
