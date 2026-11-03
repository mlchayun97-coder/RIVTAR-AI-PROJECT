"""Prepare website photos from the RIVATAR Google Drive export.

The export arrives split into several parts ("RIVATAR WEBSITE-<stamp>-001", "-002", ...), each holding
"RIVATAR WEBSITE/<event folder>/...". All parts are treated as one source.

Steps
1. Scan every part and write a catalog CSV (event, subfolder, file, type, width, height, size).
2. Per event, score every photo (sharpness = variance of the Laplacian, plus resolution), skip near
   duplicates (64-bit difference hash), and keep up to N photos. A manual override file
   (selection.json) can force-include or exclude photos.
3. Write web copies: EXIF rotation applied, colours converted to sRGB, all metadata (EXIF/GPS)
   stripped, .jfif/.png converted to JPEG. Long edge 1600 px + 600 px thumbnails.
   Output files get neutral names (<slug>-01.jpg) so original file names never reach the repo.
4. Keep the committed web assets under a size budget: if over, step down quality, then long edge.
5. Write manifest.json (read by the website) and print the total size.

Default mode (site redesign): export exactly the photos and videos chosen in the content files
(app/content/projects/<slug>.json, app/content/site.json) at 400/800/1600 px, plus muted 720p video
loops (max 10 s, under 3 MB) made with imageio-ffmpeg, and write app/static/media.json. Steps 1-4
above remain available as --auto-select (phase-1 automatic picking, useful for drafting selections).

Usage:
    python scripts/prepare_media.py                 # curated export from the content files
    python scripts/prepare_media.py --force         # re-export everything
    python scripts/prepare_media.py --auto-select   # phase-1 automatic selection into app/static/events
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rivatar import config  # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".jfif", ".png"}
VIDEO_EXT = {".mp4", ".mov"}
EXPORT_INNER = "RIVATAR WEBSITE"

# Folders in the export that are not client events.
NON_EVENT_FOLDERS = {"LOGO", "השראה אתר"}

# Explicit slugs (no surnames). Unknown folders fall back to slugify().
SLUGS = {
    "AVIGAIL & NURI": "avigail-nuri",
    "BAILEY & MOTEL": "bailey-motel",
    "BAR MITZVA AARON": "aaron-bar-mitzvah",
    "BAR MITZVA DAVID COHEN": "david-bar-mitzvah",
    "EDEN & BINYAMIN WEDDING": "eden-binyamin",
    "EVYATAR & RIVKA WEDDING": "evyatar-rivka",
    "SHAINDEL& MEIR": "shaindel-meir",
}

# Budget ladder: (long edge, JPEG quality), tried in order until the total fits.
LADDER = [(1600, 80), (1600, 75), (1600, 70), (1400, 70), (1280, 68), (1200, 65)]

SRGB = ImageCms.createProfile("sRGB")


# ---------------------------------------------------------------- helpers
def normalize_name(name: str) -> str:
    """NFC, drop combining marks (e.g. a stray Hebrew vowel point), collapse spaces."""
    decomposed = unicodedata.normalize("NFKD", name)
    no_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", no_marks)).strip()


def slugify(name: str) -> str:
    norm = normalize_name(name)
    if norm in SLUGS:
        return SLUGS[norm]
    ascii_ = unicodedata.normalize("NFKD", norm).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")
    return slug or "event"


def find_export_parts(source_root: Path) -> list[Path]:
    parts = sorted(p for p in source_root.glob(config.MEDIA_EXPORT_GLOB) if p.is_dir())
    return [p / EXPORT_INNER if (p / EXPORT_INNER).is_dir() else p for p in parts]


@dataclass
class MediaFile:
    path: Path
    event: str | None  # normalized event folder name; None for loose files
    subfolder: str
    kind: str  # image | video | other
    width: int | None = None
    height: int | None = None
    size: int = 0


@dataclass(eq=False)
class Candidate:
    media: MediaFile
    sharpness: float
    dhash: int
    colors: np.ndarray  # 8x8 RGB signature, 0..1
    score: float = 0.0


@dataclass
class EventResult:
    slug: str
    folder: str
    images: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------- scanning
def scan(source_root: Path) -> list[MediaFile]:
    files: list[MediaFile] = []
    for part in find_export_parts(source_root):
        for path in sorted(part.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(part)
            ext = path.suffix.lower()
            kind = "image" if ext in IMAGE_EXT else "video" if ext in VIDEO_EXT else "other"
            event = normalize_name(rel.parts[0]) if len(rel.parts) > 1 else None
            subfolder = "/".join(rel.parts[1:-1])
            mf = MediaFile(path, event, subfolder, kind, size=path.stat().st_size)
            if kind == "image":
                try:
                    with Image.open(path) as im:
                        w, h = im.size
                        orient = im.getexif().get(0x0112, 1)
                    mf.width, mf.height = (h, w) if orient in (5, 6, 7, 8) else (w, h)
                except Exception as exc:  # unreadable file: catalogued, never selected
                    print(f"  ! cannot read {rel}: {exc}")
                    mf.kind = "other"
            files.append(mf)
    return files


def write_catalog(files: list[MediaFile], catalog_path: Path) -> None:
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with catalog_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["event", "subfolder", "file", "type", "width", "height", "size"])
        for f in files:
            w.writerow([f.event or "", f.subfolder, f.path.name, f.kind, f.width or "", f.height or "", f.size])


# ---------------------------------------------------------------- scoring
def _analysis_image(path: Path, edge: int = 512) -> Image.Image:
    im = Image.open(path)
    im.draft("RGB", (edge, edge))  # fast JPEG decode at reduced scale
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((edge, edge))
    return im


def color_signature(rgb: Image.Image) -> np.ndarray:
    return np.asarray(rgb.resize((8, 8), Image.Resampling.BOX), dtype=np.float32) / 255.0


def similarity(a: "Candidate", b: "Candidate") -> float:
    """0 = unrelated, 1 = identical (structure via dHash, palette via the colour signature)."""
    s_struct = max(0.0, 1.0 - hamming(a.dhash, b.dhash) / 32)
    s_color = max(0.0, 1.0 - float(np.abs(a.colors - b.colors).mean()) / 0.25)
    return 0.6 * s_struct + 0.4 * s_color


def sharpness(gray: Image.Image) -> float:
    a = np.asarray(gray, dtype=np.float32)
    lap = -4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    return float(lap.var())


def dhash(gray: Image.Image) -> int:
    small = np.asarray(gray.resize((9, 8), Image.Resampling.LANCZOS), dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def score_candidates(images: list[MediaFile]) -> list[Candidate]:
    cands = []
    for m in images:
        try:
            rgb = _analysis_image(m.path)
        except Exception as exc:
            print(f"  ! skip {m.path.name}: {exc}")
            continue
        g = rgb.convert("L")
        cands.append(Candidate(m, sharpness(g), dhash(g), color_signature(rgb)))
    if not cands:
        return cands
    logs = np.log1p([c.sharpness for c in cands])
    lo, hi = float(logs.min()), float(logs.max())
    for c, s in zip(cands, logs):
        sharp_n = (s - lo) / (hi - lo) if hi > lo else 1.0
        res_n = min(1.0, ((c.media.width or 0) * (c.media.height or 0)) / 12e6)
        c.score = 0.75 * sharp_n + 0.25 * res_n
    return cands


def select(cands: list[Candidate], n: int, override: dict, dup_threshold: int = 10,
           diversity: float = 0.6) -> list[Candidate]:
    """Forced includes first (in the given order), then greedy picks that balance quality and variety.

    Near duplicates (dHash distance <= dup_threshold) are always skipped. Among the rest, each step
    takes the photo with the best  score - diversity * (max similarity to photos already picked).
    """
    include = [str(x) for x in override.get("include", [])]
    exclude = {str(x) for x in override.get("exclude", [])}
    by_name = {c.media.path.name: c for c in cands}
    picked: list[Candidate] = [by_name[x] for x in include if x in by_name and x not in exclude]
    pool = [c for c in cands if c not in picked and c.media.path.name not in exclude]
    while len(picked) < n:
        pool = [c for c in pool if all(hamming(c.dhash, p.dhash) > dup_threshold for p in picked)]
        if not pool:
            break
        best = max(pool, key=lambda c: c.score - diversity * max((similarity(c, p) for p in picked), default=0.0))
        picked.append(best)
        pool.remove(best)
    return picked[:n]


# ---------------------------------------------------------------- export
def load_web_image(path: Path) -> Image.Image:
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    icc = im.info.get("icc_profile")
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (242, 237, 228))  # site background #F2EDE4
        bg.paste(im, mask=im.getchannel("A"))
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            im = ImageCms.profileToProfile(im, src, SRGB, outputMode="RGB")
        except Exception:
            pass
    clean = Image.new("RGB", im.size)  # fresh image: no EXIF, GPS, XMP or ICC carried over
    clean.paste(im)
    return clean


def save_jpeg(im: Image.Image, dest: Path, edge: int, quality: int) -> None:
    out = im.copy()
    out.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, "JPEG", quality=quality, optimize=True, progressive=True)


def export_event(slug: str, picked: list[Candidate], out_dir: Path, edge: int, quality: int, thumb: int) -> list[dict]:
    ev_dir = out_dir / slug
    for old in list(ev_dir.glob(f"{slug}-*.jpg")) + list((ev_dir / "thumbs").glob(f"{slug}-*.jpg")):
        old.unlink()
    images = []
    for i, c in enumerate(picked, start=1):
        name = f"{slug}-{i:02d}.jpg"
        im = load_web_image(c.media.path)
        save_jpeg(im, ev_dir / name, edge, quality)
        save_jpeg(im, ev_dir / "thumbs" / name, thumb, quality)
        with Image.open(ev_dir / name) as done:
            w, h = done.size
        images.append({
            "file": f"{slug}/{name}",
            "thumb": f"{slug}/thumbs/{name}",
            "width": w,
            "height": h,
            "orientation": "landscape" if w > h * 1.05 else "portrait" if h > w * 1.05 else "square",
            "score": round(c.score, 4),
        })
    return images


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


def load_selection(path: Path, slugs: list[str]) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    template = {
        "_help": "Per event slug: 'include' = original file names to force (in order, first = cover); "
                 "'exclude' = original file names to skip. Re-run scripts/prepare_media.py after editing.",
        **{s: {"include": [], "exclude": []} for s in slugs},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return template


# ---------------------------------------------------------------- main
def run(source_root: Path, out_dir: Path, catalog: Path, per_event: int = 12, budget_mb: float = 25.0,
        thumb: int = 600, ladder: list[tuple[int, int]] | None = None,
        other_asset_dirs: list[Path] | None = None) -> dict:
    ladder = ladder or LADDER
    print(f"Scanning {source_root} ...")
    files = scan(source_root)
    write_catalog(files, catalog)
    n_img = sum(f.kind == "image" for f in files)
    n_vid = sum(f.kind == "video" for f in files)
    print(f"  {len(files)} files ({n_img} images, {n_vid} videos skipped) -> {catalog}")

    events: dict[str, list[MediaFile]] = {}
    for f in files:
        if f.kind == "image" and f.event and f.event not in NON_EVENT_FOLDERS:
            events.setdefault(f.event, []).append(f)

    slugs = {ev: slugify(ev) for ev in sorted(events)}
    selection = load_selection(out_dir / "selection.json", list(slugs.values()))

    picks: dict[str, list[Candidate]] = {}
    for ev, imgs in sorted(events.items()):
        slug = slugs[ev]
        cands = score_candidates(imgs)
        picks[slug] = select(cands, per_event, selection.get(slug, {}))
        print(f"  {slug}: {len(imgs)} photos -> {len(picks[slug])} selected")

    other = sum(dir_size(d) for d in (other_asset_dirs or []))
    budget = budget_mb * 1024 * 1024
    results: list[EventResult] = []
    for edge, quality in ladder:
        results = []
        for ev in sorted(events):
            slug = slugs[ev]
            results.append(EventResult(slug, ev, export_event(slug, picks[slug], out_dir, edge, quality, thumb)))
        events_size = sum(dir_size(out_dir / r.slug) for r in results)
        print(f"  pass edge={edge}px q={quality}: events {events_size / (1024 * 1024):.2f} MB")
        if events_size + other <= budget:
            break
    else:
        print("  ! still over budget at the last ladder step")

    manifest = {
        "settings": {"long_edge": edge, "quality": quality, "thumb_edge": thumb, "per_event": per_event},
        "events": {r.slug: {"count": len(r.images), "images": r.images} for r in results},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total = dir_size(out_dir) + other
    print(f"\nTotal committed web assets: {total / (1024 * 1024):.2f} MB (budget {budget_mb:.0f} MB)")
    return {"manifest": manifest, "total_bytes": total, "catalog_rows": len(files)}


# ================================================================ curated export (site redesign)
# The website shows only what the content files choose (app/content/projects/<slug>.json and
# app/content/site.json). This step resolves those original file names in the export, writes web copies
# at several widths with neutral names, encodes the short video loops, and writes app/static/media.json.

# Web widths per role: full-width photos need 1600 px, pairs and details 1000 px, covers 400/800 px.
ROLE_SIZES = {"hero": (800, 1600), "wide": (800, 1600), "pair": (600, 1000), "detail": (600, 1000),
              "cover": (400, 800), "home": (800, 1600)}
SIZES = tuple(sorted({w for ws in ROLE_SIZES.values() for w in ws}))
QUALITY = {400: 72, 600: 70, 800: 70, 1000: 68, 1600: 64}
VIDEO_MAX_SOURCE_MB = 10         # never touch large files (the 74.8 MB reel, the 2.6 GB clip)
VIDEO_MAX_MB = 3.0
VIDEO_SECONDS = 10
VIDEO_SHORT_SIDE = 720


def build_source_index(source_root: Path) -> dict[tuple[str, str], list[Path]]:
    """(normalized top folder, file name) -> paths, over all export parts. Images and videos."""
    index: dict[tuple[str, str], list[Path]] = {}
    for part in find_export_parts(source_root):
        for path in part.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_EXT | VIDEO_EXT:
                rel = path.relative_to(part)
                if len(rel.parts) > 1:
                    index.setdefault((normalize_name(rel.parts[0]), normalize_name(path.name)), []).append(path)
    return index


def folder_for_slug(slug: str) -> str | None:
    return next((folder for folder, s in SLUGS.items() if s == slug), None)


def resolve(index: dict, folder: str | None, name: str, root: Path) -> Path:
    """'design-reference/x.jpg' (relative to the project root), 'LOGO/x.jfif' (export folder/name),
    or a bare file name inside `folder`."""
    if "/" in name:
        local = root / name
        if local.is_file():
            return local
        folder, name = name.split("/", 1)
    hits = index.get((normalize_name(folder or ""), normalize_name(name)), [])
    if not hits:
        raise FileNotFoundError(f"{name!r} not found in export folder {folder!r}")
    if len({h.stat().st_size for h in hits}) > 1:
        raise ValueError(f"{name!r} is ambiguous in {folder!r} ({len(hits)} different files)")
    return hits[0]


def _sig(path: Path, extra: str = "") -> str:
    st = path.stat()
    return f"{st.st_size}:{int(st.st_mtime)}:{extra}"


def export_photo(src: Path, out_dir: Path, base: str, rotate: int = 0, sizes=SIZES) -> dict:
    im = load_web_image(src)
    if rotate:
        im = im.rotate(rotate, expand=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for w in sizes:
        copy = im.copy()
        if copy.width > w:
            copy = copy.resize((w, round(copy.height * w / copy.width)), Image.Resampling.LANCZOS)
        copy.save(out_dir / f"{base}-{w}.jpg", "JPEG", quality=QUALITY.get(w, 72), optimize=True, progressive=True)
        made.append(w)
    return {"base": base, "w": im.width, "h": im.height, "sizes": made}


def export_video(src: Path, out_dir: Path, base: str) -> dict | None:
    """Muted 720p loop, max 10 s, under 3 MB, plus a poster frame. None if ffmpeg is unavailable."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - depends on the machine
        print(f"  ! ffmpeg unavailable ({exc}); skipping {src.name}")
        return None
    import subprocess

    out_dir.mkdir(parents=True, exist_ok=True)
    mp4, poster = out_dir / f"{base}.mp4", out_dir / f"{base}-poster.jpg"
    side = VIDEO_SHORT_SIDE
    scale = f"scale='if(gt(iw,ih),-2,{side})':'if(gt(iw,ih),{side},-2)'"
    for crf in (28, 31, 34, 37):
        cmd = [ffmpeg, "-v", "error", "-y", "-i", str(src), "-t", str(VIDEO_SECONDS), "-an", "-sn", "-dn",
               "-map_metadata", "-1", "-vf", f"{scale},fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "slow",
               "-crf", str(crf), "-movflags", "+faststart", str(mp4)]
        subprocess.run(cmd, check=True)
        if mp4.stat().st_size <= VIDEO_MAX_MB * 1024 * 1024:
            break
    else:
        print(f"  ! {base}: still over {VIDEO_MAX_MB} MB at crf 37")
    raw = out_dir / f"{base}-poster-raw.png"
    subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", "0.5", "-i", str(mp4), "-frames:v", "1", str(raw)], check=True)
    im = load_web_image(raw)
    raw.unlink()
    im.save(poster, "JPEG", quality=72, optimize=True, progressive=True)
    return {"file": mp4.name, "poster": poster.name, "w": im.width, "h": im.height, "bytes": mp4.stat().st_size}


