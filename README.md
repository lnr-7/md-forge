# md-forge — local file → Markdown converter

## Quick start from GitHub (works anywhere, offline after install)

```bash
git clone https://github.com/<your-org>/md-forge.git
cd md-forge
```

Windows: double-click `run.bat`. Mac/Linux: `./run.sh`.
Then open `http://localhost:8090` in browser.

First run needs internet (installs deps). After that — fully offline.
Office mode: run on one server, team uses `http://<server-ip>:8090`.
Remote mode: each person runs it on own laptop, uses `localhost`.

One Python file. Converts PDF / Word / PowerPoint / Excel / CSV / HTML / etc. to `.md`.
Runs entirely on your own machine or LAN. No file leaves your network.

## Install (once, on one machine)

```bash
pip install "markitdown[all]" flask
```

Needs Python 3.10+.

## Mode 1 — Web page for the whole team (easiest)

```bash
python md_forge.py
```

Then share the address with your team:

```
http://<that-machine's-LAN-IP>:8090
```

Anyone on the network opens it, drags files in, downloads `.md` files back
(single download per file, or one zip for everything). Shows size saved per file.

Change port: `python md_forge.py --port 9000`

## Mode 2 — Watch a dump folder

If your team already dumps files into a shared folder:

```bash
python md_forge.py --watch /path/to/shared/dump_folder
```

Every new supported file is auto-converted into `dump_folder/markdown/<name>.md`.
Polls every 5 s (`--interval` to change).

## Keep it running (Linux server)

```bash
nohup python md_forge.py > md_forge.log 2>&1 &
```

or create a systemd service / Windows Task Scheduler job.

## Supported types

pdf, docx, pptx, xlsx, xls, csv, html, json, xml, txt, epub, zip, msg, images (jpg/png).

Notes:
- Scanned PDFs (images of text) need OCR — markitdown extracts text-layer only.
  Verify in current markitdown docs if you need OCR: https://github.com/microsoft/markitdown
- Legacy `.doc` / `.ppt` (pre-2007) support is weaker than `.docx` / `.pptx`.
- Charts/diagrams inside files become text descriptions or are dropped — Markdown is text.
