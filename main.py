# Standardbibliotheken
import sys
import os
import json
import re

# Drittanbieter-Bibliotheken
import pysrt

# PyQt5
from PyQt5.QtCore import (
    Qt, QTimer, QUrl, pyqtSignal, QAbstractListModel, QModelIndex
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QAction, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QLabel,
    QSlider, QMessageBox, QStatusBar
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

CONFIG_FILE = os.path.expanduser("./transplay_config.json")


class TranscriptEntry:
    """Repräsentiert einen einzelnen Transkriptionseintrag mit Start- und Endzeit sowie Text"""

    def __init__(self, start, end, text):
        self.start = self.to_seconds(start)
        self.end = self.to_seconds(end)
        self.text = text

    @staticmethod
    def to_seconds(t):
        """
        Konvertiert eine Zeitangabe in Sekunden
        :param t: Zeitangabe als srt Zeitobjekt (start oder end) z.b: 00:01:23,456
        :return: Zeit in Sekunden als float : z.B. 83.456
        """
        return t.hours * 3600 + t.minutes * 60 + t.seconds + t.milliseconds / 1000.0


def save_last_paths(data):
    """Speichert die letzten Pfade und Einstellungen in einer JSON-Datei"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)


def load_last_paths():
    """Lädt die letzten Pfade und Einstellungen aus einer JSON-Datei"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


class TranscriptListModel(QAbstractListModel):
    def __init__(self, entries, font_size=24, parent=None):
        super().__init__(parent)
        self.entries = entries  # Liste von TranscriptEntry
        self.search_term = ""
        self.font_size = font_size

    def rowCount(self, parent=QModelIndex()):
        return len(self.entries)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        entry = self.entries[index.row()]
        if role == Qt.DisplayRole:
            return entry.text
        if role == Qt.UserRole:
            return entry
        return None

    def set_search_term(self, term):
        self.search_term = term.lower()
        self.dataChanged.emit(self.index(0), self.index(self.rowCount() - 1))

    def get_highlighted_label(self, index):
        if not index.isValid():
            return QLabel()
        entry = self.entries[index.row()]
        text = entry.text

        label = QLabel()
        label.setWordWrap(True)
        label.setStyleSheet(f"font-size: {self.font_size}pt;")

        if self.search_term and self.search_term in text.lower():
            pattern = re.compile(re.escape(self.search_term), re.IGNORECASE)
            match = pattern.search(text)
            if match:
                highlighted = (
                        text[:match.start()] +
                        '<span style="background-color:#66bb66;">' +
                        text[match.start():match.end()] +
                        '</span>' +
                        text[match.end():]
                )
                label.setTextFormat(Qt.RichText)
                label.setText(highlighted)
            else:
                label.setText(text)
        else:
            label.setText(text)
        return label


class TimelineMarker(QWidget):
    """Custom Widget für Timeline mit Sprungmarken"""

    position_changed = pyqtSignal(int)
    marker_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setMinimumWidth(300)

        # Timeline-Eigenschaften
        self.duration = 1000  # Gesamtdauer in ms
        self.position = 0  # Aktuelle Position
        self.markers = []  # Liste der Marker-Positionen
        self.marker_texts = []  # Texte für Tooltips

        # UI-Eigenschaften
        self.dragging = False
        self.marker_radius = 6
        self.timeline_height = 8

    def set_duration(self, duration):
        """Setzt die Gesamtdauer der Timeline"""
        self.duration = max(1, duration)
        self.update()

    def set_position(self, position):
        """Setzt die aktuelle Wiedergabeposition"""
        self.position = max(0, min(position, self.duration))
        self.update()

    def add_marker(self, position, text=""):
        """Fügt eine Sprungmarke hinzu"""
        if 0 <= position <= self.duration:
            self.markers.append(position)
            self.marker_texts.append(text)
            self.update()

    def clear_markers(self):
        """Entfernt alle Sprungmarken"""
        self.markers.clear()
        self.marker_texts.clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Timeline-Hintergrund
        timeline_y = self.height() // 2
        timeline_rect = self.rect().adjusted(20, timeline_y - self.timeline_height // 2,
                                             -20, timeline_y + self.timeline_height // 2)

        painter.fillRect(timeline_rect, QColor(200, 200, 200))

        # Fortschrittsbalken
        if self.duration > 0:
            progress_width = int((self.position / self.duration) * timeline_rect.width())
            progress_rect = timeline_rect.adjusted(0, 0, progress_width - timeline_rect.width(), 0)
            painter.fillRect(progress_rect, QColor(70, 130, 180))

        # Sprungmarken zeichnen
        for i, marker_pos in enumerate(self.markers):
            if self.duration > 0:
                x = 20 + int((marker_pos / self.duration) * (self.width() - 40))

                # Marker-Kreis
                painter.setBrush(QBrush(QColor(255, 100, 100)))
                painter.setPen(QPen(QColor(200, 50, 50), 2))
                painter.drawEllipse(x - self.marker_radius, timeline_y - self.marker_radius,
                                    self.marker_radius * 2, self.marker_radius * 2)

                # Marker-Linie
                painter.setPen(QPen(QColor(255, 100, 100, 150), 1))
                painter.drawLine(x, 10, x, self.height() - 10)

        # Aktuelle Position (Playhead)
        if self.duration > 0:
            playhead_x = 20 + int((self.position / self.duration) * (self.width() - 40))
            painter.setPen(QPen(QColor(50, 50, 50), 3))
            painter.drawLine(playhead_x, 5, playhead_x, self.height() - 5)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Prüfe ob auf Marker geklickt wurde
            for i, marker_pos in enumerate(self.markers):
                if self.duration > 0:
                    marker_x = 20 + int((marker_pos / self.duration) * (self.width() - 40))
                    if abs(event.x() - marker_x) <= self.marker_radius + 5:
                        self.marker_clicked.emit(marker_pos)
                        return

            # Sonst normale Timeline-Interaktion
            self.dragging = True
            self.update_position_from_mouse(event.x())

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.update_position_from_mouse(event.x())

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def update_position_from_mouse(self, x):
        """Berechnet Position basierend auf Mausklick"""
        relative_x = max(20, min(x, self.width() - 20)) - 20
        timeline_width = self.width() - 40
        if timeline_width > 0:
            new_position = int((relative_x / timeline_width) * self.duration)
            self.set_position(new_position)
            self.position_changed.emit(new_position)


class EnhancedSearchWidget(QWidget):
    """Erweiterte Suche mit Sprungmarken-Navigation"""

    jump_to_result = pyqtSignal(int)  # Index des Suchergebnisses

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_label = None
        self.next_button = None
        self.search_results = []  # Liste der gefundenen Einträge
        self.current_result = -1

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        # Navigation
        nav_layout = QHBoxLayout()

        self.result_label = QLabel("0 Treffer")
        self.result_label.setStyleSheet("color: #666; font-size: 14pt;")

        self.prev_button = QPushButton("◀")
        self.prev_button.clicked.connect(self.go_to_previous)
        self.prev_button.setEnabled(False)
        self.prev_button.setFixedSize(40, 30)

        self.next_button = QPushButton("▶")
        self.next_button.clicked.connect(self.go_to_next)
        self.next_button.setEnabled(False)
        self.next_button.setFixedSize(40, 30)

        self.jump_buttons_layout = QHBoxLayout()

        nav_layout.addWidget(self.result_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addLayout(self.jump_buttons_layout)
        layout.addLayout(nav_layout)

    def set_search_results(self, results):
        """Setzt die Suchergebnisse von außen"""
        self.search_results = results
        self.current_result = -1
        self.update_ui()

    def update_ui(self):
        """Aktualisiert die UI basierend auf Suchergebnissen"""
        count = len(self.search_results)
        self.result_label.setText(f"{count} Treffer")

        # Navigation aktivieren/deaktivieren
        has_results = count > 0
        self.prev_button.setEnabled(has_results)
        self.next_button.setEnabled(has_results)

        # Sprungbuttons erstellen
        self.clear_jump_buttons()
        if count > 0 and count <= 8:  # Maximal 8 Buttons
            for i, result in enumerate(self.search_results):
                btn = QPushButton(f"{i + 1}")
                btn.setFixedSize(30, 25)
                btn.clicked.connect(lambda checked, idx=i: self.jump_to_result_index(idx))
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        border: none;
                        border-radius: 12px;
                        font-size: 11pt;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)
                self.jump_buttons_layout.addWidget(btn)

    def clear_jump_buttons(self):
        """Entfernt alle Sprungbuttons"""
        while self.jump_buttons_layout.count():
            child = self.jump_buttons_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def clear_results(self):
        """Löscht alle Suchergebnisse"""
        self.search_results.clear()
        self.current_result = -1
        self.update_ui()

    def go_to_previous(self):
        """Springt zum vorherigen Suchergebnis"""
        if self.search_results:
            self.current_result = (self.current_result - 1) % len(self.search_results)
            self.jump_to_result.emit(self.current_result)

    def go_to_next(self):
        """Springt zum nächsten Suchergebnis"""
        if self.search_results:
            self.current_result = (self.current_result + 1) % len(self.search_results)
            self.jump_to_result.emit(self.current_result)

    def jump_to_result_index(self, index):
        """Springt zu einem bestimmten Suchergebnis"""
        if 0 <= index < len(self.search_results):
            self.current_result = index
            self.jump_to_result.emit(index)


class AudioTranscriptApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎧 TransPlay: Audio & Kapitel")
        self.setGeometry(100, 100, 500, 900)

        self.player = QMediaPlayer()
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_highlight)

        self.transcript = []
        self.font_size = 24
        self.user_is_dragging = False

        self.last_paths = load_last_paths()

        self.init_ui()
        self.restore_last_session()
        self.model = TranscriptListModel(self.transcript, font_size=self.font_size)

        if not self.last_paths.get("help_shown"):
            self.show_help_box()
            self.last_paths["help_shown"] = True
            save_last_paths(self.last_paths)

        self.transcript_lower = []

    def init_ui(self):
        self.setStyleSheet("* { font-size: 24pt; }")

        open_action = QAction("Öffnen", self)
        open_action.triggered.connect(self.open_files)
        exit_action = QAction("Beenden", self)
        exit_action.triggered.connect(self.close)
        help_action = QAction("Anleitung", self)
        help_action.triggered.connect(self.show_help_box)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("Datei")
        file_menu.addAction(open_action)
        file_menu.addAction(exit_action)
        help_menu = menubar.addMenu("Hilfe")
        help_menu.addAction(help_action)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Live-Suche mit Sprungmarken ab 3 Zeichen…")
        self.search_bar.setFixedHeight(int(self.search_bar.sizeHint().height() * 1.5))
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)  # Millisekunden Verzögerung
        self.search_bar.textChanged.connect(lambda: self.search_timer.start())
        self.search_timer.timeout.connect(self.live_search_with_markers)

        # Enhanced Search Widget
        self.enhanced_search = EnhancedSearchWidget()
        self.enhanced_search.jump_to_result.connect(self.jump_to_search_result)

        self.transcript_list = QListWidget()
        self.transcript_list.itemClicked.connect(self.jump_to_selected)
        self.transcript_list.setStyleSheet(f"font-size: {self.font_size}pt;")
        self.transcript_list.setWordWrap(True)

        self.play_button = QPushButton("▶")
        self.play_button.clicked.connect(self.toggle_playback)

        self.increase_font_button = QPushButton("A+")
        self.increase_font_button.clicked.connect(self.increase_font_size)
        self.decrease_font_button = QPushButton("A−")
        self.decrease_font_button.clicked.connect(self.decrease_font_size)

        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 24pt;")

        # Timeline mit Sprungmarken (ersetzt den normalen Slider)
        self.timeline_widget = TimelineMarker()
        self.timeline_widget.position_changed.connect(self.on_timeline_position_changed)
        self.timeline_widget.marker_clicked.connect(self.on_marker_clicked)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.player.setVolume(50)
        self.volume_label = QLabel("🔊 Lautstärke")

        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_slider)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.play_button)
        control_layout.addStretch()
        control_layout.addWidget(QLabel("Zoom"))
        control_layout.addWidget(self.decrease_font_button)
        control_layout.addWidget(self.increase_font_button)

        layout = QVBoxLayout()
        layout.addWidget(self.search_bar)
        layout.addWidget(self.enhanced_search)
        layout.addWidget(self.transcript_list)
        layout.addLayout(control_layout)
        layout.addWidget(self.time_label)
        layout.addWidget(self.timeline_widget)  # Timeline statt normalem Slider
        layout.addLayout(volume_layout)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Player-Events verbinden
        self.player.positionChanged.connect(self.update_timeline_position)
        self.player.durationChanged.connect(self.update_timeline_duration)

        self.play_button.setFixedSize(60, 40)
        self.increase_font_button.setFixedSize(60, 40)
        self.decrease_font_button.setFixedSize(60, 40)

    def open_files(self):
        audio_file, _ = QFileDialog.getOpenFileName(self, "Wähle Audio-Datei", self.last_paths.get("audio", ""),
                                                    "Audio Files (*.mp3 *.wav)")
        if not audio_file:
            return

        transcript_file, _ = QFileDialog.getOpenFileName(self, "Wähle Transkript-Datei",
                                                         self.last_paths.get("transcript", ""),
                                                         "Subtitle Files (*.srt)")
        if not transcript_file:
            return

        self.last_paths.update({
            "audio": os.path.dirname(audio_file),
            "transcript": os.path.dirname(transcript_file),
            "audio_file": audio_file,
            "transcript_file": transcript_file,
            "position": 0
        })
        save_last_paths(self.last_paths)

        self.load_audio(audio_file)
        self.load_transcript(transcript_file)

    def restore_last_session(self):
        audio_path = self.last_paths.get("audio_file", "")
        transcript_path = self.last_paths.get("transcript_file", "")
        position = self.last_paths.get("position", 0)

        if os.path.isfile(audio_path) and os.path.isfile(transcript_path):
            self.load_audio(audio_path)
            self.load_transcript(transcript_path)
            self.player.setPosition(position)

    def load_audio(self, filepath):
        self.player.stop()  # Audio stoppen
        self.timeline_widget.set_position(0)
        self.timeline_widget.clear_markers()
        self.play_button.setText("▶")  # UI zurücksetzen
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(filepath)))
        self.timer.start()

    def load_transcript(self, filepath):
        try:
            self.transcript_list.clear()  # Vorherige Liste löschen
            self.transcript = []  # Daten zurücksetzen
            self.enhanced_search.clear_results()  # Suchstatus zurücksetzen
            self.timeline_widget.clear_markers()  # Marker entfernen

            subs = pysrt.open(filepath)
            self.transcript = [TranscriptEntry(s.start, s.end, s.text) for s in subs]
            self.transcript_lower = [entry.text.lower() for entry in self.transcript]

            self.restore_full_transcript()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Transkript konnte nicht geladen werden: {e}")

    def restore_full_transcript(self):
        """Zeigt alle Transkript-Einträge wieder an"""
        self.transcript_list.clear()
        for entry in self.transcript:
            self.transcript_list.addItem(entry.text)

    def live_search_with_markers(self):
        """Optimierte Live-Suche mit Sprungmarken und effizientem UI-Update"""
        text = self.search_bar.text().strip()
        self.search_bar.setFocus()

        if len(text) >= 3:
            self.timeline_widget.clear_markers()
            search_term = text.lower()

            # Suchergebnisse und Marker sammeln
            results = []
            for i, entry in enumerate(self.transcript):
                if search_term in entry.text.lower():
                    results.append({'index': i, 'entry': entry, 'text': entry.text})
                    marker_position = int(entry.start * 1000)
                    self.timeline_widget.add_marker(marker_position, entry.text[:50])

            # Setze Treffer für Navigationsleiste
            self.enhanced_search.set_search_results(results)

            # Setze Highlight im Model und aktualisiere Widgets
            self.model.set_search_term(text)
            self.refresh_visible_items()

        elif len(text) == 0:
            self.timeline_widget.clear_markers()
            self.enhanced_search.clear_results()
            self.model.set_search_term("")
            self.refresh_visible_items()

        self.search_bar.setFocus()
        self.search_text()

    def refresh_visible_items(self):
        """Aktualisiert die Widgets der sichtbaren Einträge"""
        for row in range(self.model.rowCount()):
            index = self.model.index(row)
            label = self.model.get_highlighted_label(index)
            self.transcript_list.setIndexWidget(index, label)

    def update_highlight(self):
        if self.user_is_dragging or not self.transcript:
            return
        current_time = self.player.position() / 1000
        for i, entry in enumerate(self.transcript):
            if entry.start <= current_time <= entry.end:
                self.transcript_list.setCurrentRow(i)
                break

    def jump_to_selected(self):
        row = self.transcript_list.currentRow()
        if 0 <= row < len(self.transcript):
            self.player.setPosition(int(self.transcript[row].start * 1000))
            self.player.play()
            self.play_button.setText("⏹")

    def search_text(self):
        text = self.search_bar.text().strip()
        self.transcript_list.clear()
        pattern = re.compile(re.escape(text), re.IGNORECASE)

        total = len(self.transcript)
        counter_label = QLabel("")
        self.statusBar().addPermanentWidget(counter_label)

        self.transcript_list.setUpdatesEnabled(False)

        if total > 2000:
            # Kein Highlighting bei großen Transkripten
            for entry in self.transcript:
                item = QListWidgetItem(entry.text)
                item.setData(Qt.UserRole, entry.text)
                item.setTextAlignment(Qt.AlignLeft)
                self.transcript_list.addItem(item)
            counter_label.setText("⚠ Zu viele Einträge für Markierung")
        else:
            for i, entry in enumerate(self.transcript):
                item_text = entry.text
                item = QListWidgetItem()
                item.setData(Qt.UserRole, item_text)
                item.setTextAlignment(Qt.AlignLeft)

                if text:
                    # Alle Vorkommen markieren
                    highlighted = re.sub(
                        pattern,
                        lambda m: f'<span style="background-color:#66bb66;">{m.group(0)}</span>',
                        item_text
                    )
                    item.setData(Qt.DisplayRole, '')
                    self.transcript_list.addItem(item)
                    self.transcript_list.setItemWidget(item, self.create_highlight_label(highlighted))
                else:
                    item.setText(item_text)
                    self.transcript_list.addItem(item)

                if i % 100 == 0 or i == total - 1:
                    counter_label.setText(f"🔍 Suche: {i + 1}/{total}")
                    QApplication.processEvents()

        self.transcript_list.setUpdatesEnabled(True)
        QTimer.singleShot(3000, lambda: self.statusBar().removeWidget(counter_label))

    def create_highlight_label(self, html_text):
        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet(f"font-size: {self.font_size}pt;")
        label.setText(html_text)
        return label

    def toggle_playback(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_button.setText("▶")
        else:
            if self.player.position() >= self.player.duration():
                self.player.setPosition(0)
            self.player.play()
            self.play_button.setText("⏹")

    def set_volume(self, value):
        self.player.setVolume(value)

    def on_timeline_position_changed(self, position):
        """Timeline-Position geändert"""
        self.user_is_dragging = True
        self.player.setPosition(position)
        self.user_is_dragging = False

    def on_marker_clicked(self, position):
        """Sprungmarke wurde geklickt"""
        self.player.setPosition(position)
        if self.player.state() != QMediaPlayer.PlayingState:
            self.player.play()
            self.play_button.setText("⏹")

    def jump_to_search_result(self, result_index):
        """Springt zu einem Suchergebnis"""
        if result_index < len(self.enhanced_search.search_results):
            result = self.enhanced_search.search_results[result_index]
            entry = result['entry']
            position = int(entry.start * 1000)

            # Audio springen
            self.player.setPosition(position)
            if self.player.state() != QMediaPlayer.PlayingState:
                self.player.play()
                self.play_button.setText("⏹")

            # Liste highlighten
            self.transcript_list.setCurrentRow(result['index'])

    def update_timeline_duration(self, duration):
        """Aktualisiert Timeline-Dauer"""
        self.timeline_widget.set_duration(duration)

    def update_timeline_position(self, position):
        """Aktualisiert Timeline-Position"""
        if not self.user_is_dragging:
            self.timeline_widget.set_position(position)
            self.last_paths["position"] = position
            save_last_paths(self.last_paths)
        self.time_label.setText(self.format_time(position))

    def increase_font_size(self):
        self.font_size += 2
        self.transcript_list.setStyleSheet(f"font-size: {self.font_size}pt;")

    def decrease_font_size(self):
        if self.font_size <= 6:
            return
        self.font_size = max(6, self.font_size - 2)
        self.transcript_list.setStyleSheet(f"font-size: {self.font_size}pt;")

    def format_time(self, ms):
        s = ms // 1000
        h = s // 3600
        m = (s % 3600) // 60
        s = s % 60
        return f"{h:02}:{m:02}:{s:02}"

    def show_help_box(self):
        help_box = QMessageBox(self)
        help_box.setWindowTitle("Willkommen bei TransPlay")
        help_box.setText(
            """
📁 So verwendest du TransPlay mit Sprungmarken:

• Lade eine MP3-Datei und ein passendes Transkript im .srt-Format.
• Klicke auf eine Textzeile um direkt zu dieser Stelle im Audio zu springen.
• Live-Suche ab 3 Zeichen zeigt rote Sprungmarken auf der Timeline.
• Klicke auf rote Marker um direkt dorthin zu springen.
• Nutze die Sprungbuttons (1,2,3...) für schnelle Navigation.
• ◀ / ▶ Buttons für Vor/Zurück durch alle Treffer.
• Steuere die Wiedergabe mit ▶ und ⏹.
• Mit A+ und A− kannst du die Textgröße verändern.

📅 Position und Dateien werden automatisch gespeichert.

Viel Freude mit TransPlay!
"""
        )
        help_box.setStandardButtons(QMessageBox.Ok)
        help_box.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioTranscriptApp()
    window.show()
    sys.exit(app.exec_())