def curated_jobs(content_dir: Path) -> tuple[list[dict], list[dict]]:
    """Everything the content files ask for: photo jobs and video jobs."""
    site = json.loads((content_dir / "site.json").read_text(encoding="utf-8"))
    photos, videos = [], []
    for pf in sorted((content_dir / "projects").glob("*.json")):
        proj = json.loads(pf.read_text(encoding="utf-8"))
        slug = proj["slug"]
        jobs: dict[str, dict] = {}
        items = [(proj.get("cover"), "cover"), (proj.get("hero"), "hero")]
        items += [(ph, ph.get("layout", "wide")) for ch in proj.get("chapters", []) for ph in ch.get("photos", [])]
        for item, role in items:
            if item and item.get("photo"):
                job = jobs.setdefault(item["photo"], {"group": slug, "folder": folder_for_slug(slug),
                                                      "name": item["photo"], "rotate": int(item.get("rotate", 0)),
                                                      "sizes": set()})
                job["sizes"] |= set(ROLE_SIZES.get(role, ROLE_SIZES["wide"]))
        photos += list(jobs.values())
        videos += [{"group": slug, "folder": folder_for_slug(slug), "name": v["video"]} for v in proj.get("videos", [])]
    home = site.get("home", {})
    for key in ("courtyard", "card", "bride"):
        if home.get(key, {}).get("source"):
            photos.append({"group": "home", "folder": None, "name": home[key]["source"], "key": key, "rotate": 0,
                           "sizes": set(ROLE_SIZES["home"])})
    if home.get("bride", {}).get("rotate_desktop") and home["bride"].get("source"):
        photos.append({"group": "home", "folder": None, "name": home["bride"]["source"], "key": "bride-rot",
                       "rotate": 90, "sizes": set(ROLE_SIZES["home"])})
    return photos, videos


