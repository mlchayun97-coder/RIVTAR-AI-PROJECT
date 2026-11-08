"""Site styling: the palette, typography and layout of rivatar-home.html, adapted to Streamlit.

Fonts are self-hosted in app/static/fonts (server.enableStaticServing), so the site works offline.
The design's scroll-in animation needs JavaScript (not allowed in st.html), so content simply rests
in place, which is the design's own reduced-motion behaviour.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
STATIC_URL = "/app/static"

_CSS = r"""
:root{
  /* Dark palette from the design draft (rivatar-home.html, dark mode) */
  --bg:#161513; --bg-2:#201E1B; --fg:#ECE5D9; --fg-2:#A69E91; --rule:#38342F;
  --on-photo:#F6F1E9; --todo:#C9A784; --err:#E08A7A;
  color-scheme:dark;
  --ph-sand:#B5A288; --ph-olive:#6D7162; --ph-rose:#94766B; --ph-dusk:#444B58; --ph-linen:#CBBDA8; --ph-wine:#5F3D3C;
  --f-display:"Frank Ruhl Libre","David",Georgia,serif;
  --f-latin:"Bodoni Moda","Didot","Bodoni 72",Georgia,serif;
  --f-body:"Assistant","Segoe UI",Arial,sans-serif;
  --gutter:clamp(16px,4.5vw,64px);
  --ease:cubic-bezier(.2,.7,.1,1);
}

/* ---------- Streamlit shell -> plain editorial page ---------- */
html,body,.stApp{background:var(--bg) !important;color:var(--fg)}
.stApp{direction:rtl;font-family:var(--f-body);-webkit-font-smoothing:antialiased}
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li{font-family:var(--f-body)}
header[data-testid="stHeader"]{background:transparent;height:0}
header[data-testid="stHeader"] [data-testid="stToolbar"]{top:.4rem}
[data-testid="stDecoration"]{display:none}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none}
[data-testid="stMainBlockContainer"],.block-container{max-width:none !important;padding:0 var(--gutter) 0 !important}
[data-testid="stVerticalBlock"]{gap:0}
[data-testid="stElementContainer"]:has(> .stHtml){width:100%}
.stHtml{width:100%}
.site{font-size:17px;line-height:1.7;font-weight:400}
.site a{color:inherit}
.site :focus-visible{outline:1.5px solid var(--fg);outline-offset:4px}
.site h1,.site h2,.site h3{font-family:var(--f-display);font-weight:300;line-height:1.08;margin:0;padding:0;text-wrap:balance;color:var(--fg);letter-spacing:0}
.site p{margin:0}
.lat{font-family:var(--f-latin);font-style:italic;font-weight:400;letter-spacing:.01em}
.label{font-size:.74rem;letter-spacing:.16em;text-transform:uppercase;font-weight:600;color:var(--fg-2)}
.todo{color:var(--todo) !important;border-bottom:1px dashed currentColor}

/* ---------- masthead ---------- */
.mast{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding-block:1rem;border-bottom:1px solid var(--rule)}
.mast nav{display:flex;gap:1.6rem;font-size:.92rem;align-items:center}
.mast nav a{text-decoration:none;position:relative}
.mast nav a::after{content:"";position:absolute;inset-inline:0;bottom:-3px;height:1px;background:currentColor;transform:scaleX(0);transform-origin:right;transition:transform .5s var(--ease)}
.mast nav a:hover::after{transform:scaleX(1)}
.mast nav a.lab{font-family:var(--f-latin);font-style:italic;color:var(--fg-2)}
.wordmark{display:grid;justify-items:center;gap:.45rem;text-decoration:none !important;color:var(--fg) !important;direction:ltr}
.wordmark .logo{width:clamp(110px,11vw,150px);height:auto;display:block}
.wordmark small{font-family:var(--f-body);font-size:.52rem;letter-spacing:.62em;font-weight:600;padding-inline-start:.62em;line-height:1}
.mast .cta{justify-self:end;font-size:.88rem;text-decoration:none;border:1px solid var(--fg);padding:.45rem 1.1rem;border-radius:999px;transition:background .3s,color .3s}
.mast .cta:hover{background:var(--fg);color:var(--bg)}
.menu{display:none;justify-self:start}
.menu summary{list-style:none;cursor:pointer;font-size:.9rem;padding:.4rem 0}
.menu summary::-webkit-details-marker{display:none}
.menu nav{display:flex;flex-direction:column;gap:1rem;padding-block:1.2rem .6rem;font-family:var(--f-display);font-size:1.6rem}
.menu nav a{text-decoration:none}

