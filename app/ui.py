"""HTML building blocks for the site. Pure functions that return HTML strings (no Streamlit calls),
so they are easy to test. All text is escaped; text in [brackets] is rendered as a visible TODO.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from urllib.parse import quote
from html import escape
from pathlib import Path

import content as C
from theme import STATIC_URL

APP_DIR = Path(__file__).resolve().parent
EVENTS_DIR = APP_DIR / "static" / "events"
LOGO_SVG = APP_DIR / "assets" / "rivatar-logo.svg"
TONES = ["olive", "linen", "wine", "sand", "dusk", "rose"]


# ------------------------------------------------------------------ basics
def txt(text: str, cls: str = "", tag: str = "span", attrs: str = "") -> str:
    """Escaped text in a tag; placeholders ([...]) get the dashed TODO style."""
    classes = " ".join(c for c in (cls, "todo" if C.is_todo(text) else "") if c)
    cls_attr = f' class="{classes}"' if classes else ""
    return f"<{tag}{cls_attr}{attrs}>{escape(text)}</{tag}>"


@lru_cache(maxsize=1)
def logo_mask_css() -> str:
    """st.html strips inline <svg>, so the logo is drawn as a CSS mask filled with currentColor
    (dark in the header, ivory on the hero photo)."""
    svg = re.sub(r"\s+", " ", LOGO_SVG.read_text(encoding="utf-8")).strip()
    url = f'url("data:image/svg+xml,{quote(svg)}")'
    return (f".logo{{display:block;aspect-ratio:331/60;background:currentColor;"
            f"-webkit-mask:{url} center/contain no-repeat;mask:{url} center/contain no-repeat}}")


def logo(cls: str = "logo") -> str:
    return f'<span class="{cls}" role="img" aria-label="RIVATAR"></span>'


def page_url(slug: str) -> str:
    return f"/story-{slug}"


def home_anchor(anchor: str, on_home: bool) -> str:
    return f"#{anchor}" if on_home else f"/#{anchor}"


# ------------------------------------------------------------------ media
@lru_cache(maxsize=1)
def manifest() -> dict:
    path = EVENTS_DIR / "manifest.json"
    if not path.exists():
        return {"events": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def event_images(slug: str) -> list[dict]:
    return manifest().get("events", {}).get(slug, {}).get("images", [])


def img_url(rel: str) -> str:
    return f"{STATIC_URL}/events/{rel}"


def pick_images(slug: str, wants: list[str], skip: set[str] | frozenset[str] = frozenset()) -> list[dict | None]:
    """Pick one image per wanted orientation ('landscape'/'portrait'/'any'), no repeats.
    Images whose file is in `skip` (e.g. already used in the hero) are avoided.
    Falls back to any remaining image; None if the event has too few photos."""
    pool = [i for i in event_images(slug) if i["file"] not in skip]
    out: list[dict | None] = []
    for want in wants:
        choice = next((i for i in pool if want == "any" or i["orientation"] == want), None)
        if choice is None and pool:
            choice = pool[0]
        if choice is not None:
            pool.remove(choice)
        out.append(choice)
    return out


def photo(image: dict | None, cls: str, tag: str = "", tone: str = "sand", full: bool = True,
          eager: bool = False, extra: str = "") -> str:
    """A design 'ph' frame; a toned placeholder when there is no image."""
    inner = (f'<img src="{img_url(image["file"] if full else image["thumb"])}" alt="" '
             f'loading="{"eager" if eager else "lazy"}" decoding="async">' if image else '<div class="ph-img"></div>')
    tag_html = f'<span class="ph-tag">{escape(tag)}</span>' if tag else ""
    return f'<figure class="ph {cls} {tone}">{inner}{tag_html}{extra}</figure>'


# ------------------------------------------------------------------ chrome
def masthead(on_home: bool) -> str:
    links = "".join(f'<a href="{home_anchor(a, on_home)}" target="_self">{escape(lbl)}</a>' for lbl, a in C.NAV)
    links += f'<a class="lab" href="/ml-lab" target="_self">{escape(C.NAV_LAB)}</a>'
    cta_lbl, cta_anchor = C.NAV_CTA
    return f"""
