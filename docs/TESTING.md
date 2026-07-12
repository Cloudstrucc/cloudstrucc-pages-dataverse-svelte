# Testing

## Local structural tests

```bash
npm test
```

Checks include XML parsing, expected solution files, web-resource presence, JavaScript syntax extraction, and ZIP contents.

## Environment tests

1. Import schema solution into a disposable environment.
2. Confirm all custom tables and columns exist.
3. Import full unmanaged solution.
4. Open the admin web resource.
5. Create a test website for each theme.
6. Confirm English/French setup.
7. Open Studio and add/edit/reorder components.
8. Test panel collapse/restore and canvas fit.
9. Publish and verify the Power Pages site.
10. Run Solution Checker and accessibility scans.

Never mark a release production-ready until these environment tests pass.
