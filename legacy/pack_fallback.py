#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys, zipfile
root=Path(__file__).resolve().parents[1]
for validator in ["validate-solution-manifest.py","validate-table-metadata.py"]:
    subprocess.run([sys.executable,str(root/"scripts"/validator)],check=True)
for kind,base in (("schema","CloudstruccPagesSchema"),("full","CloudstruccPagesStudio")):
    src=root/"solution"/kind/"unpacked"; out=root/"solution"/kind/"packed"; out.mkdir(parents=True,exist_ok=True)
    dest=out/f"{base}_1_0_2_0_unmanaged.zip"
    if dest.exists(): dest.unlink()
    with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as z:
        z.write(src/"Other"/"Solution.xml", "solution.xml")
        z.write(src/"Other"/"Customizations.xml", "customizations.xml")
        z.write(src/"[Content_Types].xml", "[Content_Types].xml")
        for path in src.rglob("*"):
            if not path.is_file(): continue
            rel=path.relative_to(src).as_posix()
            if rel in {"Other/Solution.xml","Other/Customizations.xml","[Content_Types].xml"}: continue
            z.write(path,rel)
    subprocess.run([sys.executable,str(root/"scripts"/"normalize-solution-zip.py"),str(dest),"--validate-only"],check=True)
    print(dest)
