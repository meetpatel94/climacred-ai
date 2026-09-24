# Legacy database fixtures (developer/test data only)

These files are MongoDB extended-JSON dumps of what **older ClimaCred builds actually
wrote** into an empty database. They were produced by running the historical code
from commit `a9db8ba` (not hand-written), and are used by `tests/test_legacy_demo.py`
to prove that the current backend removes this data and never serves it.

| File | Produced by (commit a9db8ba) | Documents |
|---|---|---|
| `legacy_autoinsert_db.json` | one dashboard load of the old app: `GET /api/profile`, `GET /api/assessment`, `GET /api/climate-fingerprint` auto-inserted the "ABC Textile" demo and stored a 47.5 fingerprint | profile, assessment, fingerprint |
| `legacy_seed_db.json` | the old `python seed.py --demo` | profile, assessment, fingerprint, transformation plan, report, impact record |

They contain the demo values on purpose (ABC Textile Manufacturing Ltd., 38,500 kWh, ...).
They are never loaded by the application.
