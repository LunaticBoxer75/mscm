"""Render every dashboard page headlessly and fail on any exception.

Streamlit's AppTest can't switch between function-based st.navigation pages, so
this swaps st.navigation for a stub that runs one page's function, then runs the
real app.py unmodified. Forces MSCM_STORE_MODE=file so nothing is read from or
written to GitHub, even with a token in .streamlit/secrets.toml.

Usage (from repo root, with the python that has streamlit):
    python scripts/smoke_test_pages.py
Exit code 1 if any page raises.
"""
import os, time, sys
os.environ["MSCM_STORE_MODE"] = "file"  # never touch GitHub from a test
from streamlit.testing.v1 import AppTest
HARNESS = '''
import os, sys, runpy, streamlit as st
sys.path.insert(0, os.getcwd())
class Nav:
    def __init__(self, pages): self.pages = pages
    def run(self):
        target = os.environ["MSCM_TEST_PAGE"]
        next(p for p in self.pages if p._page.__name__ == "page_" + target)._page()
st.navigation = Nav
runpy.run_path("app.py", run_name="__main__")
'''
pages = ["jobs","tracker","todos","networking","interview","referrals","sponsors",
         "skills","insights","fellowships","projects","tools","export"]
bad_total = 0
for p in pages:
    os.environ["MSCM_TEST_PAGE"] = p
    at = AppTest.from_string(HARNESS, default_timeout=300)
    at.run()
    t = time.time(); at.run(); warm = time.time() - t
    n = sum(1 for _ in at.main)
    bad = len(at.exception) + len(at.error)
    bad_total += bad
    print(f"{p:12} warm {warm:5.2f}s  elements {n:5}  {'OK' if not bad else 'BROKEN'}")
    for e in at.exception: print("   EXC:", str(e.value)[:300])
    for e in at.error: print("   ERR:", str(e.value)[:200])
print("problems:", bad_total)
sys.exit(1 if bad_total else 0)
