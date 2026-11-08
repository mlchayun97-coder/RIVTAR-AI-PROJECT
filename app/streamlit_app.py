"""RIVATAR website (Streamlit).

Run from the project root:
    streamlit run app/streamlit_app.py

English by default; ?lang=he switches the whole site to Hebrew (RTL). All text comes from
app/content (en.json, he.json, site.json, projects/*.json).
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
import ui  # noqa: E402
from views import about, contact, home, ml_lab, projects, services  # noqa: E402


def _project_page(slug: str):
    def page() -> None:
        projects.render_project(slug)

    page.__name__ = f"project_{slug.replace('-', '_')}"
    return page


def build_pages(lang: str = C.DEFAULT_LANG) -> list:
    brand = C.t("meta.brand", lang)
    title = lambda key: f"{C.t(key, lang)} · {brand}"  # noqa: E731
    pages = [st.Page(home.render, title=C.t("meta.site_title", lang), url_path="home", default=True),
             st.Page(about.render, title=title("nav.about"), url_path="about"),
             st.Page(projects.render_index, title=title("nav.projects"), url_path="projects")]
    pages += [st.Page(_project_page(p["slug"]), title=f'{C.loc(p["name"], lang)} · {brand}',
                      url_path=ui.project_path(p["slug"])) for p in C.projects()]
    pages += [st.Page(services.render, title=title("nav.services"), url_path="services"),
              st.Page(contact.render, title=title("nav.contact"), url_path="contact"),
              st.Page(ml_lab.render, title=title("nav.lab"), url_path="ml-lab")]
    return pages


def main() -> None:
    lang = C.normalize_lang(st.query_params.get("lang"))
    st.set_page_config(page_title=C.t("meta.site_title", lang), page_icon=str(APP_DIR / "assets" / "favicon.png"),
                       layout="wide", initial_sidebar_state="collapsed")
    theme.inject()
    st.navigation(build_pages(lang), position="hidden").run()


if __name__ == "__main__":
    main()
