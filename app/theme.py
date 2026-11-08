"""Site styling: black, white and ivory; Bellefair titles, Jost (EN) / Heebo (HE) for labels and text.

Fonts are self-hosted in app/static/fonts (server.enableStaticServing), so the site works offline.
Motion is CSS only and always ends in the visible state; prefers-reduced-motion switches it off.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
STATIC_URL = "/app/static"

_CSS = r"""
:root{
  --bg:#000; --fg:#EDE8E0; --fg-2:#A9A39A; --accent:#CFC3AE; --rule:rgb(237 232 224 / .18);
  --paper:#F4F0E8; --ink:#141312; --ink-2:#5E5A54; --todo:#CFA77A; --err:#E8907E;
  --f-title:"Bellefair","Times New Roman",serif;
  --f-label:"Jost","Heebo","Segoe UI",Arial,sans-serif;
  --f-body:"Jost","Heebo","Segoe UI",Arial,sans-serif;
  --track:.16em;
  --gutter:clamp(16px,4vw,64px);
  --ease:cubic-bezier(.22,.61,.24,1);
  color-scheme:dark;
}
:root:has(.site[lang="he"]){--f-label:"Heebo","Segoe UI",Arial,sans-serif;--f-body:"Heebo","Segoe UI",Arial,sans-serif;--track:0}

/* ---------- Streamlit shell -> plain page ---------- */
html,body,.stApp{background:var(--bg) !important;color:var(--fg)}
.stApp{font-family:var(--f-body);-webkit-font-smoothing:antialiased}
.stApp p,.stApp label,.stApp input,.stApp textarea,.stApp button,.stApp li{font-family:var(--f-body)}
header[data-testid="stHeader"]{display:none}
[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none !important}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none}
[data-testid="stMainBlockContainer"],.block-container{max-width:none !important;padding:0 !important}
[data-testid="stVerticalBlock"]{gap:0 !important}
[data-testid="stElementContainer"]:has(> .stHtml){width:100%}
.stHtml{width:100%}
.stApp:has(.site[dir="rtl"]){direction:rtl}

.site{font-size:16px;line-height:1.7;font-weight:300;color:var(--fg);position:relative}
.site a{color:inherit;text-decoration:none}
.site :focus-visible{outline:1px solid var(--fg);outline-offset:4px}
.site h1,.site h2,.site h3{font-family:var(--f-title);font-weight:400;line-height:1.08;margin:0;padding:0;color:inherit;letter-spacing:.02em}
.site[lang="he"] h1,.site[lang="he"] h2,.site[lang="he"] h3{letter-spacing:0}
.site p{margin:0}
.label{font-family:var(--f-label);font-size:.74rem;letter-spacing:var(--track);text-transform:uppercase;font-weight:400}
.todo{color:var(--todo) !important;border-bottom:1px dashed currentColor}
.rule{display:block;width:56px;height:1px;background:var(--fg);opacity:.6;margin-inline:auto}
.btn-line{display:inline-block;font-family:var(--f-label);font-size:.78rem;letter-spacing:var(--track);text-transform:uppercase;border:1px solid currentColor;padding:.85em 2.2em;transition:background .4s var(--ease),color .4s var(--ease)}
.btn-line:hover{background:var(--fg);color:var(--bg)}
.link-line{font-family:var(--f-label);font-size:.8rem;letter-spacing:var(--track);text-transform:uppercase;padding-bottom:.35em;border-bottom:1px solid currentColor}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

/* ---------- logo (CSS mask: st.html strips inline SVG) ---------- */
.logo{display:block;aspect-ratio:331/60;background:currentColor}

/* ---------- header ---------- */
.mast{position:absolute;inset-inline:0;top:0;z-index:30;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:2rem;padding:clamp(18px,2.6vw,38px) var(--gutter)}
.mast .brand{color:var(--fg);width:clamp(118px,11vw,170px)}
.mast nav.main{display:flex;justify-content:center;gap:clamp(1.4rem,3.6vw,4rem)}
.mast nav.main a,.lang a,.lang span{font-family:var(--f-label);font-size:.8rem;letter-spacing:var(--track);text-transform:uppercase;padding-bottom:.3em;border-bottom:1px solid transparent;transition:border-color .3s}
.mast nav.main a:hover,.mast nav.main a[aria-current="page"]{border-bottom-color:currentColor}
.lang{display:flex;align-items:center;gap:.6rem;direction:ltr}
.lang .on{border-bottom-color:currentColor}
.lang .sep{opacity:.5;border:0 !important}
.menu{display:none}
.mast.solid{position:relative;background:var(--bg);border-bottom:1px solid var(--rule)}

