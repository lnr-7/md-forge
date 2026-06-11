#!/usr/bin/env python3
"""
md-forge: local file -> Markdown converter for teams.

Two modes:
  1. Web UI (default)   : python md_forge.py            -> http://<server-ip>:8090
  2. Watch folder       : python md_forge.py --watch /path/to/dump_folder
                          converts every new file into ./dump_folder/markdown/

Install once:
  pip install "markitdown[all]" flask

Supported inputs (via Microsoft markitdown): pdf, docx, pptx, xlsx, xls, csv,
html, json, xml, txt, epub, images-with-text (needs OCR deps), zip, and more.
"""

import argparse
import io
import os
import re
import sys
import time
import zipfile
from pathlib import Path

from markitdown import MarkItDown

CONVERTER = MarkItDown()

SUPPORTED = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv",
    ".html", ".htm", ".json", ".xml", ".txt", ".epub", ".msg", ".zip",
    ".jpg", ".jpeg", ".png", ".rtf", ".odt",
}


def safe_stem(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"[^\w\-. ]", "_", stem).strip() or "converted"


def convert_bytes(filename: str, data: bytes) -> str:
    """Convert raw file bytes to markdown text."""
    ext = Path(filename).suffix.lower()
    result = CONVERTER.convert_stream(io.BytesIO(data), file_extension=ext)
    return result.text_content or ""


def convert_path(path: Path) -> str:
    result = CONVERTER.convert(str(path))
    return result.text_content or ""


# ---------------------------------------------------------------- watch mode
def watch(folder: Path, interval: int = 5) -> None:
    out_dir = folder / "markdown"
    out_dir.mkdir(exist_ok=True)
    seen: dict[str, float] = {}
    print(f"[md-forge] watching {folder}  ->  {out_dir}  (every {interval}s, Ctrl+C to stop)")
    while True:
        for p in folder.iterdir():
            if not p.is_file() or p.suffix.lower() not in SUPPORTED:
                continue
            mtime = p.stat().st_mtime
            if seen.get(p.name) == mtime:
                continue
            # skip files still being copied (size changing)
            s1 = p.stat().st_size
            time.sleep(1)
            if p.stat().st_size != s1:
                continue
            target = out_dir / (safe_stem(p.name) + ".md")
            try:
                target.write_text(convert_path(p), encoding="utf-8")
                seen[p.name] = mtime
                print(f"[ok]   {p.name}  ->  markdown/{target.name}")
            except Exception as e:  # noqa: BLE001
                seen[p.name] = mtime
                print(f"[fail] {p.name}: {e}")
        time.sleep(interval)


# ------------------------------------------------------------------ web mode
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>md-forge — file to Markdown</title>
<style>
  :root{
    --paper:#fbfaf7; --ink:#1c2430; --ink-soft:#5b6675;
    --line:#d8d4ca; --accent:#0f62fe; --ok:#1a7f4b; --bad:#b3261e;
    --mono:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);
       font:15px/1.5 var(--mono);padding:48px 20px}
  main{max-width:640px;margin:0 auto}
  h1{font-size:20px;font-weight:600;margin:0}
  h1 .ext{color:var(--accent)}
  p.sub{color:var(--ink-soft);margin:6px 0 28px;font-size:13px}
  #drop{border:1.5px dashed var(--line);padding:48px 24px;text-align:center;
        cursor:pointer;background:#fff;transition:border-color .15s}
  #drop.hot{border-color:var(--accent)}
  #drop b{color:var(--accent)}
  #drop small{display:block;margin-top:8px;color:var(--ink-soft)}
  input[type=file]{display:none}
  table{width:100%;border-collapse:collapse;margin-top:24px;font-size:13px}
  td{padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
  td.name{word-break:break-all}
  td.size{text-align:right;white-space:nowrap;color:var(--ink-soft)}
  td.size .save{color:var(--ok)}
  td.st{white-space:nowrap;text-align:right}
  .ok{color:var(--ok)} .bad{color:var(--bad)} .busy{color:var(--ink-soft)}
  a.dl{color:var(--accent);text-decoration:none}
  a.dl:hover{text-decoration:underline}
  #zip{display:none;margin-top:18px;background:var(--ink);color:#fff;border:0;
       font:inherit;padding:10px 18px;cursor:pointer}
  footer{margin-top:40px;font-size:12px;color:var(--ink-soft)}
