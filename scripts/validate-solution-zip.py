#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('zip_path')
args = parser.parse_args()
path = Path(args.zip_path)
if not path.is_file():
    print(f'ERROR: solution ZIP not found: {path}', file=sys.stderr)
    raise SystemExit(1)
with zipfile.ZipFile(path) as zf:
    names = set(zf.namelist())
required = {'solution.xml', 'customizations.xml', '[Content_Types].xml'}
missing = sorted(required - names)
if missing:
    print('ERROR: invalid Dataverse solution ZIP; missing root files: ' + ', '.join(missing), file=sys.stderr)
    raise SystemExit(1)
print(f'Solution ZIP structure valid: {path}')