/* ---------- photos ---------- */
.ph{position:relative;margin:0;overflow:hidden;aspect-ratio:var(--ar,4/3);max-width:100%;background:var(--tone,var(--ph-sand))}
.ph img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;transition:transform 1.6s var(--ease)}
.ph:hover img{transform:scale(1.025)}
.ph-img{position:absolute;inset:0;background:radial-gradient(120% 80% at 30% 20%,rgb(255 255 255 / .22),transparent 60%),radial-gradient(90% 70% at 80% 90%,rgb(0 0 0 / .28),transparent 65%),var(--tone,var(--ph-sand))}
.ph-tag{position:absolute;inset-block-end:.8rem;inset-inline-start:.9rem;color:var(--on-photo);font-size:.68rem;letter-spacing:.18em;font-weight:600;text-transform:uppercase;opacity:.92;text-shadow:0 1px 8px rgb(0 0 0 / .45)}
.ph-tag::before{content:"";display:inline-block;width:1.4em;height:1px;background:currentColor;vertical-align:middle;margin-inline-end:.5em}
.sand{--tone:var(--ph-sand)} .olive{--tone:var(--ph-olive)} .rose{--tone:var(--ph-rose)} .dusk{--tone:var(--ph-dusk)} .linen{--tone:var(--ph-linen)} .wine{--tone:var(--ph-wine)}

/* ---------- hero ---------- */
.hero{padding-block:clamp(1.5rem,4vw,3rem) 0;display:grid;grid-template-columns:repeat(12,1fr);gap:clamp(16px,2.4vw,36px)}
.hero-main{grid-column:1/-1;--ar:16/8.5}
.hero-main::after{content:"";position:absolute;inset:0;background:linear-gradient(to top,rgb(0 0 0 / .38),transparent 45%);pointer-events:none}
.hero-word{position:absolute;inset-inline:6%;bottom:6%;color:var(--on-photo);pointer-events:none;z-index:1;animation:unveil 1.8s var(--ease) both}
.hero-word .logo{display:block;width:100%;height:auto}
@keyframes unveil{from{clip-path:inset(0 0 100% 0);transform:translateY(12%)}to{clip-path:inset(0);transform:none}}
.hero-main img{animation:breathe 2.4s var(--ease) both}
@keyframes breathe{from{transform:scale(1.06)}to{transform:scale(1.001)}}
.hero-main .ph-tag{inset-block-start:.9rem;inset-block-end:auto;z-index:1}
.hero-copy{grid-column:1/span 7;padding-block:clamp(1.5rem,3vw,2.5rem)}
.hero-copy h1{font-size:clamp(2rem,4.6vw,4.2rem) !important;max-width:15ch}
.hero-copy .lede{margin-top:1.4rem;max-width:44ch;color:var(--fg-2);font-size:1.08rem}
.hero-side{grid-column:9/-1;margin-top:clamp(-9rem,-9vw,-3rem);display:grid;gap:.9rem;align-content:start;z-index:2}
.hero-side .ph{--ar:4/5;width:78%;justify-self:end;box-shadow:0 0 0 clamp(8px,1vw,14px) var(--bg)}
.hero-side .cap{font-size:.82rem;color:var(--fg-2);max-width:28ch;justify-self:end;text-align:end}
.disciplines{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:.4rem 2.2rem;align-items:baseline;border-top:1px solid var(--rule);padding-block:1rem;font-family:var(--f-display);font-size:clamp(1.05rem,1.6vw,1.3rem)}
.disciplines .lat{font-size:.95em;color:var(--fg-2);margin-inline-start:auto}

