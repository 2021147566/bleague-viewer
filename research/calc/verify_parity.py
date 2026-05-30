"""JS engine ↔ Python second_import_slot parity spot-check."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from gunma_samsung_analysis import role_load_vector  # noqa: E402
from second_import_slot import _vec, team_w  # noqa: E402

DATA = ROOT / "data" / "baseline.json"
b = json.loads(DATA.read_text(encoding="utf-8"))

base = np.array(b["baseRaw"], dtype=float)
c = b["defaultCandidate"]
mpg = float(c.get("avg_MPG", 27))
s = pd.Series({**c, "Player": c["name"]})
iv = _vec(role_load_vector(s))

failed = 0
for code in ["LIN", "AIS", "CCT"]:
    target = np.array(b["targets"][code], dtype=float)
    w = team_w(base, mpg, iv, target)
    ref = b["idealsByMpg"][str(int(mpg))][code]["defaultScore"]["w_after"]
    ok = abs(w - ref) < 0.00015
    print(f"{code} w_after py={w:.4f} ref={ref} {'OK' if ok else 'FAIL'}")
    if not ok:
        failed += 1

raise SystemExit(failed)