<header class="mast" id="mast">
  <details class="menu"><summary>{escape(C.MENU_LABEL)}</summary><nav aria-label="ניווט נייד">{links}</nav></details>
  <nav aria-label="ניווט ראשי">{links}</nav>
  <a class="wordmark" href="/" target="_self" aria-label="{escape(C.BRAND)}">{logo()}<small>PRODUCTIONS</small></a>
  <a class="cta" href="{home_anchor(cta_anchor, on_home)}" target="_self">{escape(cta_lbl)}</a>
</header>"""


def footer(on_home: bool) -> str:
    nav = "".join(f'<a href="{home_anchor(a, on_home)}" target="_self">{escape(lbl)}</a>' for lbl, a in C.FOOTER_NAV)
    return f"""
<footer class="foot">
  <div class="foot-word">{logo()}</div>
  <div class="foot-row"><span>{escape(C.FOOTER_LINE)}</span><nav aria-label="ניווט תחתון">{nav}</nav></div>
</footer>"""


def wrap(html: str) -> str:
    return f'<div class="site" dir="rtl" lang="he">{html}</div>'


# ------------------------------------------------------------------ home sections
def hero_images() -> tuple[dict | None, dict | None]:
    """Cover = the hero event's last landscape photo (its first one opens the event's story)."""
    landscapes = [i for i in event_images(C.HERO_EVENT) if i["orientation"] == "landscape"]
    cover = landscapes[-1] if landscapes else next(iter(pick_images(C.HERO_EVENT, ["any"])), None)
    portraits = [i for i in event_images(C.HERO_SIDE_EVENT) if i["orientation"] == "portrait"]
    side = portraits[-1] if portraits else next(iter(pick_images(C.HERO_SIDE_EVENT, ["any"])), None)
    return cover, side


def hero_files() -> frozenset[str]:
    return frozenset(i["file"] for i in hero_images() if i)


def hero() -> str:
    cover, side = hero_images()
    disc = "".join(f"<span>{escape(d)}</span>" for d in C.DISCIPLINES)
    return f"""
<div class="hero" id="top">
  {photo(cover, "hero-main", C.HERO_TAG, "sand", eager=True, extra=f'<div class="hero-word">{logo()}</div>')}
  <div class="hero-copy"><h1>{escape(C.HERO_TITLE)}</h1><p class="lede">{escape(C.HERO_LEDE)}</p></div>
  <div class="hero-side">
    {photo(side, "", C.HERO_SIDE_TAG, "rose", full=False, eager=True)}
    {txt(C.HERO_SIDE_CAPTION, tag="p", cls="cap")}
  </div>
  <div class="disciplines">{disc}<span class="lat">{escape(C.DISCIPLINES_LATIN)}</span></div>
</div>"""


def _story_text(ev: dict) -> str:
    n = len(event_images(ev["slug"]))
    type_lbl = C.event_type_label(ev)
    return f"""
<div class="story-text">
  <p class="kicker">{txt(type_lbl, "label")}{txt(ev.get("location", ""), "label")}</p>
  <h3 class="lat">{escape(ev["name"])}</h3>
  {txt(ev.get("desc", ""), "desc", "p")}
  <a class="more" href="{page_url(ev["slug"])}" target="_self">{escape(C.STORY_MORE)} <span>←</span></a>
  <span class="gal-count">{escape(C.GALLERY_COUNT.format(n=n))}</span>
