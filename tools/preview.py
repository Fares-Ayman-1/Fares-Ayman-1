"""Write preview.html: the README framed like a dark GitHub profile, using local dist/ cards."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
readme = (ROOT / "README.md").read_text(encoding="utf-8")
readme = readme.replace("https://raw.githubusercontent.com/Fares-Ayman-1/Fares-Ayman-1/output/", "dist/")
page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Profile README preview</title>
<style>body{{margin:0;background:#0d1117;color:#e6edf3;font-family:-apple-system,Segoe UI,sans-serif}}
.wrap{{max-width:1012px;margin:24px auto;display:flex;gap:24px;padding:0 16px}}
aside{{width:296px;flex:none}} aside .av{{width:296px;height:296px;border-radius:50%;background:#161b22 url(tools/portrait.png) center 10%/120% no-repeat;border:1px solid #30363d}}
main{{flex:1;min-width:0;border:1px solid #30363d;border-radius:6px;padding:24px}}
main img{{max-width:100%}} p{{margin:0 0 16px}} main>img{{display:block;margin:0 0 16px}}
@media(max-width:800px){{.wrap{{flex-direction:column}}aside{{width:auto}}aside .av{{width:160px;height:160px}}}}</style></head>
<body><div class="wrap"><aside><div class="av"></div><h2>Fares Ayman</h2><p style="color:#8b949e">Fares-Ayman-1</p></aside>
<main>{readme}</main></div></body></html>"""
(ROOT / "preview.html").write_text(page, encoding="utf-8")
print("wrote preview.html")
