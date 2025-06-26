# TransPlay

**TransPlay** ist eine moderne Qt-Anwendung zur synchronisierten Wiedergabe von Audiodateien mit einem Transkript im SRT-Format.

Ideal für Interviews, Podcasts, Vorträge oder Barrierefreiheit.

## Funktionen

* ▶ Wiedergabe von MP3- und WAV-Dateien mit synchronisiertem Transkript
* 🔍 Volltextsuche mit Live-Markierung ab 3 Zeichen
* ■ Klicken auf Text springt zur passenden Stelle im Audio
* ⏹ Automatische Wiederaufnahme bei letzter Position
* ↕ Einstellbare Schriftgröße (Zoom)
* 🔊 Lautstärkeregler
* 📁 Speicherung der zuletzt verwendeten Datei und Abspielposition
* 🔹 Optionales Hilfe-Fenster beim ersten Start

## Voraussetzungen

* Python 3.8+
* Abhängigkeiten:

  ```bash
  pip install PyQt5 pysrt
  ```

## Starten der App

```bash
python3 main.py
```

## Bedienung

1. **Datei öffnen**: Wähle eine MP3- oder WAV-Datei sowie ein passendes .SRT-Transkript
2. **Text durchklicken**: Klicke auf eine Zeile im Text, um die Stelle im Audio zu hören
3. **Suche verwenden**: Gib einen Begriff ein (mind. 3 Buchstaben), Treffer werden grün markiert
4. **Slider benutzen**: Ziehe die Leiste, um beliebige Stellen anzuspringen
5. **Zoom und Lautstärke**: Steuere Textgröße und Lautstärke unten

## Dateiformat

* **Audio**: `.mp3`, `.wav`
* **Transkript**: `.srt` (SubRip Subtitle Format)

Beispiel `.srt`:

```
1
00:00:00,000 --> 00:00:03,000
Das ist ein Beispiel.

2
00:00:03,000 --> 00:00:06,000
Dies ist der zweite Satz.
```

## Speicherort

* Konfigurationsdatei: `./transplay_config.json`

## Lizenz

MIT-Lizenz

---

**Hinweis**: 

Dieses Projekt ist für Desktop-Nutzung optimiert. 
Getestartet mit Python 3.8 und PyQt5. Funktioniert auf **macOS**. 
Windows und Linux sollten ebenfalls kompatibel sein, aber nicht getestet.
Touch-Eingabe (Tablet) funktioniert, ist aber nicht vorrangig getestet.

## Beispieldaten
Alle daten wurden selber generiert und sind frei nutzbar.
Der Text ist aus dem Original vom Gutenberg-Projekt (https://www.projekt-gutenberg.org/rilke/erzaehlg/chap005.html) und wurde von mir ins SRT-Format umgewandelt.
KI-Stimmen wurden mit "Text to Speech: Voice Reader" generiert (https://apps.apple.com/de/app/text-to-speech-voice-reader/id1626767582).