</style>
</head>
<body>
<main>
  <h1>md-forge <span class="ext">*.* → .md</span></h1>
  <p class="sub">Converts PDF / Word / PowerPoint / Excel / CSV / HTML and more to Markdown. Runs on this network only — files never leave it.</p>

  <div id="drop">
    <b>Drop files here</b> or click to choose<br>
    <small>multiple files OK</small>
    <input type="file" id="pick" multiple>
  </div>

  <table id="list"></table>
  <button id="zip">Download all as .zip</button>

  <footer>pdf · docx · pptx · xlsx · csv · html · json · txt · epub</footer>
</main>

<script>
const drop=document.getElementById('drop'),pick=document.getElementById('pick'),
      list=document.getElementById('list'),zipBtn=document.getElementById('zip');
const done=[];

drop.onclick=()=>pick.click();
['dragover','dragenter'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('hot');}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('hot');}));
drop.addEventListener('drop',ev=>handle(ev.dataTransfer.files));
pick.onchange=()=>handle(pick.files);

function fmt(n){return n>1048576?(n/1048576).toFixed(1)+' MB':n>1024?(n/1024).toFixed(0)+' KB':n+' B';}

async function handle(files){
  for(const f of files){
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="name">${f.name}</td><td class="size">${fmt(f.size)}</td><td class="st busy">converting…</td>`;
    list.appendChild(tr);
    const st=tr.querySelector('.st'), sz=tr.querySelector('.size');
    try{
      const fd=new FormData(); fd.append('file',f);
      const r=await fetch('/convert',{method:'POST',body:fd});
      if(!r.ok){st.textContent='failed: '+(await r.text()).slice(0,80);st.className='st bad';continue;}
      const blob=await r.blob();
      const mdName=f.name.replace(/\\.[^.]+$/,'')+'.md';
      done.push({name:mdName,blob});
      const url=URL.createObjectURL(blob);
      const pct=f.size>0?Math.max(0,Math.round((1-blob.size/f.size)*100)):0;
      sz.innerHTML=`${fmt(f.size)} → ${fmt(blob.size)} <span class="save">−${pct}%</span>`;
      st.innerHTML=`<a class="dl" href="${url}" download="${mdName}">download .md</a>`;
      st.className='st ok';
      if(done.length>1)zipBtn.style.display='inline-block';
    }catch(e){st.textContent='failed: '+e;st.className='st bad';}
  }
}

zipBtn.onclick=async()=>{
  const fd=new FormData();
  done.forEach(d=>fd.append('files',d.blob,d.name));
  const r=await fetch('/zip',{method:'POST',body:fd});
  const url=URL.createObjectURL(await r.blob());
  const a=document.createElement('a');a.href=url;a.download='markdown.zip';a.click();
};
</script>
</body>
</html>"""


def run_web(host: str, port: int) -> None:
    from flask import Flask, Response, request

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

    @app.get("/")
    def index():
        return Response(PAGE, mimetype="text/html")

    @app.post("/convert")
    def convert():
        f = request.files.get("file")
        if not f or not f.filename:
            return "no file", 400
        ext = Path(f.filename).suffix.lower()
        if ext not in SUPPORTED:
            return f"unsupported type: {ext}", 415
        try:
            md_text = convert_bytes(f.filename, f.read())
        except Exception as e:  # noqa: BLE001
            return f"conversion error: {e}", 500
        out = safe_stem(f.filename) + ".md"
        return Response(
            md_text,
            mimetype="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{out}"'},
        )

    @app.post("/zip")
    def zip_all():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in request.files.getlist("files"):
                z.writestr(f.filename, f.read())
        buf.seek(0)
        return Response(
            buf.read(),
            mimetype="application/zip",
            headers={"Content-Disposition": 'attachment; filename="markdown.zip"'},
        )

    print(f"[md-forge] web UI on http://0.0.0.0:{port}  (share http://<this-machine-ip>:{port} with team)")
    app.run(host=host, port=port)


def main() -> None:
    ap = argparse.ArgumentParser(description="Local file -> Markdown converter")
    ap.add_argument("--watch", metavar="FOLDER", help="watch a folder instead of running web UI")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--interval", type=int, default=5, help="watch poll seconds")
    args = ap.parse_args()

    if args.watch:
        folder = Path(args.watch).expanduser().resolve()
        if not folder.is_dir():
            sys.exit(f"not a folder: {folder}")
        watch(folder, args.interval)
    else:
        run_web(args.host, args.port)


if __name__ == "__main__":
    main()
