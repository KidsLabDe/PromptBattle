# Prompt Battle

Eine lokale Prompt-Battle-App, bei der Spieler gegeneinander antreten und mithilfe von Text-zu-Bild-KI versuchen, Zielbilder so genau wie möglich nachzubilden.

Gebaut mit einem **FastAPI**-Backend (Python) und einem **SvelteKit**-Frontend (TypeScript).

## So funktioniert's

1. Allen Spielern wird ein Zielbild angezeigt
2. Die Spieler formulieren Prompts, um ein KI-Bild zu generieren, das dem Zielbild möglichst nahe kommt
3. Die beste Übereinstimmung gewinnt die Runde

## Erste Schritte

### Voraussetzungen

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) (Python-Paketmanager)

### Installation

```bash
# Python-Abhängigkeiten installieren
uv sync

# Frontend-Abhängigkeiten installieren
cd frontend && npm install && cd ..
```

### Starten

```bash
# Manuell
uv run run.py

# Als systemd-Service (Autostart beim Booten)
sudo ln -s $(pwd)/promptbattle.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now promptbattle

# Logs
journalctl -u promptbattle -f
```

### Konfiguration

Alle Einstellungen über `.env` mit `PB_`-Prefix:

| Variable | Beschreibung | Default |
|---|---|---|
| `PB_IMAGE_BACKEND` | Bildgenerierung: `local` oder `gemini` | `local` |
| `PB_SIMILARITY_BACKEND` | Bewertung: `clip` oder `gemini` | `clip` |
| `PB_GEMINI_API_KEY` | Google Gemini API Key (für gemini-Backends) | — |
| `PB_ROUND_TIME_SECONDS` | Sekunden pro Runde | `60` |
| `PB_LOBBY_TIMEOUT_SECONDS` | Sekunden bis Auto-Start in Lobby | `120` |
| `PB_BASE_THRESHOLD` | Start-Schwellenwert (%) | `25` |

Alle Optionen: siehe `backend/config.py`

## Credits

Dieses Projekt ist inspiriert von [Prompt Battle](https://promptbattle.com/) — einem Live-Event-Format, bei dem Menschen mit Text-zu-Bild-Software gegeneinander antreten.

Das ursprüngliche Prompt-Battle-Format wurde entwickelt von:

- [Florian A. Schmidt](https://florianalexanderschmidt.de/)
- [Sebastian Schmieg](https://sebastianschmieg.com/)

Zusammen mit Designstudierenden der HTW Dresden:

- [Bernadette Geiger](https://bernadettegeiger.com/)
- [Ella Zickerick](https://ellazickerick.de/)
- [Emily Krause](https://emily-krause.com/)
- [Levi Stein](https://is.gd/WVZvnI)
- [Lina Schwarzenberg](https://www.linaschwarzenberg.com/)
- [Robert Hellwig](https://robert-hellwig.com/)

## Lizenz

Creative Commons
