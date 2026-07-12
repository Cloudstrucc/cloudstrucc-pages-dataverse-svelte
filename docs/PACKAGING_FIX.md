# Packaging fix

The build scripts previously attempted to pack managed packages from an unmanaged-only unpacked solution. PAC CLI correctly rejected that operation with:

```text
Solution package type did not match requested type.
Command line argument: Managed
Package type: Unmanaged
```

The corrected scripts now:

- pack only unmanaged development packages locally;
- require managed artifacts to come from a Dataverse export;
- let managed deployments accept an explicit exported package path;
- remove stale generated managed ZIPs from the repository.

The warning about unexpected children beneath `Entities` remains a signal that the bootstrap solution XML should be replaced by an authoritative Dataverse export/unpack before production release.
