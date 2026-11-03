"""HTML building blocks. Pure functions that return HTML strings (no Streamlit calls), so they are easy
to test. All text is escaped; text in [brackets] is rendered as a visible TODO.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import quote

import content as C
from theme import STATIC_URL

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
LOGO_SVG = APP_DIR / "assets" / "rivatar-logo.svg"
WHATSAPP_BASE = "https://wa.me/"

NAV = ("home", "about", "projects", "services", "contact")
PAGE_PATHS = {"home": "", "about": "about", "projects": "projects", "services": "services",
              "contact": "contact", "lab": "ml-lab"}


# ------------------------------------------------------------------ context
@dataclass(frozen=True)
class Ctx:
    """Language and current page. Every link keeps the language (?lang=he)."""
    lang: str = "en"
    path: str = ""  # current page path without leading slash ("" = home)

    @property
    def dir(self) -> str:
        return "rtl" if self.lang == "he" else "ltr"

    def t(self, key: str, **fmt) -> str:
        return C.t(key, self.lang, **fmt)

    def loc(self, field) -> str:
        return C.loc(field, self.lang)

    def href(self, path: str, lang: str | None = None) -> str:
        lang = lang or self.lang
        base = "/" + path.strip("/")
        return f"{base}?lang={lang}" if (lang != C.DEFAULT_LANG or lang != self.lang) else base


def page_path(page: str) -> str:
    return PAGE_PATHS.get(page, page)


def project_path(slug: str) -> str:
    return f"project-{slug}"


# ------------------------------------------------------------------ basics
def txt(text: str, cls: str = "", tag: str = "span", attrs: str = "") -> str:
    """Escaped text in a tag; placeholders ([...]) get the dashed TODO style."""
    classes = " ".join(c for c in (cls, "todo" if C.is_todo(text) else "") if c)
    cls_attr = f' class="{classes}"' if classes else ""
    return f"<{tag}{cls_attr}{attrs}>{escape(text)}</{tag}>"


def wrap(ctx: Ctx, html: str) -> str:
    return f'<div class="site" dir="{ctx.dir}" lang="{ctx.lang}">{html}</div>'


def _mask(svg: str) -> str:
    svg = re.sub(r"\s+", " ", svg).strip()
    url = f'url("data:image/svg+xml,{quote(svg)}")'
    return f"-webkit-mask:{url} center/contain no-repeat;mask:{url} center/contain no-repeat"


_IG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.5'>"
       "<rect x='3' y='3' width='18' height='18' rx='5'/><circle cx='12' cy='12' r='4.2'/>"
       "<circle cx='17.4' cy='6.6' r='1' fill='black' stroke='none'/></svg>")
_WA = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.5' "
       "stroke-linejoin='round'><path d='M4.2 19.8l1.2-4A8.4 8.4 0 1 1 8.5 19l-4.3.8z'/>"
       "<path fill='black' stroke='none' d='M9.2 7.6c.3-.1.6 0 .7.3l.7 1.6c.1.3 0 .5-.2.7l-.5.5c.6 1.2 1.6 2.2 "
       "2.8 2.8l.5-.5c.2-.2.5-.3.7-.2l1.6.7c.3.1.4.4.3.7-.3 1-1.2 1.6-2.2 1.4-2.8-.6-5-2.8-5.6-5.6-.2-1 .4-1.9 "
       "1.2-2.4z'/></svg>")


@lru_cache(maxsize=1)
def icon_css() -> str:
    """st.html strips inline <svg>, so the logo and icons are CSS masks filled with currentColor."""
    logo = LOGO_SVG.read_text(encoding="utf-8")
    return f".logo{{{_mask(logo)}}}.ico-ig{{{_mask(_IG)}}}.ico-wa{{{_mask(_WA)}}}"


def logo() -> str:
    return '<span class="logo" role="img" aria-label="RIVATAR"></span>'


def whatsapp_url() -> str:
    return WHATSAPP_BASE + C.site().get("contact", {}).get("whatsapp", "")


# ------------------------------------------------------------------ media
@lru_cache(maxsize=1)
def media() -> dict:
    path = STATIC_DIR / "media.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"projects": {}, "home": {}, "videos": {}}


def photo_entry(slug: str, photo: str | None) -> dict | None:
    return media().get("projects", {}).get(slug, {}).get(photo or "")


def _srcset(folder: str, entry: dict) -> tuple[str, str]:
    urls = [(w, f"{STATIC_URL}/{folder}/{entry['base']}-{w}.jpg") for w in entry["sizes"]]
    return urls[-1][1] if len(urls) == 1 else urls[len(urls) // 2][1], ", ".join(f"{u} {w}w" for w, u in urls)


def img(folder: str, entry: dict | None, alt: str = "", sizes: str = "100vw", focus: str = "50% 50%",
        eager: bool = False) -> str:
    if not entry:
        return ""
    src, srcset = _srcset(folder, entry)
    return (f'<img src="{src}" srcset="{srcset}" sizes="{sizes}" alt="{escape(alt)}" width="{entry["w"]}" '
            f'height="{entry["h"]}" style="object-position:{escape(focus)}" '
            f'loading="{"eager" if eager else "lazy"}" decoding="async">')


def project_img(slug: str, item: dict | None, alt: str = "", sizes: str = "100vw", eager: bool = False) -> str:
    if not item:
        return ""
    return img(f"projects/{slug}", photo_entry(slug, item.get("photo")), alt, sizes, item.get("focus", "50% 50%"), eager)


def ref_img(ref: dict, alt: str = "", sizes: str = "50vw") -> str:
    """A {"project": slug, "photo": name} reference from site.json."""
    return project_img(ref.get("project", ""), {"photo": ref.get("photo")}, alt, sizes)


def figure(inner: str, cls: str = "") -> str:
    return f'<figure class="ph {cls}">{inner}</figure>'


# ------------------------------------------------------------------ chrome
def masthead(ctx: Ctx, current: str, solid: bool = False) -> str:
    links = "".join(
        f'<a href="{ctx.href(page_path(p))}" target="_self"{" aria-current=\"page\"" if p == current else ""}>'
        f'{escape(ctx.t("nav." + p))}</a>' for p in NAV)
    langs = []
    for code in C.LANGS:
        label = code.upper()
        if code == ctx.lang:
            langs.append(f'<span class="on" aria-current="true">{label}</span>')
        else:
            langs.append(f'<a href="{ctx.href(ctx.path, lang=code)}" target="_self" hreflang="{code}" '
                         f'lang="{code}">{label}</a>')
    lang_html = '<span class="sep" aria-hidden="true">|</span>'.join(langs)
    return f"""
