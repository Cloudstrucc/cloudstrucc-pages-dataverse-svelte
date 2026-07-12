# Schema and Studio installation

## Preferred one-package installation

Import:

```text
solution/full/packed/CloudstruccPagesStudio_1_0_2_0_unmanaged.zip
```

This package contains all Cloudstrucc tables and Studio web resources.

## Optional split installation

1. Import `CloudstruccPagesSchema_1_0_2_0_unmanaged.zip`.
2. Import `CloudstruccPagesStudio_1_0_2_0_unmanaged.zip`.
3. Publish all customizations.

## Metadata validation

Before packing, run:

```bash
python3 scripts/validate-solution-manifest.py
python3 scripts/validate-table-metadata.py
```

The second validator checks that each entity has a primary ID and a primary-name attribute and that `cs_name` is marked with `IsPrimaryName=1`.
