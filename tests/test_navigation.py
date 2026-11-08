"""Navigation on the deployed site: every internal link is a full page load (a new Streamlit session), so
the intro must be suppressed by the URL (intro=0) and by the browser (sessionStorage), and must only ever
show on the first, parameter-free entry to the home page. The loading screen must be dark."""
import re
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path[:0] = [str(APP), str(ROOT / "src")]

PAGES = ["home.render()", "about.render()", "projects.render_index()", "projects.render_project('eden-binyamin')",
         "services.render()", "contact.render()", "ml_lab.render()"]


def _render(call: str, query: dict | None = None, seen: bool = True) -> str:
    from streamlit.testing.v1 import AppTest
    script = (f"import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\n"
              "import streamlit as st\n"
              + "".join(f"st.query_params[{k!r}] = {v!r}\n" for k, v in (query or {}).items())
              + f"from views import common\ncommon.intro_seen = lambda: {seen!r}\n"
              "import theme\nfrom views import home, about, projects, services, contact, ml_lab\ntheme.inject()\n" + call)
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    assert not at.exception, call
    return " ".join(str(h.proto.body) for h in at.get("html"))


@pytest.mark.parametrize("path,query,seen,show", [
    ("", {}, False, True),                      # first entry to the home page
    ("", {}, True, False),                      # already seen in this browser
    ("", {"intro": "0"}, False, False),         # came from an internal link
    ("", {"lang": "he"}, False, False),         # language switch / any page parameter
    ("about", {}, False, False),                # never on another page
    ("project-eden-binyamin", {}, False, False),
])
def test_intro_only_on_first_parameter_free_home_visit(path, query, seen, show):
    from views import common
    assert common.should_show_intro(path, query, seen) is show


def test_intro_rendered_on_home_only_and_not_after_an_internal_link():
    assert 'class="intro"' in _render("home.render()", seen=False)
    assert 'class="intro"' not in _render("home.render()", {"intro": "0"}, seen=False)
    assert 'class="intro"' not in _render("home.render()", {"lang": "he"}, seen=False)
    assert 'class="intro"' not in _render("about.render()", seen=False)


@pytest.mark.parametrize("call", PAGES)
@pytest.mark.parametrize("lang", ["en", "he"])
def test_every_internal_link_carries_intro_0(call, lang):
    html = _render(call, {"lang": lang} if lang == "he" else None).replace("&amp;", "&")
    hrefs = re.findall(r'href="([^"]*)"', html)
    assert not [h for h in hrefs if h.startswith("/")], "absolute internal link (breaks behind the Cloud proxy path)"
    links = [h for h in hrefs if not re.match(r"(https?:|mailto:|tel:|#|data:)", h)]
    assert links, call
    missing = [h for h in links if "intro=0" not in h]
    assert not missing, missing[:5]
    if lang == "he":  # the language is kept on every internal link (except the switch back to English)
        assert all("lang=he" in h for h in links if "lang=en" not in h)


def test_language_switch_keeps_the_page_and_skips_the_intro():
    import ui
    assert ui.Ctx("en", "").href("") == "./?intro=0"  # home, relative
    html = ui.masthead(ui.Ctx("he", "project-eden-binyamin"), "projects")
    assert 'href="project-eden-binyamin?lang=en&intro=0"' in html


def test_intro_script_uses_session_storage_safely():
    from views import common
    js = common._INTRO_JS
    assert "sessionStorage.getItem" in js and "sessionStorage.setItem" in js
    for call in ("sessionStorage.getItem", "sessionStorage.setItem", "d.cookie"):
        line = next(l for l in js.splitlines() if call in l)
        assert "try {" in line and "catch (e)" in line, line  # blocked storage never breaks the page


def test_streamlit_theme_is_dark_so_the_loading_screen_matches_the_site():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    theme = cfg["theme"]
    assert theme["base"] == "dark"
    assert theme["backgroundColor"].lower() == "#000000"
    assert theme["primaryColor"] and theme["textColor"]
    assert cfg["server"]["enableStaticServing"] is True