</div>"""


def story(ev: dict, layout: str, k: int) -> str:
    """Three spread layouts from the design, in rotation: a (wide + side), b (text, tall, low), c (pano + strip)."""
    slug, t, used = ev["slug"], C.IMAGE_TAGS, hero_files()
    tone = lambda i: TONES[(k + i) % len(TONES)]  # noqa: E731
    if layout == "a":
        wide, side = pick_images(slug, ["landscape", "portrait"], used)
        return f"""<article class="story s-a">{photo(wide, "wide", t["wide"], tone(0))}
  <div class="side">{photo(side, "", t["detail"], tone(1), full=False)}{_story_text(ev)}</div></article>"""
    if layout == "b":
        tall, low = pick_images(slug, ["portrait", "any"], used)
        return f"""<article class="story s-b">{_story_text(ev)}{photo(tall, "tall", t["portrait"], tone(0))}
  {photo(low, "low", t["detail"], tone(1), full=False)}</article>"""
    pano, *strip = pick_images(slug, ["landscape", "portrait", "any", "portrait"], used)
    strip_html = "".join(photo(im, "", tg, tone(i + 1), full=False)
                         for i, (im, tg) in enumerate(zip(strip, [t["detail"], t["detail"], t["moment"]])))
    return f"""<article class="story s-c">{photo(pano, "pano", t["pano"], tone(0))}{_story_text(ev)}
  <div class="strip">{strip_html}</div></article>"""


def stories() -> str:
    arts = "".join(story(ev, "abc"[k % 3], k) for k, ev in enumerate(C.visible_events()))
    return f"""
<section class="sec" id="stories" aria-labelledby="stories-h">
  <div class="sec-head"><h2 id="stories-h">{escape(C.STORIES_TITLE)}</h2><span class="lat">{escape(C.STORIES_LATIN)}</span>
    <p class="note">{escape(C.STORIES_NOTE)}</p></div>
  <div class="stories">{arts}</div>
</section>"""


def approach() -> str:
    pillars = "".join(f"""<div class="pillar"><span class="lat">{escape(p["latin"])}</span><h3>{escape(p["title"])}</h3>
      <p>{escape(p["text"])}</p></div>""" for p in C.PILLARS)
    return f"""
<section class="sec" id="approach" aria-labelledby="approach-h">
  <div class="sec-head"><h2 id="approach-h">{escape(C.APPROACH_TITLE)}</h2><span class="lat">{escape(C.APPROACH_LATIN)}</span></div>
  <div class="approach">
    <p class="statement">{escape(C.APPROACH_STATEMENT)} <em>{escape(C.APPROACH_STATEMENT_EM)}</em></p>
    <div class="pillars">{pillars}</div>
  </div>
</section>"""


def services() -> str:
    items = "".join(f"""<li class="svc"><h3>{escape(s["title"])}<span class="lat">{escape(s["latin"])}</span></h3>
      <p>{escape(s["text"])}</p><span class="swatch" style="--tone:var(--ph-{s["tone"]})"></span></li>""" for s in C.SERVICES)
    addons = "".join(f"<span>{escape(a)}</span>" for a in C.ADDONS)
    return f"""
<section class="sec" id="services" aria-labelledby="services-h">
  <div class="sec-head"><h2 id="services-h">{escape(C.SERVICES_TITLE)}</h2><span class="lat">{escape(C.SERVICES_LATIN)}</span></div>
  <ul class="svc-list">{items}</ul>
  <p class="addons"><span class="label">{escape(C.ADDONS_LABEL)}</span>{addons}</p>
</section>"""


def about() -> str:
    return f"""
<section class="sec" id="about" aria-labelledby="about-h">
  <div class="about">
    {photo(None, "portrait", C.ABOUT_PORTRAIT_TAG, "linen")}
    <div class="bio">
      <span class="label">{escape(C.ABOUT_LABEL)}</span>
      <h2 class="name" id="about-h">{escape(C.ABOUT_NAME)}</h2>
      {txt(C.ABOUT_ROLE, tag="p")}
      {txt(C.ABOUT_BIO, tag="p")}
    </div>
  </div>
