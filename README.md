# NUP GUI

A graphical interface for the **NX Package Format** (`.nup`).

NUP GUI is a small desktop front end for [`nup`](https://github.com/a55uka/nup), the command-line tool that packs unencrypted Nintendo Switch / Switch 2 game dumps into a single compressed `.nup` container. Instead of typing commands, you pick files and folders, press a button, and watch the progress.

> **Unofficial.** This project is a third-party GUI. It does not reimplement the format: it builds the right `nup` commands and runs them for you. The format and the reference tool belong to their original author.

<!-- Add a screenshot here, e.g. ![NUP GUI](docs/screenshot.png) -->

## Features

- **Pack** a dump folder (`base/`, `updates/`, `dlc/`) into a `.nup`, with a compression level selector (1–10), optional Title ID and display version.
- **Unpack** a `.nup`, fully or only a part (`--package base|update|addon`, `--subtree romfs`).
- **List** every file inside a `.nup`.
- **Info** about the container, with optional file tree.
- **Verify** integrity (structure and per-file SHA-256), with a fast mode.
- Live **progress bar**, plus start time, end time and duration of every run.
- Color-coded output log, and a **Stop** button to cancel a running job.
- Dark theme, sidebar navigation, scales on high-DPI screens.
- Standard library only, no extra Python packages needed for the GUI.

## Requirements

- Windows, Linux or macOS with **Python 3** and **tkinter**
  (tkinter ships with the Windows installer from python.org; on Debian/Ubuntu install it with `sudo apt install python3-tk`).
- The [`nup`](https://github.com/a55uka/nup) command-line tool, installed and working (`nup --help`).
  Note that `nup` itself needs a recent Python (3.12 or newer at the time of writing).

## Installation

Clone the repository:

```bash
git clone git@github.com:emulation/nup_gui.git
cd nup_gui
```

(HTTPS works too: `git clone https://github.com/emulation/nup_gui.git`.)

Install `nup` if you don't have it yet:

```bash
git clone https://github.com/a55uka/nup
pip install ./nup/tools/nup
```

## Usage

Run the GUI directly with Python:

```bash
python nup_gui.py
```

The program looks for `nup` automatically (in your `PATH`, next to the GUI, in `dist/`, or in a local `.venv`). If it can't find it, type or browse to the path in the **Programa nup** field at the top. Leaving that field empty makes the GUI run `python -m nup.cli` instead.

Typical workflow:

1. Open a tab in the sidebar (**Empaquetar**, **Desempaquetar**, **Listar**, **Info**, **Verificar**).
2. Choose the files or folders with the **Examinar** buttons.
3. Press the action button and follow the progress bar and the output log.

| Tab | Runs |
| --- | --- |
| Empaquetar | `nup pack <dump_dir> <out.nup> [--level N] [--title-id HEX] [--display-version V]` |
| Desempaquetar | `nup extract <file.nup> <dest> [--package base\|update\|addon] [--subtree romfs]` |
| Listar | `nup list <file.nup>` |
| Info | `nup info <file.nup> [--tree]` |
| Verificar | `nup verify <file.nup> [--fast]` |

The exact command is always echoed at the top of each run in the output log.

> The percentage on the progress bar is read from what `nup` prints. If the tool doesn't print percentages for an operation, the bar shows an animation while it works and fills to 100% when the job finishes successfully.

## Build a standalone executable

You can bundle the GUI into a single `.exe` with [PyInstaller](https://pyinstaller.org):

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name nup_gui nup_gui.py
```

The result is `dist/nup_gui.exe`. Put it in the same folder as `nup.exe` (which you can build the same way from the `nup` repo) and the GUI will find it by itself.

Tips:

- Always build from the file you actually edited, and check the version shown in the window title.
- Some antivirus programs flag `--onefile` PyInstaller executables as suspicious (false positive). Building with `--onedir` instead of `--onefile` usually avoids it.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `SyntaxError: f-string expression part cannot include a backslash` when running `nup` | Your Python is older than 3.12. Use Python 3.12+ for `nup`. |
| `.venv\Scripts\activate` fails in PowerShell | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or use Git Bash with `source .venv/Scripts/activate`. |
| The window shows an old version | You are running an old copy of the script or `.exe`. Rebuild from the right file. |
| "Faltan datos" warning | A required file or folder field is empty. |

## Project layout

```
nup_gui/
├── nup_gui.py   # the whole application
└── README.md
```

## Credits

- The NX Package Format and the `nup` tool: [a55uka/nup](https://github.com/a55uka/nup).

## License

Add the license of your choice here (for example MIT) and include a `LICENSE` file.



<img width="1086" height="839" alt="image" src="https://github.com/user-attachments/assets/f27f0cf1-0408-4b42-a6e6-41c5e5913c4a" />


<img width="1085" height="848" alt="image" src="https://github.com/user-attachments/assets/e4479b0e-b4ec-4257-b104-a902144ae325" />

<img width="2548" height="1385" alt="image" src="https://github.com/user-attachments/assets/67d40ea2-a273-4cec-a526-acb3e5482401" />


<img width="2559" height="1379" alt="image" src="https://github.com/user-attachments/assets/54307f88-c34e-490a-b95e-0d4f03cf5d1c" />


<img width="1075" height="843" alt="image" src="https://github.com/user-attachments/assets/5f1025fc-9426-46c2-aad1-b13718a237e2" />



