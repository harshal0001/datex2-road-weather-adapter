# DATEX II XSD setup

The DATEX II v3.4 XSD files are **not committed** (licensing) — download them once.

## One-time setup

1. Go to **https://webtool.datex2.eu/**
2. Choose: **DATEX II v3.4** → profile **MeteorologicalInformationPublication**
   (or the full v3.4 model if you want to support more publication types).
3. Click **Generate** → download the ZIP.
4. Extract `DATEXII_3_*.xsd` (and any imports it references) into this folder:
   ```
   schemas/
   ├── DATEXII_3_MeteorologicalInformationPublication.xsd
   ├── DATEXII_3_Common.xsd
   └── ... (any other imported XSDs)
   ```
5. Run the dataclass generator:
   ```bash
   python scripts/generate_dataclasses.py
   ```

That writes Python dataclasses to `generated/datex2/`, which the mapper imports.

## Re-generating

Whenever you swap profile or upgrade DATEX II version, drop the new XSDs in and re-run the
generator. `generated/datex2/` is gitignored and disposable.