</section>"""


def contact_head() -> str:
    dl = "".join(f"<dt>{escape(k)}</dt>{txt(v, tag='dd')}" for k, v in C.CONTACT_DETAILS)
    return f"""
<div class="contact-head" id="contact">
  <span class="lat">{escape(C.CONTACT_LATIN)}</span>
  <h2 id="contact-h">{escape(C.CONTACT_TITLE)}</h2>
  <dl>{dl}</dl>
</div>"""


def legend(text: str, first: bool = False) -> str:
    return f'<p class="legend{" first" if first else ""}">{escape(text)}</p>'


def estimate_box(case: str | None, result: dict | None) -> str:
    """Estimate panel. Shows the live estimate when the estimator returns one (phase 3)."""
    E = C.ESTIMATE
    case_html = escape(case) if case else f'<span style="color:var(--fg-2)">{escape(E["case_empty"])}</span>'
    if result and result.get("status") == "ok":
        body = (f'<p class="est-num" dir="ltr" style="color:var(--fg)">₪{result["estimate_ils"]:,.0f}</p>'
                f'<div class="est-track"></div><div class="est-ends" style="display:flex;justify-content:space-between;'
                f'direction:ltr;font-size:.85rem;color:var(--fg-2);margin-top:.7rem"><span>₪{result["low_ils"]:,.0f}</span>'
                f'<span>₪{result["high_ils"]:,.0f}</span></div>')
        tag = ""
    else:
        body = (f'<p class="est-num" dir="ltr">₪ —</p><p class="est-pending">{escape(E["unavailable_he"])}'
                f'<span class="lat" dir="ltr">{escape(E["unavailable_en"])}</span></p><div class="est-track"></div>')
        tag = f'<span class="est-tag">{escape(E["tag"])}</span>'
    return f"""
<aside class="estimate" aria-label="{escape(E["label"])}">
  <div class="est-top"><span class="label">{escape(E["label"])}</span>{tag}</div>
  <p class="est-case">{case_html}</p>
  {body}
  <p class="est-fine">{escape(E["fine"])}</p>
</aside>"""


def messages(errors: list[str] | None = None, ok: str | None = None) -> str:
    if errors:
        items = "".join(f"<li>{escape(e)}</li>" for e in errors)
        return f'<div class="form-errors" role="alert">{escape(C.FORM["fix_errors"])}<ul>{items}</ul></div>'
    if ok:
        return f'<div class="form-ok" role="status">{escape(ok)}</div>'
    return ""


# ------------------------------------------------------------------ gallery page
def gallery(ev: dict) -> str:
    imgs = event_images(ev["slug"])
    tiles = "".join(f'<a href="{img_url(i["file"])}" target="_blank" rel="noopener">'
                    f'<img src="{img_url(i["thumb"])}" alt="" loading="lazy" width="{i["width"]}" height="{i["height"]}"></a>'
                    for i in imgs)
    others = "".join(f'<a href="{page_url(o["slug"])}" target="_self"{" aria-current=\"page\"" if o["slug"] == ev["slug"] else ""}>'
                     f'{escape(o["name"])}</a>' for o in C.visible_events())
    return f"""
<div class="gal-head">
  <a class="back" href="/#stories" target="_self">→ {escape(C.GALLERY_BACK)}</a>
  <p class="kicker" style="display:flex;gap:.7rem;flex-wrap:wrap">{txt(C.event_type_label(ev), "label")}{txt(ev.get("location", ""), "label")}</p>
  <h1>{escape(ev["name"])}</h1>
  {txt(ev.get("desc", ""), "desc", "p")}
  <span class="gal-count">{escape(C.GALLERY_COUNT.format(n=len(imgs)))}</span>
</div>
<div class="gallery">{tiles}</div>
<p class="gal-hint">{escape(C.GALLERY_HINT)}</p>
<nav class="gal-others" aria-label="אירועים נוספים">{others}</nav>"""