/* ---------- photos ---------- */
.ph{position:relative;margin:0;overflow:hidden;background:#111}
.ph img,.ph video{display:block;width:100%;height:100%;object-fit:cover}
.bw img,.bw video{filter:grayscale(1) contrast(1.04)}
.zoom img{transition:transform 1.8s var(--ease)}
.zoom:hover img{transform:scale(1.035)}

/* ---------- intro (first visit only; the server leaves it out once the cookie is set) ---------- */
.intro{position:fixed;inset:0;z-index:1000;background:var(--paper);color:var(--ink);display:grid;place-content:center;justify-items:center;gap:2.2rem;cursor:pointer;animation:intro-out .8s var(--ease) 2.1s forwards}
.intro .logo{width:clamp(130px,14vw,190px);color:var(--ink);opacity:0;animation:fade-in .6s ease .1s forwards}
.intro p{font-family:var(--f-title);font-size:clamp(1.1rem,2vw,1.5rem);letter-spacing:.14em;text-transform:uppercase;min-height:1.4em}
.intro p span{opacity:0;animation:fade-in .01s linear forwards}
.intro.skip{animation:intro-out .35s ease forwards}
@keyframes intro-out{to{opacity:0;visibility:hidden}}
@keyframes fade-in{to{opacity:1}}
.st-key-introjs{position:absolute !important;width:0 !important;height:0 !important;overflow:hidden}

/* ---------- home ---------- */
.home-split{display:grid;grid-template-columns:1fr 1fr;min-height:100vh}
.home-left{position:sticky;top:0;height:100vh;overflow:hidden}
.home-left .ph{position:absolute;inset:0}
.home-left .ph::after{content:"";position:absolute;inset:0;background:linear-gradient(to top,rgb(0 0 0 / .62),rgb(0 0 0 / .08) 55%,rgb(0 0 0 / .25))}
.home-copy{position:absolute;inset-inline:clamp(24px,6vw,96px);bottom:clamp(48px,12vh,120px);z-index:2;max-width:34rem}
.home-copy h1{font-size:clamp(2.6rem,5vw,4.6rem);line-height:1.04;animation:rise-in 1.4s var(--ease) both}
.home-copy p{margin-top:1.4rem;font-size:1.02rem;max-width:30rem;color:var(--fg);animation:rise-in 1.4s var(--ease) .15s both}
.home-copy .link-line{display:inline-block;margin-top:2rem;animation:rise-in 1.4s var(--ease) .3s both}
.home-right{display:flex;flex-direction:column;align-items:center;gap:clamp(14px,1.6vw,22px);padding:clamp(120px,24vh,260px) clamp(24px,7vw,120px) clamp(60px,12vh,140px)}
.home-right figure{width:100%;max-width:600px}
.home-card{aspect-ratio:565/340}
.home-bride{aspect-ratio:565/255}
.home-bride .upright{display:none}
.xfade{position:relative;aspect-ratio:4/5;width:78% !important;margin-top:clamp(40px,10vh,120px) !important}
.xfade img{position:absolute;inset:0;opacity:0}
.xfade img:first-child{opacity:1}
.xfade.n3 img{animation:xf3 12s infinite} .xfade.n4 img{animation:xf4 16s infinite}
.xfade img:nth-child(2){animation-delay:4s} .xfade img:nth-child(3){animation-delay:8s} .xfade img:nth-child(4){animation-delay:12s}
@keyframes xf3{0%{opacity:0}8%{opacity:1}33%{opacity:1}41%{opacity:0}100%{opacity:0}}
@keyframes xf4{0%{opacity:0}6%{opacity:1}25%{opacity:1}31%{opacity:0}100%{opacity:0}}
.xfade-cap{width:78%;max-width:600px;display:flex;justify-content:space-between;color:var(--fg-2)}
@keyframes rise-in{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}

/* ---------- section heads ---------- */
.sec{padding:clamp(80px,12vw,160px) var(--gutter) 0}
.sec-head{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:1rem 2rem;margin-bottom:clamp(32px,5vw,64px);border-bottom:1px solid var(--rule);padding-bottom:1.2rem}
.sec-head h2{font-size:clamp(1.8rem,3.4vw,3rem);text-transform:uppercase}
.page-head{padding:clamp(130px,18vh,200px) var(--gutter) clamp(40px,6vw,80px)}
.page-head h1{font-size:clamp(2.4rem,5.4vw,5rem);text-transform:uppercase}
.page-head p{margin-top:1.4rem;max-width:40rem;color:var(--fg-2);font-size:1.05rem}

/* ---------- project covers ---------- */
.covers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:clamp(10px,1.2vw,18px);padding:0 var(--gutter)}
.cover{position:relative;display:block;aspect-ratio:9/16;border-radius:10px;overflow:hidden;background:#111;isolation:isolate}
.cover .ph{position:absolute;inset:0;animation:load-sharp 1.4s var(--ease) both}
.cover img{transition:filter .7s var(--ease),transform 1.6s var(--ease)}
.cover .meta{position:absolute;inset:auto 0 0 0;z-index:2;padding:clamp(18px,2vw,28px);display:grid;gap:.35rem;opacity:0;transform:translateY(8px);transition:opacity .6s var(--ease),transform .6s var(--ease)}
.cover .meta h3{font-size:clamp(1.5rem,2.2vw,2.1rem)}
.cover .meta .label{color:var(--fg)}
.cover .meta .where{font-size:.92rem;color:var(--fg)}
.cover:hover img,.cover:focus-visible img{filter:blur(6px) brightness(.5);transform:scale(1.03)}
.cover:hover .meta,.cover:focus-visible .meta{opacity:1;transform:none}
.cover:focus-visible{outline:1px solid var(--fg);outline-offset:4px}
@keyframes load-sharp{from{filter:blur(14px);opacity:.3}to{filter:none;opacity:1}}
@media (hover:none){
  .cover .meta{opacity:1;transform:none;padding-top:5rem;background:linear-gradient(to top,rgb(0 0 0 / .82),rgb(0 0 0 / .45) 60%,transparent)}
}
.covers-foot{display:flex;justify-content:center;padding:clamp(40px,5vw,64px) var(--gutter) 0}

/* ---------- project page ---------- */
.p-hero{position:relative;height:100vh;min-height:520px;overflow:hidden}
.p-hero .ph{position:absolute;inset:0}
.p-hero .ph::after{content:"";position:absolute;inset:0;background:rgb(0 0 0 / .45)}
.p-hero-copy{position:absolute;inset:0;z-index:2;display:grid;place-content:center;justify-items:center;text-align:center;gap:1.1rem;padding:0 var(--gutter)}
.p-hero-copy h1{font-size:clamp(2.6rem,6vw,5.6rem);animation:rise-in 1.4s var(--ease) both}
.p-hero-copy .label{animation:rise-in 1.4s var(--ease) .15s both}
.p-hero-copy .btn-line{margin-top:1.4rem;animation:rise-in 1.4s var(--ease) .3s both}
.p-intro{max-width:44rem;margin:0 auto;padding:clamp(80px,10vw,140px) var(--gutter) 0;text-align:center;display:grid;gap:1.8rem}
.p-intro .lead{font-size:clamp(1.05rem,1.4vw,1.2rem);line-height:1.85}
.p-facts{display:flex;justify-content:center;flex-wrap:wrap;gap:1rem 3.5rem;border-block:1px solid var(--rule);padding:1.3rem 0;margin-top:.6rem}
.p-facts div{display:grid;gap:.25rem}
.p-facts dt{color:var(--fg-2)} .p-facts dd{margin:0;font-family:var(--f-title);font-size:1.2rem}
.palette{display:grid;justify-items:center;gap:1.6rem;padding:clamp(80px,10vw,140px) var(--gutter) 0}
.palette-row{display:grid;grid-template-columns:1fr 1fr;gap:clamp(8px,1vw,14px);width:min(560px,100%);aspect-ratio:2/1.25}
.swatches{display:grid;grid-template-rows:repeat(4,1fr);outline:1px solid var(--rule);outline-offset:-1px}
.palette .ph{height:100%}
.palette + .gallery{padding-top:clamp(36px,4.5vw,64px)}
.palette + .gallery > .chapter-title:first-child{padding-top:0}
.gallery{display:grid;gap:clamp(10px,1.2vw,18px);padding:clamp(80px,10vw,140px) var(--gutter) 0;max-width:1500px;margin:0 auto;scroll-margin-top:24px}
.chapter-title{text-align:center;font-size:clamp(1.4rem,2.4vw,2rem);text-transform:uppercase;padding:clamp(40px,6vw,80px) 0 clamp(10px,2vw,24px)}
.g-wide{aspect-ratio:3/2}
.g-pair{display:grid;grid-template-columns:1fr 1fr;gap:clamp(10px,1.2vw,18px)}
.g-pair .ph{aspect-ratio:4/5}
.g-detail{width:min(560px,70%);aspect-ratio:4/5;justify-self:center;margin-block:clamp(30px,5vw,70px)}
.films{padding:clamp(80px,10vw,140px) 0 0}
.films h2{text-align:center;font-size:clamp(1.3rem,2vw,1.7rem);text-transform:uppercase;margin-bottom:clamp(24px,3vw,40px)}
.films-row{display:flex;gap:clamp(10px,1.2vw,18px);overflow-x:auto;padding:0 var(--gutter) 12px;scroll-snap-type:x mandatory;scrollbar-width:thin;scrollbar-color:var(--rule) transparent}
.films-row .ph{flex:0 0 auto;height:clamp(320px,52vh,560px);aspect-ratio:var(--ar,9/16);scroll-snap-align:start}
.films-row .still{display:none}
.p-next{display:grid;justify-items:center;gap:1.4rem;text-align:center;padding:clamp(90px,12vw,170px) var(--gutter) 0}
.p-next h2{font-size:clamp(2rem,4vw,3.4rem)}
.p-invite{max-width:40rem;margin:0 auto;text-align:center;display:grid;gap:1.2rem;justify-items:center;padding:clamp(90px,12vw,170px) var(--gutter) 0}
.p-invite h2{font-size:clamp(1.6rem,3vw,2.4rem)}
.p-invite p{color:var(--fg-2)}
.pending{text-align:center;padding:4rem 0}

/* ---------- contact band (bottom of every page) ---------- */
.cta-band{position:relative;margin-top:clamp(100px,12vw,180px);height:clamp(380px,62vh,640px);overflow:hidden;color:#fff}
.cta-band .ph{position:absolute;inset:0}
.cta-band .ph::after{content:"";position:absolute;inset:0;background:rgb(0 0 0 / .42)}
.cta-copy{position:absolute;inset:0;z-index:2;display:grid;place-content:center;justify-items:center;gap:2rem;text-align:center;padding:0 var(--gutter)}
.cta-copy h2{font-size:clamp(2rem,4.4vw,3.8rem);max-width:18ch}
.cta-copy .btn-line{color:#fff}
.cta-copy .btn-line:hover{background:#fff;color:#111}

/* ---------- footer ---------- */
.foot{padding:clamp(80px,10vw,140px) var(--gutter) clamp(28px,3vw,40px);display:grid;gap:clamp(60px,8vw,120px)}
.foot-top{display:grid;grid-template-columns:1.6fr repeat(3,1fr);gap:2rem}
.foot-top .brand{width:clamp(110px,10vw,150px)}
.foot-col h4{font-family:var(--f-title);font-weight:400;font-size:1.25rem;text-transform:uppercase;margin:0 0 1rem;letter-spacing:.04em}
.foot-col ul{list-style:none;margin:0;padding:0;display:grid;gap:.45rem}
.foot-col li{margin:0}
.foot-col a,.foot-col span{font-family:var(--f-label);font-size:.78rem;letter-spacing:var(--track);text-transform:uppercase}
.foot-col a:hover{border-bottom:1px solid currentColor}
.foot-bottom{display:flex;justify-content:space-between;align-items:center;gap:1rem;border-top:1px solid var(--rule);padding-top:1.4rem}
.foot-bottom .icons{display:flex;gap:1rem}
.foot-bottom small{font-family:var(--f-title);font-size:1rem;letter-spacing:.06em}
.ico{display:inline-block;width:22px;height:22px;background:currentColor}

/* ---------- floating WhatsApp ---------- */
.wa-float{position:fixed;inset-inline-start:clamp(14px,2vw,28px);bottom:clamp(14px,2vw,28px);z-index:50;width:52px;height:52px;border-radius:50%;background:var(--paper);color:var(--ink) !important;display:grid;place-items:center;box-shadow:0 6px 24px rgb(0 0 0 / .35);transition:transform .3s var(--ease)}
.wa-float:hover{transform:scale(1.06)}
.wa-float .ico{width:26px;height:26px}

/* ---------- services ---------- */
.acc{padding:0 var(--gutter);max-width:1300px}
.acc details{border-bottom:1px solid var(--rule)}
.acc details:first-child{border-top:1px solid var(--rule)}
.acc summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:clamp(20px,2.4vw,32px) 0;font-family:var(--f-title);font-size:clamp(1.4rem,2.8vw,2.4rem);text-transform:uppercase;letter-spacing:.03em}
.site[lang="he"] .acc summary{letter-spacing:0}
.acc summary::-webkit-details-marker{display:none}
.acc summary::after{content:"+";font-family:var(--f-label);font-weight:300;font-size:1.6rem;line-height:1}
.acc details[open] summary::after{content:"\2212"}
.acc .body{padding:0 0 clamp(24px,3vw,40px);display:grid;gap:1.2rem;max-width:46rem;animation:rise-in .6s var(--ease) both}
.acc .body p{color:var(--fg-2)}
.chips{display:flex;flex-wrap:wrap;gap:.6rem}
.chip{border:1px solid var(--fg-2);border-radius:999px;padding:.3em 1.05em;font-size:.88rem}

/* ---------- about ---------- */
.about-split{display:grid;grid-template-columns:1fr 1fr;min-height:100vh}
.about-left{position:sticky;top:0;height:100vh;overflow:hidden}
.about-left .ph{position:absolute;inset:0}
.about-left .ph::after{content:"";position:absolute;inset:0;background:rgb(0 0 0 / .52)}
.about-copy{position:absolute;inset:0;z-index:2;display:grid;place-content:center;justify-items:center;text-align:center;gap:1.6rem;padding:0 clamp(24px,7vw,110px)}
.about-copy h1{font-size:clamp(2.2rem,4vw,3.6rem);text-transform:uppercase}
.about-copy p{max-width:34rem}
.about-right{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:clamp(120px,22vh,240px) clamp(24px,7vw,120px)}
.about-right .xfade{width:82% !important;margin-top:0 !important}
.pillars{display:grid;grid-template-columns:1fr 1fr;gap:clamp(30px,6vw,90px);padding:0 var(--gutter)}
.pillars h3{font-size:clamp(1.4rem,2.2vw,1.9rem);text-transform:uppercase;margin-bottom:.9rem}
.pillars p{color:var(--fg-2)}
.founder{display:grid;gap:1rem;max-width:44rem;padding:0 var(--gutter)}
.founder h3{font-size:clamp(1.8rem,3vw,2.6rem)}

/* ---------- contact: envelope and letter ---------- */
.st-key-envelope{position:relative;overflow:hidden;min-height:100vh;padding:clamp(120px,18vh,180px) var(--gutter) 0 !important;isolation:isolate}
.st-key-envelope .stHtml:has(.c-bg),.st-key-envelope [data-testid="stElementContainer"]:has(.c-bg){position:static !important}
.c-bg{position:absolute;inset:0;z-index:-1}
.c-bg .ph{position:absolute;inset:0;animation:bg-sharp 2.4s var(--ease) both}
.c-bg .ph img{filter:grayscale(1) brightness(.42) blur(3px);transform:scale(1.04)}
@keyframes bg-sharp{from{filter:blur(18px)}to{filter:none}}
.c-side{position:absolute;top:44vh;inset-inline:var(--gutter);display:flex;justify-content:space-between;pointer-events:none;z-index:0}
.c-side span{font-family:var(--f-label);font-size:.9rem;letter-spacing:var(--track);text-transform:uppercase}
.st-key-letter{position:relative;z-index:2;max-width:640px;margin:0 auto !important;background:var(--paper);color:var(--ink);padding:clamp(28px,4vw,48px) clamp(22px,3.4vw,44px) 150px !important;box-shadow:0 30px 80px rgb(0 0 0 / .45);animation:letter-rise 1.6s var(--ease) .5s both}
@keyframes letter-rise{from{transform:translateY(46vh)}to{transform:none}}
.letter-head h1{font-family:var(--f-title);font-size:clamp(1.5rem,2.6vw,2rem);text-transform:uppercase;color:var(--ink);letter-spacing:.03em}
.site[lang="he"] .letter-head h1{letter-spacing:0}
.letter-head p{color:var(--ink-2);margin:.8rem 0 .4rem;font-size:.95rem}
.letter-head .details{display:flex;flex-wrap:wrap;gap:.3rem 1.4rem;font-size:.85rem;color:var(--ink-2);margin-top:.6rem}
.letter-head .details a{color:var(--ink);border-bottom:1px solid currentColor}
.st-key-letter .legend{font-family:var(--f-label);font-size:.72rem;letter-spacing:var(--track);text-transform:uppercase;color:var(--ink-2);border-bottom:1px solid rgb(20 19 18 / .18);padding-bottom:.4rem;margin:2rem 0 1rem}
.st-key-letter [data-testid="stWidgetLabel"] p{font-size:.8rem !important;color:var(--ink-2) !important}
.st-key-letter [data-testid="stTextInputRootElement"],.st-key-letter [data-testid="stNumberInputContainer"],
.st-key-letter [data-baseweb="input"],.st-key-letter [data-baseweb="select"]>div,
.st-key-letter [data-baseweb="textarea"],.st-key-letter [data-testid="stTextAreaRootElement"]{background:transparent !important;border:0 !important;border-bottom:1px solid rgb(20 19 18 / .35) !important;border-radius:0 !important;box-shadow:none !important}
.st-key-letter [data-baseweb="base-input"],.st-key-letter [data-baseweb="input"] [data-baseweb="input"]{background:transparent !important;border:0 !important}
.st-key-letter [data-baseweb="select"]>div:focus-within,.st-key-letter [data-baseweb="input"]:focus-within,.st-key-letter [data-baseweb="textarea"]:focus-within{border-bottom-color:var(--ink) !important}
.st-key-letter input,.st-key-letter textarea,.st-key-letter [data-baseweb="select"] div{background:transparent !important;color:var(--ink) !important;-webkit-text-fill-color:var(--ink);padding-inline:0 !important}
.st-key-letter input::placeholder,.st-key-letter textarea::placeholder{color:#8F8A83 !important;-webkit-text-fill-color:#8F8A83}
.st-key-letter [data-baseweb],.st-key-letter [data-baseweb] *,.st-key-letter [data-testid="stSelectbox"] div,.st-key-letter [data-testid="stDateInput"] div{background-color:transparent !important}
.st-key-letter [data-testid="stSelectbox"] div,.st-key-letter [data-testid="stDateInput"] div{border-color:transparent !important;border-radius:0 !important;box-shadow:none !important}
html body .stApp .st-key-letter [data-testid="stSelectbox"] div[class]{border:0 !important;border-radius:0 !important;outline:0 !important;box-shadow:none !important}
.st-key-letter [data-testid="stSelectbox"],.st-key-letter [data-testid="stDateInput"]{position:relative}
.st-key-letter [data-testid="stSelectbox"]::after,.st-key-letter [data-testid="stDateInput"]::after{content:"";position:absolute;inset-inline:0;bottom:0;height:1px;background:rgb(20 19 18 / .35)}
.st-key-letter [data-testid="stSelectbox"]:focus-within::after,.st-key-letter [data-testid="stDateInput"]:focus-within::after{background:var(--ink)}
.st-key-letter [data-testid="stSelectbox"] input,.st-key-letter [data-testid="stSelectbox"] [data-testid="stSelectboxVirtualDropdown"]{padding-inline:0 !important}
.st-key-letter [data-testid="stSelectbox"] *,.st-key-letter [data-testid="stDateInput"] *{color:var(--ink) !important;-webkit-text-fill-color:var(--ink)}
.st-key-letter [data-baseweb="select"] *,.st-key-letter [data-baseweb="input"] *{color:var(--ink) !important;-webkit-text-fill-color:var(--ink)}
.st-key-letter svg{color:var(--ink-2);fill:currentColor}
.st-key-letter [data-testid="stNumberInputStepDown"],.st-key-letter [data-testid="stNumberInputStepUp"]{background:transparent !important;color:var(--ink) !important}
.st-key-letter [data-testid="stForm"]{border:0;padding:0}
.st-key-letter [data-testid="stElementContainer"]{margin-bottom:.8rem}
.st-key-letter [data-testid="stHorizontalBlock"]{gap:1.4rem}
.st-key-letter [data-testid="stButtonGroup"] button{border-radius:999px;border:1px solid rgb(20 19 18 / .35);background:transparent;color:var(--ink)}
.st-key-letter [data-testid="stButtonGroup"] button p{color:var(--ink)}
.st-key-letter [data-testid="stButtonGroup"] button[kind$="Active"]{background:var(--ink);border-color:var(--ink)}
.st-key-letter [data-testid="stButtonGroup"] button[kind$="Active"] p{color:var(--paper)}
.st-key-letter [data-testid="stFormSubmitButton"] button{width:100%;background:transparent;color:var(--ink);border:1px solid var(--ink);border-radius:0;padding:.95rem 2rem;transition:background .3s,color .3s}
.st-key-letter [data-testid="stFormSubmitButton"] button p{font-family:var(--f-label);font-size:.8rem;letter-spacing:var(--track);text-transform:uppercase;color:inherit}
.st-key-letter [data-testid="stFormSubmitButton"] button:hover{background:var(--ink);color:var(--paper)}
.form-errors{border-inline-start:2px solid #B4472F;padding:.6rem 1rem;margin:.6rem 0;color:#9A3420;font-size:.9rem}
.form-errors ul{margin:.3rem 0 0;padding-inline-start:1.2rem}
.pocket{position:relative;z-index:3;height:190px;margin:-120px auto 0;max-width:700px;pointer-events:none}
.pocket::before{content:"";position:absolute;inset:0;background:#E3DDD1;clip-path:polygon(0 0,50% 52%,100% 0,100% 100%,0 100%);box-shadow:0 -1px 0 rgb(0 0 0 / .08)}
.pocket::after{content:"";position:absolute;inset:0;background:linear-gradient(to bottom right,transparent 49.6%,rgb(0 0 0 / .08) 50%,transparent 50.4%),linear-gradient(to bottom left,transparent 49.6%,rgb(0 0 0 / .08) 50%,transparent 50.4%);clip-path:polygon(0 0,50% 52%,100% 0,100% 100%,0 100%)}
/* sent: the paper slides back, the flap closes, the thank-you appears */
.sent{position:relative;z-index:2;max-width:700px;margin:0 auto;display:grid;justify-items:center;gap:0;padding-top:2vh}
.sent .paper{width:92%;height:260px;background:var(--paper);animation:paper-down 1.4s var(--ease) both}
.sent .env{position:relative;width:100%;height:260px;margin-top:-170px;background:#E3DDD1}
.sent .flap{position:absolute;inset:0 0 auto 0;height:58%;background:#D9D2C4;clip-path:polygon(0 0,100% 0,50% 100%);transform-origin:top;animation:flap-close 1s var(--ease) 1.1s both}
.sent .thanks{text-align:center;display:grid;gap:.8rem;justify-items:center;margin-top:2.4rem;animation:rise-in 1s var(--ease) 1.8s both}
.sent .thanks h1{font-size:clamp(1.8rem,3vw,2.6rem);text-transform:uppercase}
.sent .thanks p{color:var(--fg)}
@keyframes paper-down{from{transform:translateY(-120px)}to{transform:translateY(80px)}}
@keyframes flap-close{from{transform:scaleY(-1)}to{transform:none}}
.st-key-again{position:relative;z-index:2;display:flex;justify-content:center;padding:1.4rem 0 0}
.st-key-again button{background:transparent;border:1px solid var(--fg);border-radius:0;color:var(--fg)}
.st-key-again button p{font-family:var(--f-label);font-size:.78rem;letter-spacing:var(--track);text-transform:uppercase}
.save-error{position:relative;z-index:3;max-width:640px;margin:1rem auto 0;background:#3A1712;color:#FFD9D0;padding:1rem 1.2rem;font-size:.95rem}
.estimate{position:relative;z-index:2;max-width:640px;margin:2rem auto 0;border:1px solid var(--rule);background:rgb(0 0 0 / .55);padding:clamp(1.2rem,2.6vw,2rem);display:grid;gap:.6rem}
.est-top{display:flex;justify-content:space-between;align-items:center;gap:1rem}
.est-tag{font-size:.72rem;border:1px solid var(--todo);color:var(--todo);border-radius:999px;padding:.1rem .7rem}
.est-case{font-family:var(--f-title);font-size:1.15rem}
.est-num{font-family:var(--f-title);font-size:clamp(1.7rem,4vw,2.8rem);line-height:1.1;color:var(--fg-2);white-space:nowrap}
.est-fine{font-size:.85rem;color:var(--fg-2)}
.c-after{height:clamp(60px,10vh,120px)}

/* ---------- ML LAB ---------- */
.lab-sec{padding:clamp(48px,6vw,80px) var(--gutter) 0}
.lab-sec h2{font-size:clamp(1.4rem,2.4vw,2rem);text-transform:uppercase;margin-bottom:1.4rem}
.lab-md-head{padding-bottom:0}
.lab-empty{color:var(--todo)}
.lab-run{border:1px solid var(--rule);padding:1.4rem 1.6rem;display:grid;gap:.6rem}
.lab-run.succeeded{border-color:#7FB79A}
.lab-run.stopped{border-color:var(--err);background:rgb(232 144 126 / .07)}
.lab-run-status{font-family:var(--f-title);font-size:clamp(1.5rem,2.6vw,2.1rem);text-transform:uppercase}
.lab-run.succeeded .lab-run-status{color:#9FD3B6}
.lab-run.stopped .lab-run-status,.lab-stop-gate{color:var(--err)}
.lab-run-meta{color:var(--fg-2);font-size:.88rem}
.lab-violations{margin:0;padding-inline-start:1.2rem;color:var(--err);font-family:Consolas,monospace;font-size:.88rem;display:grid;gap:.3rem}
.lab-stages{list-style:none;margin:0 !important;padding:0 !important}
.lab-stages li{margin:0 !important;padding-inline:0 !important}
.lab-stage{display:grid;grid-template-columns:2.4rem minmax(0,1.1fr) minmax(0,1.6fr) auto;gap:1rem 1.6rem;align-items:baseline;padding-block:1.1rem;border-bottom:1px solid var(--rule)}
.lab-stage:first-child{border-top:1px solid var(--rule)}
.lab-stage .n{font-family:var(--f-title);color:var(--fg-2)}
.lab-stage .t{font-family:var(--f-title);font-size:1.2rem;text-transform:uppercase}
.lab-stage .d{color:var(--fg-2)}
.pill{font-size:.72rem;border:1px solid var(--fg-2);color:var(--fg-2);border-radius:999px;padding:.1rem .8rem;white-space:nowrap}
.pill.ok{border-color:var(--fg);background:var(--fg);color:var(--bg)}
.pill.fail{border-color:var(--err);background:var(--err);color:var(--bg)}
.pill.skip{opacity:.55}
.lab-q{font-family:var(--f-title);font-size:1.25rem;margin-bottom:1rem}
.lab-decision{display:grid;gap:.9rem;margin:0;border-inline-start:2px solid var(--accent);padding-inline-start:1.4rem}
.lab-decision dt{color:var(--fg-2);margin-bottom:.2rem}
.lab-decision dd{margin:0;line-height:1.6;max-width:62rem}
.lab-decision code{font-size:.9em;background:rgb(237 232 224 / .08);padding:0 .3em}
.lab-table{overflow-x:auto}
.lab-table table{border-collapse:collapse;width:100%;font-size:.92rem}
.lab-table th{font-family:var(--f-label);font-weight:400;font-size:.72rem;letter-spacing:var(--track);text-transform:uppercase;color:var(--fg-2);text-align:start;padding:.6rem .8rem;border-bottom:1px solid var(--rule);white-space:nowrap}
.lab-table td{padding:.6rem .8rem;border-bottom:1px solid var(--rule);vertical-align:top}
.lab-table tr.chosen td{background:rgb(237 232 224 / .06)}
.lab-table code,.lab-rules code{font-size:.85rem}
.lab-rules{margin:1rem 0 0;padding-inline-start:1.2rem;color:var(--fg-2);font-size:.9rem}
.lab-charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:clamp(12px,1.6vw,22px)}
.lab-chart{margin:0;background:#fff;padding:.4rem}
.lab-chart img{display:block;width:100%;height:auto}
.lab-chart figcaption{color:#5E5A54;font-size:.78rem;padding:.4rem .2rem .1rem}
.lab-log{background:#0e0d0c;border:1px solid var(--rule);padding:1rem 1.2rem;overflow-x:auto;font-size:.8rem;line-height:1.7;white-space:pre}
.lab-log .dec{color:#E3CF8F}
.lab-log .bad{color:var(--err)}
.lab-note{padding:1.4rem var(--gutter) 0;color:var(--todo);font-size:.92rem}
.st-key-labinsights,.st-key-labcard{padding:0 var(--gutter) !important}
.st-key-labinsights h1,.st-key-labcard h1{display:none}
.st-key-labinsights h2,.st-key-labcard h2,.st-key-labinsights h3,.st-key-labcard h3{font-family:var(--f-title) !important;font-weight:400 !important;font-size:1.25rem !important;text-transform:uppercase}
.st-key-labinsights table,.st-key-labcard table{font-size:.88rem}

/* ---------- tablet ---------- */
@media (max-width:1000px){
  .mast{grid-template-columns:auto 1fr auto auto;gap:1.2rem}
  .mast nav.main{display:none}
  .lang{justify-self:end;grid-column:3}
  .menu{display:block;justify-self:end;position:static;grid-column:4}
  .menu summary{list-style:none;cursor:pointer;font-family:var(--f-label);font-size:.8rem;letter-spacing:var(--track);text-transform:uppercase}
  .menu summary::-webkit-details-marker{display:none}
  .menu nav{position:absolute;inset-inline:0;top:100%;background:var(--bg);border-block:1px solid var(--rule);display:grid;gap:1.1rem;padding:1.6rem var(--gutter) 2rem;font-family:var(--f-title);font-size:1.7rem;text-transform:uppercase}
  .covers{grid-template-columns:repeat(2,minmax(0,1fr))}
  .foot-top{grid-template-columns:1fr 1fr}
  .foot-top .brand-col{grid-column:1/-1}
}
/* ---------- phone ---------- */
@media (max-width:700px){
  .site{font-size:15.5px}
  .home-split,.about-split{grid-template-columns:1fr}
  .home-left,.about-left{position:relative;height:92svh}
  .home-copy{inset-inline:20px;bottom:44px}
  .home-copy h1{font-size:clamp(2.4rem,11vw,3.2rem)}
  .home-right{padding:56px 16px 24px}
  .home-bride{aspect-ratio:4/5}
  .home-bride .rot{display:none}
  .home-bride .upright{display:block}
  .xfade{width:100% !important;margin-top:24px !important}
  .xfade-cap{width:100%}
  .covers{grid-template-columns:1fr;gap:16px}
  .cover{aspect-ratio:4/5}
  .p-hero{height:86svh}
  .g-pair{grid-template-columns:1fr}
  .g-wide{aspect-ratio:4/5}
  .g-detail{width:100%;margin-block:0}
  .cta-band{height:70svh}
  .pillars{grid-template-columns:1fr}
  .foot-top{grid-template-columns:1fr}
  .foot-bottom{flex-direction:column-reverse;align-items:flex-start}
  .st-key-envelope{padding:110px 12px 0 !important}
  .st-key-letter{padding:26px 18px 140px !important}
  .st-key-letter [data-testid="stHorizontalBlock"]{flex-direction:column;gap:0}
  .c-side{display:none}
  .lab-stage{grid-template-columns:2rem 1fr}
  .lab-stage .d,.lab-stage .pill{grid-column:2}
  .lab-charts{grid-template-columns:1fr}
}
/* ---------- reduced motion: no intro, no crossfades, no slide-ins ---------- */
@media (prefers-reduced-motion:reduce){
  .intro{display:none !important}
  *,*::before,*::after{animation:none !important;transition:none !important}
  .xfade img:not(:first-child){opacity:0 !important}
  .films-row video{display:none}
  .films-row .still{display:block}
}
"""


@st.cache_data
def _fonts_css() -> str:
    return (APP_DIR / "static" / "fonts" / "fonts.css").read_text(encoding="utf-8")


def inject() -> None:
    """Inject fonts and site CSS. Call once per page run, before any content."""
    from ui import icon_css  # local import: ui imports theme

    st.html(f"<style>{_fonts_css()}\n{_CSS}\n{icon_css()}</style>")