<header class="mast{' solid' if solid else ''}">
  <a class="brand" href="{ctx.href('')}" target="_self" aria-label="RIVATAR">{logo()}</a>
  <nav class="main" aria-label="{escape(ctx.t('nav.menu'))}">{links}</nav>
  <div class="lang" aria-label="Language">{lang_html}</div>
  <details class="menu"><summary>{escape(ctx.t('nav.menu'))}</summary><nav>{links}</nav></details>
</header>"""


def tiles(ctx: Ctx) -> str:
    refs = C.site().get("tiles", {})
    out = []
    for key in ("about", "projects", "contact"):
        ref = refs.get(key, {})
        out.append(f'<a class="tile" href="{ctx.href(page_path(key))}" target="_self">'
                   f'{figure(ref_img(ref, sizes="(max-width:700px) 100vw, 34vw"))}'
                   f'<span>{escape(ctx.t("tiles." + key))}</span></a>')
    return f'<nav class="tiles" aria-label="{escape(ctx.t("nav.menu"))}">{"".join(out)}</nav>'


def _contact_item(value: str, href: str | None) -> str:
    if C.is_todo(value) or not href:
        return f"<li>{txt(value)}</li>"
    return f'<li><a href="{escape(href)}" target="_blank" rel="noopener">{escape(value)}</a></li>'


def footer(ctx: Ctx) -> str:
    info = C.site().get("contact", {})
    menu = "".join(f'<li><a href="{ctx.href(page_path(p))}" target="_self">{escape(ctx.t("nav." + p))}</a></li>'
                   for p in NAV)
    phone, email, insta = info.get("phone", ""), info.get("email", ""), info.get("instagram", "")
    contact = (_contact_item(phone, f"tel:{phone}") + _contact_item(email, f"mailto:{email}")
               + f'<li><a href="{whatsapp_url()}" target="_blank" rel="noopener">{escape(ctx.t("contact.whatsapp"))}</a></li>')
    infos = (f"<li>{txt(ctx.t('footer.privacy'))}</li><li>{txt(ctx.t('footer.terms'))}</li>"
             f'<li><a href="{ctx.href(page_path("lab"))}" target="_self">{escape(ctx.t("nav.lab"))}</a></li>')
    ig = (f'<a href="{escape(insta)}" target="_blank" rel="noopener" aria-label="Instagram"><span class="ico ico-ig"></span></a>'
          if insta and not C.is_todo(insta) else
          f'<span title="{escape(insta)}" aria-label="Instagram"><span class="ico ico-ig" style="opacity:.45"></span></span>')
    return f"""