/* ---------- sections ---------- */
.sec{padding-block:clamp(4.5rem,10vw,9rem) 0;scroll-margin-top:1rem}
.sec-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:.5rem 1.4rem;margin-bottom:clamp(2.5rem,6vw,5rem)}
.sec-head h2{font-size:clamp(2.4rem,6vw,5.4rem) !important}
.sec-head .lat{font-size:clamp(1.1rem,1.8vw,1.5rem);color:var(--fg-2)}
.sec-head .note{margin-inline-start:auto;max-width:34ch;color:var(--fg-2);font-size:.95rem}

/* ---------- stories ---------- */
.stories{display:grid;gap:clamp(5rem,12vw,11rem)}
.story{display:grid;grid-template-columns:repeat(12,1fr);gap:clamp(16px,2.4vw,36px);align-items:start}
.story-text{display:grid;gap:.9rem;align-content:start;min-width:0}
.story-text .kicker{display:flex;gap:.7rem;flex-wrap:wrap}
.story-text h3{font-size:clamp(1.9rem,3.4vw,3.1rem) !important}
.story-text h3.lat{font-family:var(--f-latin);font-style:italic;font-weight:400}
.story-text .desc{color:var(--fg-2);max-width:40ch}
.more{justify-self:start;display:inline-flex;gap:.6rem;align-items:center;text-decoration:none;font-weight:600;font-size:.92rem;margin-top:.4rem;padding-bottom:.2rem;border-bottom:1px solid var(--fg)}
.more span{transition:transform .5s var(--ease)}
.more:hover span{transform:translateX(-6px)}
.gal-count{font-size:.8rem;color:var(--fg-2)}
.s-a .wide{grid-column:1/span 8;--ar:4/3}
.s-a .side{grid-column:9/-1;display:grid;gap:clamp(1.5rem,3vw,2.5rem);padding-top:clamp(2rem,10vw,9rem)}
.s-a .side .ph{--ar:3/4;width:72%}
.s-b .story-text{grid-column:1/span 4;padding-top:clamp(1rem,6vw,6rem)}
.s-b .tall{grid-column:5/span 5;--ar:4/5.4}
.s-b .low{grid-column:10/-1;--ar:1/1;margin-top:clamp(6rem,24vw,22rem)}
.s-c .pano{grid-column:1/-1;--ar:21/8}
.s-c .story-text{grid-column:1/span 5}
.s-c .strip{grid-column:7/-1;display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:clamp(10px,1.4vw,18px);align-items:end;margin-top:clamp(-6rem,-7vw,-2rem)}
.s-c .strip .ph:nth-child(1){--ar:4/5}
.s-c .strip .ph:nth-child(2){--ar:1/1}
.s-c .strip .ph:nth-child(3){--ar:3/4.4}
.s-c .strip .ph{box-shadow:0 0 0 clamp(6px,.8vw,12px) var(--bg)}

/* ---------- approach ---------- */
.approach{display:grid;grid-template-columns:repeat(12,1fr);gap:clamp(16px,2.4vw,36px)}
.approach .statement{grid-column:1/span 10;font-family:var(--f-display);font-weight:300;font-size:clamp(1.9rem,4.4vw,3.9rem);line-height:1.2;text-wrap:balance}
.approach .statement em{font-style:normal;color:var(--fg-2)}
.pillars{grid-column:1/-1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:clamp(2rem,5vw,5rem);margin-top:clamp(2.5rem,5vw,4.5rem);border-top:1px solid var(--rule);padding-top:2rem}
.pillar{display:grid;gap:.7rem;align-content:start}
.pillar h3{font-size:clamp(1.5rem,2.4vw,2rem) !important}
.pillar p{color:var(--fg-2);max-width:46ch}
.pillar .lat{color:var(--fg-2);font-size:1.05rem}

