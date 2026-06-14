"""Generate Python dataclasses from the DATEX II XSDs in schemas/.

Run AFTER placing the XSDs (see schemas/README.md).

Output: generated/datex2/  (gitignored)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
OUT = ROOT / "generated" / "datex2"


def main() -> int:
    xsds = sorted(SCHEMAS.rglob("*.xsd"))
    if not xsds:
        sys.stderr.write(
            f"No XSD files found under {SCHEMAS}.\n"
            "See schemas/README.md for one-time setup instructions.\n"
        )
        return 1

    # Use the directory that actually contains the XSDs (handles wizard's
    # DATEXII_3_Profile/ subfolder or flat schemas/ layout).
    xsd_dir = xsds[0].parent
    print(f"Found {len(xsds)} XSD file(s) in {xsd_dir.relative_to(ROOT)}")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "__init__.py").touch()
    (OUT / "__init__.py").touch()

    cmd = [
        sys.executable, "-m", "xsdata", "generate",
        str(xsd_dir),
        "--package", "generated.datex2",
        "--output", "dataclasses",
        # DATEX II has circular cross-namespace refs (Common <-> CommonExtension etc.)
        # `clusters` groups related classes by dependency, avoiding import cycles.
        "--structure-style", "clusters",
        "--unnest-classes",
    ]
    print("  $ " + " ".join(cmd))
    # xsdata shells out to `ruff` for formatting — ensure it can find the venv's bin.
    env = os.environ.copy()
    venv_bin = Path(sys.executable).parent
    env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
