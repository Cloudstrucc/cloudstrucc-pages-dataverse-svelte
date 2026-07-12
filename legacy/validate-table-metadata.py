#!/usr/bin/env python3
from pathlib import Path
import sys, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
files=[ROOT/'solution/schema/unpacked/Other/Customizations.xml',ROOT/'solution/full/unpacked/Other/Customizations.xml']
errors=[]
for f in files:
    root=ET.parse(f).getroot()
    for wrap in root.findall('./Entities/Entity'):
        ent=wrap.find('./EntityInfo/entity'); name=ent.get('Name')
        pn=(ent.findtext('PrimaryNameAttribute') or '').strip(); pi=(ent.findtext('PrimaryIdAttribute') or '').strip()
        attrs={a.findtext('LogicalName'):a for a in ent.findall('./attributes/attribute')}
        if not pn or pn not in attrs: errors.append(f'{f}: {name}: missing primary-name attribute {pn!r}')
        else:
            if attrs[pn].findtext('IsPrimaryName')!='1': errors.append(f'{f}: {name}.{pn}: IsPrimaryName must be 1')
            if attrs[pn].findtext('Type')!='nvarchar': errors.append(f'{f}: {name}.{pn}: primary name must be nvarchar')
        if not pi or pi not in attrs: errors.append(f'{f}: {name}: missing primary-id attribute {pi!r}')
        elif attrs[pi].findtext('IsPrimaryId')!='1': errors.append(f'{f}: {name}.{pi}: IsPrimaryId must be 1')
if errors:
    print('Table metadata validation failed:')
    print('\n'.join(' - '+x for x in errors)); sys.exit(1)
print('Table metadata validation passed for schema and full solutions.')
