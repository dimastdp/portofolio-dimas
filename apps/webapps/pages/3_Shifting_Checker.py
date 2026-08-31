import os

# ─────────────────────────────────────────────────────────────────────────────
# Shifting Checker — Streamlit Page Wrapper
# ─────────────────────────────────────────────────────────────────────────────
# File ini adalah wrapper tipis untuk menjadikan shifting_checker.py sebagai
# halaman ke-3 dalam Streamlit multi-page app.
# File asli (shifting_checker.py) TIDAK diubah sama sekali.
# ─────────────────────────────────────────────────────────────────────────────

_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shifting_checker.py")

with open(_script, encoding="utf-8") as _f:
    exec(compile(_f.read(), _script, "exec"), {"__file__": _script, "__name__": "__main__"})