/* ---------- services ---------- */
.svc-list{list-style:none;margin:0;padding:0;border-top:1px solid var(--fg)}
.svc{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr) auto;gap:1rem 2.5rem;align-items:center;padding-block:clamp(1.4rem,3vw,2.4rem);border-bottom:1px solid var(--rule);position:relative;margin:0}
.svc h3{font-size:clamp(2rem,5vw,4.4rem) !important;transition:transform .7s var(--ease)}
.svc h3 .lat{display:block;font-size:.3em;color:var(--fg-2);margin-top:.5rem}
.svc p{color:var(--fg-2);max-width:40ch}
.svc .swatch{width:clamp(70px,9vw,130px);aspect-ratio:3/4;background:var(--tone);opacity:0;transform:translateY(10px) rotate(-2deg);transition:opacity .6s var(--ease),transform .7s var(--ease)}
.svc:hover h3{transform:translateX(-14px)}
.svc:hover .swatch{opacity:1;transform:none}
.addons{display:flex;flex-wrap:wrap;gap:.4rem 1.6rem;align-items:baseline;margin-top:1.6rem;color:var(--fg-2)}
.addons .label{margin-inline-end:.6rem}

/* ---------- about ---------- */
.about{display:grid;grid-template-columns:repeat(12,1fr);gap:clamp(16px,2.4vw,36px);align-items:end}
.about .portrait{grid-column:1/span 5;--ar:3/4}
.about .bio{grid-column:7/-1;display:grid;gap:1.2rem;padding-bottom:clamp(0rem,3vw,3rem);min-width:0}
.about .name{font-size:clamp(4rem,12vw,10rem) !important;line-height:.9 !important}
.about .bio p{color:var(--fg-2);max-width:48ch}

