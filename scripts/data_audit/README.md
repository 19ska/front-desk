# scripts/data_audit/

How the problems in `data/*.csv` were found, before any app code was written. The findings and what the app does
about each are in [../../docs/DATA_NOTES.md](../../docs/DATA_NOTES.md).

```bash
python3 -I scripts/data_audit/audit.py data        # broad profile of both files
python3 -I scripts/data_audit/deep_dive.py data    # follow-ups: duplicates, the August gap, the 9 am peak
```

The scripts are standard library only and read-only.

`verify_a/` and `verify_b/` hold the scripts of two independent auditors. They checked the raw files without seeing
these results, and their conclusions are reconciled at the end of DATA_NOTES. These are exploration scripts, kept as
evidence; the app doesn't use them.
