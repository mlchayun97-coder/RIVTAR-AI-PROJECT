"""Every static file the site references must be in git with the exact name (the cloud runs Linux, where
case matters), and every static URL must be RELATIVE: on Streamlit Community Cloud the app runs behind a
proxy path, so "/app/static/..." returns 404 there (images show only their alt text, fonts fall back)."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))


def _tracked() -> set[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    return set(out.stdout.splitlines())


def _referenced() -> list[str]:
    """Repo paths of every file the site serves from app/static: photos (all sizes), videos and posters
    from media.json, and the fonts in fonts.css."""
    m = json.loads((APP / "static" / "media.json").read_text(encoding="utf-8"))
    paths = []
    for slug, photos in m.get("projects", {}).items():
        for e in photos.values():
            paths += [f"app/static/projects/{slug}/{e['base']}-{w}.jpg" for w in e["sizes"]]
    for e in m.get("home", {}).values():
        paths += [f"app/static/home/{e['base']}-{w}.jpg" for w in e["sizes"]]
    for slug, vids in m.get("videos", {}).items():
        for v in vids:
            paths += [f"app/static/projects/{slug}/{v['file']}", f"app/static/projects/{slug}/{v['poster']}"]
    css = (APP / "static" / "fonts" / "fonts.css").read_text(encoding="utf-8")
    paths += re.findall(r"url\(([^)]+)\)", css)
    return paths


def test_every_referenced_media_file_is_in_git_with_exact_case():
    tracked = _tracked()
    refs = _referenced()
    assert len(refs) > 250
    missing = [p for p in refs if p not in tracked]
    case_only = [p for p in missing if p.lower() in {t.lower() for t in tracked}]
    assert not case_only, f"case differs from git: {case_only[:5]}"
    assert not missing, f"not committed: {missing[:5]}"


def test_media_never_points_outside_app_static():
    """Nothing may be served from design-reference/ or the Drive export folders (both kept out of git)."""
    for p in _referenced():
        assert p.startswith("app/static/"), p


def test_static_urls_are_relative():
    import theme
    assert not theme.STATIC_URL.startswith("/") and theme.STATIC_URL == "app/static"
    css = (APP / "static" / "fonts" / "fonts.css").read_text(encoding="utf-8")
    assert re.findall(r"url\(([^)]+)\)", css) and "url(/" not in css


@pytest.mark.parametrize("call", ["home.render()", "projects.render_project('aaron-bar-mitzvah')",
                                  "projects.render_index()", "about.render()", "contact.render()"])
def test_rendered_pages_have_no_absolute_static_urls(call):
    from streamlit.testing.v1 import AppTest
    script = (f"import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\n"
              "import theme\nfrom views import home, projects, about, contact\ntheme.inject()\n" + call)
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    assert not at.exception
    html = " ".join(str(h.proto.body) for h in at.get("html"))
    assert "app/static/" in html
    assert not re.search(r"""(src|href|poster|srcset)=["']/app/static|, /app/static|url\(/app/static""", html)


def test_static_serving_config_at_repo_root():
    cfg = ROOT / ".streamlit" / "config.toml"
    assert ".streamlit/config.toml" in _tracked()
    assert re.search(r"^\s*enableStaticServing\s*=\s*true", cfg.read_text(encoding="utf-8"), re.M)