/* ---------- contact (native Streamlit widgets inside a keyed container) ---------- */
.st-key-contact{background:var(--bg-2);margin-top:clamp(4.5rem,10vw,9rem);margin-inline:calc(var(--gutter) * -1) !important;padding:clamp(3rem,8vw,7rem) var(--gutter) !important;width:calc(100% + 2 * var(--gutter)) !important;max-width:none !important;scroll-margin-top:1rem}
.contact-head{display:grid;gap:1.4rem;align-content:start}
.contact-head h2{font-size:clamp(2.2rem,5vw,4.4rem) !important}
.contact-head dl{display:grid;grid-template-columns:auto 1fr;gap:.5rem 1.4rem;margin:1rem 0 0;font-size:.95rem}
.contact-head dt{color:var(--fg-2)}
.contact-head dd{margin:0}
.legend{font-family:var(--f-display);font-size:1.35rem;margin:1.6rem 0 .4rem;color:var(--fg)}
.legend.first{margin-top:0}
.st-key-contact [data-testid="stWidgetLabel"] p{font-size:.8rem;color:var(--fg-2);letter-spacing:.04em}
/* underline-only fields, as in the design */
.st-key-contact [data-testid="stTextInputRootElement"],.st-key-contact [data-testid="stNumberInputContainer"],
.st-key-contact [data-testid="stDateInputField"],.st-key-contact [data-baseweb="input"],.st-key-contact [data-baseweb="select"]>div,
.st-key-contact [data-baseweb="textarea"],.st-key-contact [data-testid="stTextAreaRootElement"]{background:transparent !important;border:0 !important;border-bottom:1px solid var(--fg-2) !important;border-radius:0 !important;box-shadow:none !important}
.st-key-contact [data-baseweb="base-input"],.st-key-contact [data-baseweb="input"] [data-baseweb="input"]{background:transparent !important;border:0 !important}
.st-key-contact [data-testid="stTextInputRootElement"]:focus-within,.st-key-contact [data-testid="stNumberInputContainer"]:focus-within,
.st-key-contact [data-baseweb="select"]>div:focus-within,.st-key-contact [data-baseweb="textarea"]:focus-within,.st-key-contact [data-baseweb="input"]:focus-within{border-bottom-color:var(--fg) !important}
.st-key-contact input,.st-key-contact textarea{background:transparent !important;font-size:1rem !important;padding-inline:0 !important}
.st-key-contact [data-testid="stForm"]{border:0;padding:0}
.st-key-contact [data-testid="stFormSubmitButton"] button{font-weight:600;background:var(--fg);color:var(--bg);border:0;border-radius:999px;padding:.85rem 2rem;transition:transform .3s var(--ease)}
.st-key-contact [data-testid="stFormSubmitButton"] button:hover{transform:translateY(-2px);color:var(--bg)}
.st-key-contact [data-testid="stFormSubmitButton"] button p{font-size:1rem}
.st-key-contact [data-testid="stButtonGroup"] button{border-radius:999px;border:1px solid var(--fg-2);background:transparent}
.st-key-contact [data-testid="stButtonGroup"] button[kind$="Active"]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.st-key-contact [data-testid="stElementContainer"]{margin-bottom:.9rem}
.form-errors{border-inline-start:2px solid var(--err);padding:.6rem 1rem;margin:.6rem 0;color:var(--err);font-size:.92rem}
.form-errors ul{margin:.3rem 0 0;padding-inline-start:1.2rem}
.form-ok{border-inline-start:2px solid var(--fg);padding:.6rem 1rem;margin:.6rem 0;font-size:.95rem}
.estimate{background:var(--bg);padding:clamp(1.4rem,3vw,2.4rem);display:grid;gap:.6rem;margin-top:1.2rem}
.est-top{display:flex;justify-content:space-between;align-items:center;gap:1rem}
.est-tag{font-size:.72rem;border:1px solid var(--todo);color:var(--todo);border-radius:999px;padding:.1rem .7rem}
.est-case{font-family:var(--f-display);font-size:1.15rem}
.est-num{font-family:var(--f-latin);font-size:clamp(2.8rem,6vw,4.6rem);line-height:1;text-align:right;font-variant-numeric:lining-nums tabular-nums;margin-block:.3rem .8rem;color:var(--fg-2)}
.est-pending{font-family:var(--f-display);font-size:clamp(1.3rem,2.4vw,1.8rem);line-height:1.3}
.est-pending .lat{display:block;font-size:.75em;color:var(--fg-2);margin-top:.2rem}
.est-track{position:relative;height:1px;background:var(--rule);margin-top:.6rem}
.est-track::before,.est-track::after{content:"";position:absolute;top:-5px;width:1px;height:11px;background:var(--rule)}
.est-track::before{left:0}.est-track::after{right:0}
.est-fine{font-size:.85rem;color:var(--fg-2);max-width:52ch;margin-top:.4rem}

/* ---------- footer ---------- */
.foot{padding-block:clamp(3rem,7vw,6rem) 2rem;display:grid;gap:1.5rem}
.foot-word{color:var(--fg);padding-inline:2%}
.foot-word .logo{display:block;width:100%;height:auto}
.foot-row{display:flex;flex-wrap:wrap;justify-content:space-between;gap:1rem;font-size:.85rem;color:var(--fg-2);border-top:1px solid var(--rule);padding-top:1.2rem}
.foot-row nav{display:flex;gap:1.4rem;flex-wrap:wrap}
.foot-row a{text-decoration:none}

/* ---------- gallery pages ---------- */
.gal-head{padding-block:clamp(2rem,5vw,4rem) clamp(1.5rem,4vw,3rem);display:grid;gap:.9rem}
.gal-head h1{font-family:var(--f-latin) !important;font-style:italic;font-weight:400 !important;font-size:clamp(2.6rem,7vw,6rem) !important}
.gal-head .desc{color:var(--fg-2);max-width:52ch}
.gal-head .back{justify-self:start;text-decoration:none;font-size:.9rem;border-bottom:1px solid var(--fg);font-weight:600}
.gallery{columns:3 280px;column-gap:clamp(10px,1.6vw,22px)}
.gallery a{display:block;margin-bottom:clamp(10px,1.6vw,22px);break-inside:avoid;overflow:hidden;background:var(--bg-2)}
.gallery img{display:block;width:100%;height:auto;transition:transform 1.2s var(--ease)}
.gallery a:hover img{transform:scale(1.03)}
.gal-hint{font-size:.82rem;color:var(--fg-2);margin-top:1rem}
.gal-others{display:flex;flex-wrap:wrap;gap:.6rem 1.6rem;border-top:1px solid var(--rule);padding-top:1.2rem;margin-top:clamp(3rem,6vw,5rem)}
.gal-others a{text-decoration:none;font-family:var(--f-latin);font-style:italic;font-size:1.15rem}
.gal-others a[aria-current]{border-bottom:1px solid var(--fg)}