def run_curated(source_root: Path, static_dir: Path, content_dir: Path, budget_mb: float = 40.0,
                other_asset_dirs: list[Path] | None = None, force: bool = False, root: Path = ROOT) -> dict:
    """Export the curated photos and videos. Unchanged sources are skipped (see media.json 'sig')."""
    manifest_path = static_dir / "media.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    index = build_source_index(source_root)
    photos, videos = curated_jobs(content_dir)
    manifest: dict = {"sizes": list(SIZES), "projects": {}, "videos": {}, "home": {}}
    counters: dict[str, int] = {}
    errors: list[str] = []

    for job in photos:
        group = job["group"]
        try:
            src = resolve(index, job["folder"], job["name"], root)
        except (FileNotFoundError, ValueError) as exc:
            errors.append(f"{group}: {exc}")
            continue
        if group == "home":
            base, out_dir = job["key"], static_dir / "home"
            prev = old.get("home", {}).get(job["key"])
        else:
            counters[group] = counters.get(group, 0) + 1
            base, out_dir = f"{group}-{counters[group]:02d}", static_dir / "projects" / group
            prev = old.get("projects", {}).get(group, {}).get(job["name"])
        sizes = tuple(sorted(job.get("sizes") or SIZES))
        sig = _sig(src, f"r{job['rotate']}|{sizes}|{sorted(QUALITY.items())}")
        if (not force and prev and prev.get("sig") == sig and prev.get("base") == base
                and all((out_dir / f"{base}-{w}.jpg").exists() for w in prev["sizes"])):
            entry = prev
        else:
            entry = {**export_photo(src, out_dir, base, job["rotate"], sizes), "sig": sig}
            print(f"  wrote {out_dir.name}/{base} ({entry['w']}x{entry['h']})")
        if group == "home":
            manifest["home"][job["key"]] = entry
        else:
            manifest["projects"].setdefault(group, {})[job["name"]] = entry

    vcount: dict[str, int] = {}
    for job in videos:
        group = job["group"]
        try:
            src = resolve(index, job["folder"], job["name"], root)
        except (FileNotFoundError, ValueError) as exc:
            errors.append(f"{group}: {exc}")
            continue
        if src.stat().st_size > VIDEO_MAX_SOURCE_MB * 1024 * 1024:
            errors.append(f"{group}: {job['name']} is over {VIDEO_MAX_SOURCE_MB} MB, skipped by rule")
            continue
        vcount[group] = vcount.get(group, 0) + 1
        base, out_dir = f"{group}-v{vcount[group]:02d}", static_dir / "projects" / group
        sig = _sig(src, f"{VIDEO_SECONDS}|{VIDEO_SHORT_SIDE}|{VIDEO_MAX_MB}")
        prev = next((v for v in old.get("videos", {}).get(group, []) if v.get("source") == job["name"]), None)
        if not force and prev and prev.get("sig") == sig and prev.get("file") == f"{base}.mp4" \
                and (out_dir / prev["file"]).exists():
            entry = prev
        else:
            entry = export_video(src, out_dir, base)
            if entry is None:
                continue
            entry.update(source=job["name"], sig=sig)
            print(f"  wrote {base}.mp4 ({entry['bytes'] / 1024 / 1024:.2f} MB)")
        manifest["videos"].setdefault(group, []).append(entry)

    # remove web copies that the content files no longer ask for
    keep = {f"{e['base']}-{w}.jpg" for g in manifest["projects"].values() for e in g.values() for w in e["sizes"]}
    keep |= {f"{e['base']}-{w}.jpg" for e in manifest["home"].values() for w in e["sizes"]}
    keep |= {n for vs in manifest["videos"].values() for v in vs for n in (v["file"], v["poster"])}
    for sub in (static_dir / "projects", static_dir / "home"):
        if sub.exists():
            for f in sub.rglob("*"):
                if f.is_file() and f.name not in keep:
                    f.unlink()

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    web = dir_size(static_dir / "projects") + dir_size(static_dir / "home") + manifest_path.stat().st_size
    total = web + sum(dir_size(d) for d in (other_asset_dirs or []))
    print(f"\nCurated media: {web / 1024 / 1024:.2f} MB; total committed web assets: "
          f"{total / 1024 / 1024:.2f} MB (budget {budget_mb:.0f} MB)")
    for e in errors:
        print(f"  ! {e}")
    return {"manifest": manifest, "total_bytes": total, "errors": errors}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source-root", type=Path, default=config.ROOT, help="folder holding the export parts")
    ap.add_argument("--budget-mb", type=float, default=40.0)
    ap.add_argument("--force", action="store_true", help="re-export everything")
    ap.add_argument("--auto-select", action="store_true",
                    help="phase-1 mode: score and pick photos automatically into app/static/events")
    ap.add_argument("--per-event", type=int, default=12)
    ap.add_argument("--thumb", type=int, default=600)
    args = ap.parse_args(argv)

    others = [config.STATIC_DIR / "fonts", config.APP_DIR / "assets"]
    if args.auto_select:
        result = run(args.source_root, config.EVENTS_STATIC_DIR, config.MEDIA_CATALOG_CSV, args.per_event,
                     args.budget_mb, args.thumb, other_asset_dirs=others)
        return 0 if result["total_bytes"] <= args.budget_mb * 1024 * 1024 else 1
    if config.EVENTS_STATIC_DIR.exists():
        others.append(config.EVENTS_STATIC_DIR)  # the phase-1 folder still counts while it exists
    result = run_curated(args.source_root, config.STATIC_DIR, config.APP_DIR / "content", args.budget_mb,
                         other_asset_dirs=others, force=args.force)
    over = result["total_bytes"] > args.budget_mb * 1024 * 1024
    return 1 if over or result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
