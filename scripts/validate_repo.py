from pathlib import Path
import xml.etree.ElementTree as ET, zipfile, re, subprocess, tempfile, sys
root=Path(__file__).resolve().parents[1]
errors=[]
for kind in ("schema","full"):
  u=root/"solution"/kind/"unpacked"
  for rel in ("Other/Solution.xml","Other/Customizations.xml","[Content_Types].xml"):
    p=u/rel
    if not p.exists(): errors.append(f"Missing {p}")
    else:
      try: ET.parse(p)
      except Exception as e: errors.append(f"Invalid XML {p}: {e}")
for p in (root/"src/studio-webresources").glob("*.html"):
  text=p.read_text(errors="ignore")
  if "Cloudstrucc Pages Studio" not in text: errors.append(f"Unexpected Studio file {p}")
  scripts=re.findall(r"<script(?:[^>]*)>(.*?)</script>",text,re.S)
  for i,s in enumerate(scripts):
    if not s.strip(): continue
    with tempfile.NamedTemporaryFile("w",suffix=".js",delete=False) as f: f.write(s); name=f.name
    r=subprocess.run(["node","--check",name],capture_output=True,text=True)
    if r.returncode: errors.append(f"JS syntax error {p} script {i}: {r.stderr[:300]}")
for p in (root/"solution").glob("*/packed/*.zip"):
  try:
    with zipfile.ZipFile(p) as z:
      names=set(z.namelist())
      for req in ("Other/Solution.xml","Other/Customizations.xml","[Content_Types].xml"):
        if req not in names: errors.append(f"{p} missing {req}")
  except Exception as e: errors.append(f"Invalid ZIP {p}: {e}")
if errors:
  print("\n".join(errors)); sys.exit(1)
print("Repository validation passed")