/* ---------- ML LAB ---------- */
.lab-stages{list-style:none;margin:0 !important;padding:0 !important;border-top:1px solid var(--fg)}
.lab-stages li,.svc-list li{margin:0 !important;padding-inline:0 !important}
.lab-stage{display:grid;grid-template-columns:2.2rem minmax(0,1.1fr) minmax(0,1.6fr) auto;gap:1rem 1.6rem;align-items:baseline;padding-block:1.2rem;border-bottom:1px solid var(--rule)}
.lab-stage .n{font-family:var(--f-latin);font-style:italic;color:var(--fg-2)}
.lab-stage .t{font-family:var(--f-latin);font-size:1.3rem;direction:ltr;text-align:right}
.lab-stage .d{color:var(--fg-2)}
.pill{font-size:.72rem;border:1px solid var(--fg-2);color:var(--fg-2);border-radius:999px;padding:.1rem .7rem;white-space:nowrap}
.pill.ok{border-color:var(--fg);background:var(--fg);color:var(--bg)}
.lab-note{margin-top:1.4rem;color:var(--todo);font-size:.92rem}

/* ---------- tablet ---------- */
@media (max-width:980px){
  .mast > nav{display:none}
  .menu{display:block}
  .menu[open]{grid-column:1/-1;grid-row:2}
  .mast:has(.menu[open]){grid-template-rows:auto auto}
  .hero-copy{grid-column:1/-1}
  .hero-side{grid-column:1/-1;margin-top:0;grid-template-columns:1fr 1fr;align-items:end}
  .hero-side .ph{width:100%}
  .hero-side .cap{justify-self:start;text-align:start}
}
/* ---------- phone ---------- */
@media (max-width:720px){
  .site{font-size:16px}
  .wordmark .logo{width:96px}
  .mast .cta{padding:.35rem .9rem;font-size:.8rem}
  .hero-main{--ar:4/5}
  .hero-word{inset-inline:7%;bottom:5%}
  .story,.approach,.about{grid-template-columns:1fr}
  .story>*,.approach>*,.about>*{grid-column:1/-1 !important}
  .s-a .side{padding-top:0}
  .s-a .side .ph{width:62%;justify-self:end;margin-top:-4.5rem;box-shadow:0 0 0 10px var(--bg)}
  .s-b .story-text{padding-top:0;order:3}
  .s-b .tall{width:86%}
  .s-b .low{width:52%;justify-self:end;margin-top:-6rem;box-shadow:0 0 0 10px var(--bg)}
  .s-c .pano{--ar:4/3}
  .s-c .strip{margin-top:0}
  .pillars{grid-template-columns:1fr}
  .svc{grid-template-columns:1fr}
  .svc .swatch{display:none}
  .about .portrait{width:82%}
  .lab-stage{grid-template-columns:2rem 1fr}
  .lab-stage .d,.lab-stage .pill{grid-column:2}
  .lab-stage .t{text-align:start}
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none !important;transition:none !important}
}
"""


@st.cache_data
def _fonts_css() -> str:
    return (APP_DIR / "static" / "fonts" / "fonts.css").read_text(encoding="utf-8")


def inject() -> None:
    """Inject fonts and site CSS. Call once per page run, before any content."""
    from ui import logo_mask_css  # local import: ui imports theme

    st.html(f"<style>{_fonts_css()}\n{_CSS}\n{logo_mask_css()}</style>")
