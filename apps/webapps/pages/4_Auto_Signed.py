import os

# ─────────────────────────────────────────────────────────────────────────────
# PDF Auto-Signer — Streamlit Page Wrapper
# ─────────────────────────────────────────────────────────────────────────────

_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auto_signed.py")

with open(_script, encoding="utf-8") as _f:
    exec(compile(_f.read(), _script, "exec"), {"__file__": _script, "__name__": "__main__"})
