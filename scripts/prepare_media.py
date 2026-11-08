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

Videos are catalogued but not processed in this phase.

Usage:
    python scripts/prepare_media.py                 # defaults from rivatar.config
    python scripts/prepare_media.py --per-event 10 --budget-mb 20
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source-root", type=Path, default=config.ROOT, help="folder holding the export parts")
    ap.add_argument("--out", type=Path, default=config.EVENTS_STATIC_DIR)
    ap.add_argument("--catalog", type=Path, default=config.MEDIA_CATALOG_CSV)
    ap.add_argument("--per-event", type=int, default=12)
    ap.add_argument("--budget-mb", type=float, default=25.0)
    ap.add_argument("--thumb", type=int, default=600)
    args = ap.parse_args(argv)

    # Everything else that is committed under app/ counts toward the same budget.
    others = [config.STATIC_DIR / "fonts", config.APP_DIR / "assets"] if args.out == config.EVENTS_STATIC_DIR else []
    result = run(args.source_root, args.out, args.catalog, args.per_event, args.budget_mb, args.thumb,
                 other_asset_dirs=others)
    return 0 if result["total_bytes"] <= args.budget_mb * 1024 * 1024 else 1


if __name__ == "__main__":
    raise SystemExit(main())