<footer class="foot">
  <div class="foot-top">
    <div class="brand-col"><a class="brand" href="{ctx.href('')}" target="_self" aria-label="RIVATAR">{logo()}</a></div>
    <div class="foot-col"><h4>{escape(ctx.t('footer.menu'))}</h4><ul>{menu}</ul></div>
    <div class="foot-col"><h4>{escape(ctx.t('footer.contact'))}</h4><ul>{contact}</ul></div>
    <div class="foot-col"><h4>{escape(ctx.t('footer.info'))}</h4><ul>{infos}</ul></div>
  </div>
  <div class="foot-bottom">
    <div class="icons">{ig}<a href="{whatsapp_url()}" target="_blank" rel="noopener" aria-label="WhatsApp"><span class="ico ico-wa"></span></a></div>
    <small>{escape(ctx.t('footer.rights'))}</small>
  </div>
</footer>
<a class="wa-float" href="{whatsapp_url()}" target="_blank" rel="noopener" aria-label="{escape(ctx.t('contact.whatsapp_aria'))}"><span class="ico ico-wa"></span></a>"""


def page_end(ctx: Ctx) -> str:
    return tiles(ctx) + footer(ctx)


def intro(ctx: Ctx) -> str:
    """First-visit intro: logo + line typed letter by letter (CSS only), fades out by itself."""
    line = ctx.t("intro.line")
    step = 1.3 / max(len(line), 1)
    letters = "".join(f'<span style="animation-delay:{0.45 + i * step:.2f}s">{escape(ch)}</span>'
                      for i, ch in enumerate(line))
    return (f'<div class="intro" role="presentation" aria-hidden="true" title="{escape(ctx.t("intro.skip"))}">'
            f'{logo()}<p>{letters}</p></div>')


# ------------------------------------------------------------------ home
def _home_img(key: str, alt: str, sizes: str, eager: bool = False) -> str:
    cfg = C.site().get("home", {}).get(key, {})
    return img("home", media().get("home", {}).get(key), alt, sizes, cfg.get("focus", "50% 50%"), eager)


def xfade(ctx: Ctx, refs: list[dict], cls: str = "bw", sizes: str = "40vw") -> str:
    refs = [r for r in refs if photo_entry(r.get("project", ""), r.get("photo"))][:4]
    if not refs:
        return ""
    imgs = "".join(ref_img(r, sizes=sizes) for r in refs)
    n = len(refs) if len(refs) in (3, 4) else 0
    return f'<figure class="ph xfade {cls} n{n}" aria-label="{escape(ctx.t("home.crossfade_label"))}">{imgs}</figure>'


def home_top(ctx: Ctx) -> str:
    home = C.site().get("home", {})
    bride = (f'<span class="rot">{_home_img("bride-rot", ctx.t("home.bride_alt"), "(max-width:700px) 100vw, 40vw")}</span>'
             if home.get("bride", {}).get("rotate_desktop") else "")
    bride += f'<span class="upright">{_home_img("bride", ctx.t("home.bride_alt"), "100vw")}</span>'
    return f"""
