# Installation

## From source

### Prerequisites

- Python 3.10+ (developed on 3.14)
- [uv](https://docs.astral.sh/uv/) package manager

### Steps

```bash
# Clone the repository
git clone <repo-url>
cd senior-rpa

# Create virtual environment and install dependencies
uv sync

# Install Playwright browser (required for RPA tasks)
uv run playwright install chromium

# Run the application
uv run python main.py web
```

## Portable .exe

Download the latest `senior-rpa.exe` from [GitHub Releases](https://github.com/user/senior-rpa/releases). No installation required — double-click to run.

The executable is self-contained (bundles Python + dependencies + Chromium via Playwright).

### First run

1. Launch `senior-rpa.exe`
2. Your default browser opens to `http://127.0.0.1:8080`
3. If port 8080 is busy, the app auto-selects the next available port
4. If the app is already running, the existing instance gets focus

### Updating

On startup, the app checks GitHub for newer releases. If an update is available, it downloads the new `.exe` to a temporary directory and prompts to apply it on next restart.
