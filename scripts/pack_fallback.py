from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[1]
for kind,base in [("schema","CloudstruccPagesSchema"),("full","CloudstruccPagesStudio")]:
    src=root/"solution"/kind/"unpacked"
    out=root/"solution"/kind/"packed"
    out.mkdir(parents=True,exist_ok=True)
    for package_type in ("unmanaged","managed"):
        dest=out/f"{base}_1_0_0_0_{package_type}.zip"
        with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as z:
            for p in src.rglob("*"):
                if p.is_file(): z.write(p,p.relative_to(src).as_posix())
        print(dest)
print("Fallback ZIPs created. Use PAC CLI for authoritative Dataverse packaging and managed conversion.")