<section class="home-split">
  <div class="home-left">
    {figure(_home_img("courtyard", ctx.t("home.courtyard_alt"), "(max-width:700px) 100vw, 50vw", eager=True), "bw")}
    <div class="home-copy">
      <h1>{escape(ctx.t("home.title"))}</h1>
      <p>{escape(ctx.t("home.text"))}</p>
      <a class="link-line" href="{ctx.href("projects")}" target="_self">{escape(ctx.t("home.cta"))}</a>
    </div>
  </div>
  <div class="home-right">
    {figure(_home_img("card", ctx.t("home.card_alt"), "(max-width:700px) 100vw, 40vw", eager=True), "home-card")}
    <figure class="ph home-bride bw">{bride}</figure>
    {xfade(ctx, home.get("crossfade", []))}
    <p class="xfade-cap label"><span>{escape(ctx.t("home.crossfade_label"))}</span><span>RIVATAR</span></p>
  </div>
</section>"""


# ------------------------------------------------------------------ covers
def cover(ctx: Ctx, proj: dict, eager: bool = False) -> str:
    slug = proj["slug"]
    name = ctx.loc(proj.get("name"))
    kind = C.event_type_label(proj.get("event_type"), ctx.lang)
    where = ctx.loc(proj.get("location"))
    image = project_img(slug, proj.get("cover"), alt=name, eager=eager,
                        sizes="(max-width:700px) 100vw, (max-width:1000px) 50vw, 33vw")
    return f"""
<a class="cover" href="{ctx.href(project_path(slug))}" target="_self" aria-label="{escape(name)}, {escape(kind)}, {escape(where)}">
  {figure(image)}
  <div class="meta"><span class="label">{escape(kind)}</span><h3>{escape(name)}</h3>{txt(where, "where")}</div>
</a>"""


def covers(ctx: Ctx, projects: list[dict]) -> str:
    return f'<div class="covers">{"".join(cover(ctx, p, eager=i < 3) for i, p in enumerate(projects))}</div>'


# ------------------------------------------------------------------ project page
def _gallery_rows(ctx: Ctx, slug: str, photos: list[dict]) -> str:
    rows, pending = [], []

    def flush_pair():
        if len(pending) == 2:
            rows.append('<div class="g-pair">' + "".join(
                figure(project_img(slug, p, ctx.loc(p.get("alt")), "(max-width:700px) 100vw, 50vw"), "zoom")
                for p in pending) + "</div>")
        elif pending:
            p = pending[0]
            rows.append(figure(project_img(slug, p, ctx.loc(p.get("alt")), "(max-width:700px) 100vw, 560px"), "g-detail zoom"))
        pending.clear()

    for p in photos:
        layout = p.get("layout", "wide")
        if layout == "pair":
            pending.append(p)
            if len(pending) == 2:
                flush_pair()
            continue
        flush_pair()
        if layout == "detail":
            rows.append(figure(project_img(slug, p, ctx.loc(p.get("alt")), "(max-width:700px) 100vw, 560px"), "g-detail zoom"))
        else:
            rows.append(figure(project_img(slug, p, ctx.loc(p.get("alt")), "100vw"), "g-wide zoom"))
    flush_pair()
    return "".join(rows)


def project_hero(ctx: Ctx, proj: dict) -> str:
    slug = proj["slug"]
    name = ctx.loc(proj.get("name"))
    kind = C.event_type_label(proj.get("event_type"), ctx.lang)
    where = ctx.loc(proj.get("location"))
    return f"""
<section class="p-hero">
  {figure(project_img(slug, proj.get("hero") or proj.get("cover"), name, "100vw", eager=True))}
  <div class="p-hero-copy">
    <span class="label">{escape(kind)} · {escape(where)}</span>
    <h1>{escape(name)}</h1>
    <a class="btn-line" href="#gallery">{escape(ctx.t("project.gallery"))}</a>
  </div>
</section>"""


def project_body(ctx: Ctx, proj: dict) -> str:
    slug = proj["slug"]
    facts = [("project.type", C.event_type_label(proj.get("event_type"), ctx.lang)),
             ("project.location", ctx.loc(proj.get("location")))]
    credits = [c for c in proj.get("credits", []) if c]
    facts_html = "".join(f'<div><dt class="label">{escape(ctx.t(k))}</dt>{txt(v, tag="dd")}</div>' for k, v in facts)
    intro = f"""
