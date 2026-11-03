"""RIVATAR Productions website (Streamlit).

Run from the project root:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
for p in (APP_DIR, APP_DIR.parent / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

import content as C  # noqa: E402
import theme  # noqa: E402
from views import gallery, home, ml_lab  # noqa: E402


def _gallery_page(slug: str):
    def page() -> None:
        gallery.render(slug)

    page.__name__ = f"story_{slug.replace('-', '_')}"
    return page


def build_pages() -> list:
    pages = [st.Page(home.render, title=C.BRAND, url_path="home", default=True)]
    pages += [st.Page(_gallery_page(ev["slug"]), title=f'{C.display_name(ev)} · {C.BRAND}',
                      url_path=f'story-{ev["slug"]}') for ev in C.visible_events()]
    pages.append(st.Page(ml_lab.render, title=f"{C.NAV_LAB} · {C.BRAND}", url_path="ml-lab"))
    return pages


def main() -> None:
    st.set_page_config(page_title=C.BRAND, page_icon=str(APP_DIR / "assets" / "favicon.png"),
                       layout="wide", initial_sidebar_state="collapsed")
    theme.inject()
    st.navigation(build_pages(), position="hidden").run()


if __name__ == "__main__":
    main()