<section class="p-intro">
  {txt(ctx.loc(proj.get("text")) or ctx.t("todo"), "lead", "p")}
  <span class="rule"></span>
  <dl class="p-facts">{facts_html}</dl>
</section>"""
    chapters = []
    for ch in proj.get("chapters", []):
        title = ctx.loc(ch.get("title")) if ch.get("title") else ""
        head = f'<h2 class="chapter-title">{escape(title)}</h2>' if title else ""
        chapters.append(head + _gallery_rows(ctx, slug, ch.get("photos", [])))
    gallery = "".join(chapters) or f'<p class="pending">{txt(ctx.t("project.pending"))}</p>'
    films = ""
    vids = media().get("videos", {}).get(slug, [])
    if vids:
        items = "".join(
            f'<figure class="ph" style="--ar:{v["w"]}/{v["h"]}">'
            f'<video src="{STATIC_URL}/projects/{slug}/{v["file"]}" poster="{STATIC_URL}/projects/{slug}/{v["poster"]}" '
            f'autoplay muted loop playsinline preload="metadata" aria-hidden="true"></video>'
            f'<img class="still" src="{STATIC_URL}/projects/{slug}/{v["poster"]}" alt="" loading="lazy"></figure>'
            for v in vids)
        films = f'<section class="films"><h2>{escape(ctx.t("project.films"))}</h2><div class="films-row">{items}</div></section>'
    credit_html = ""
    if credits:
        credit_html = (f'<section class="p-intro"><span class="label">{escape(ctx.t("project.credits"))}</span>'
                       + "".join(txt(ctx.loc(c), tag="p") for c in credits) + "</section>")
    nxt = C.next_project(slug)
    next_html = ""
    if nxt:
        next_html = f"""
<section class="p-next">
  <a class="btn-line" href="{ctx.href(project_path(nxt["slug"]))}" target="_self">{escape(ctx.t("project.next"))}</a>
  <h2>{escape(ctx.loc(nxt.get("name")))}</h2>
</section>"""
    invite = f"""
<section class="p-invite">
  <h2>{escape(ctx.t("project.invite_title"))}</h2>
  <p>{escape(ctx.t("project.invite_text"))}</p>
  <a class="link-line" href="{ctx.href("contact")}" target="_self">{escape(ctx.t("project.invite_cta"))}</a>
</section>"""
    return (intro + f'<section class="gallery" id="gallery">{gallery}</section>' + films + credit_html
            + next_html + invite)


# ------------------------------------------------------------------ contact
def estimate_box(ctx: Ctx, case: str | None, result: dict | None) -> str:
    """Estimate panel. Shows the live estimate when the estimator returns one (phase 3)."""
    case_html = escape(case) if case else f'<span style="color:var(--fg-2)">{escape(ctx.t("estimate.case_empty"))}</span>'
    if result and result.get("status") == "ok":
        body = (f'<p class="est-num" dir="ltr" style="color:var(--fg)">₪{result["estimate_ils"]:,.0f}</p>'
                f'<p class="est-fine" dir="ltr">₪{result["low_ils"]:,.0f} – ₪{result["high_ils"]:,.0f}</p>')
        tag = ""
    else:
        body = (f'<p class="est-num" dir="ltr">₪ —</p>'
                f'<p class="est-pending">{escape(ctx.t("estimate.unavailable"))}</p>')
        tag = f'<span class="est-tag">{escape(ctx.t("estimate.tag"))}</span>'
    return f"""
<aside class="estimate" aria-label="{escape(ctx.t("estimate.label"))}">
  <div class="est-top"><span class="label">{escape(ctx.t("estimate.label"))}</span>{tag}</div>
  <p class="est-case">{case_html}</p>
  {body}
  <p class="est-fine">{escape(ctx.t("estimate.fine"))}</p>
</aside>"""


def errors_box(ctx: Ctx, messages: list[str]) -> str:
    items = "".join(f"<li>{escape(m)}</li>" for m in messages)
    return f'<div class="form-errors" role="alert">{escape(ctx.t("form.fix_errors"))}<ul>{items}</ul></div>'
