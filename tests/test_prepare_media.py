"""prepare_media on a tiny temporary export (never touches the real photos)."""

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_media", ROOT / "scripts" / "prepare_media.py")
pm = importlib.util.module_from_spec(spec)
sys.modules["prepare_media"] = pm  # dataclasses need the module registered
spec.loader.exec_module(pm)


def _photo(path: Path, size=(2400, 1600), seed=0, exif_orientation=None, gps=False, fmt="JPEG"):
    rng = np.random.default_rng(seed)
    arr = (rng.random((size[1] // 40, size[0] // 40, 3)) * 255).astype("uint8")
    im = Image.fromarray(arr).resize(size, Image.Resampling.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    exif = Image.Exif()
    if exif_orientation:
        exif[0x0112] = exif_orientation
    if gps:
        exif[0x8825] = {1: "N", 2: (31.0, 46.0, 0.0)}
    if fmt == "PNG":
        im.convert("RGBA").save(path, "PNG")
    else:
        im.save(path, "JPEG", exif=exif.tobytes(), quality=90)


@pytest.fixture
def export(tmp_path):
    """Two parts of one export: an event split across parts, a vowel-marked folder name, a LOGO folder."""
    p1 = tmp_path / "src" / "RIVATAR WEBSITE-20260101T000000Z-1-001" / "RIVATAR WEBSITE"
    p2 = tmp_path / "src" / "RIVATAR WEBSITE-20260101T000000Z-1-002" / "RIVATAR WEBSITE"
    ev = "AVIGAIL & NURI"
    _photo(p1 / ev / "a.jpg", seed=1, exif_orientation=6, gps=True)   # rotated + GPS
    _photo(p1 / ev / "b.jpg", seed=2)
    _photo(p1 / ev / "b_copy.jpg", seed=2)                               # exact duplicate of b
    _photo(p2 / ev / "sub" / "c.jfif", seed=3, size=(1200, 1800))
    _photo(p2 / ev / "d.png", seed=4, size=(800, 800), fmt="PNG")
    _photo(p2 / "SHAINDEL&ַ MEIR" / "x.jpg", seed=5)                  # hidden Hebrew vowel mark
    _photo(p1 / "LOGO" / "logo.jpg", seed=6)
    (p2 / ev / "clip.mp4").write_bytes(b"\x00" * 100)
    return tmp_path


def test_prepare_media_end_to_end(export, capsys):
    out, catalog = export / "out", export / "catalog.csv"
    result = pm.run(export / "src", out, catalog, per_event=3, budget_mb=25)

    rows = list(csv.DictReader(catalog.open(encoding="utf-8")))
    assert len(rows) == 8
    assert {r["type"] for r in rows} == {"image", "video"}
    assert set(rows[0]) == {"event", "subfolder", "file", "type", "width", "height", "size"}
    a = next(r for r in rows if r["file"] == "a.jpg")
    assert (int(a["width"]), int(a["height"])) == (1600, 2400)   # catalog reports the rotated size

    events = result["manifest"]["events"]
    assert set(events) == {"avigail-nuri", "shaindel-meir"}      # LOGO skipped, vowel mark normalised
    imgs = events["avigail-nuri"]["images"]
    assert len(imgs) == 3                                         # per-event cap
    for meta in imgs:
        f = out / meta["file"]
        assert f.name.startswith("avigail-nuri-") and f.suffix == ".jpg"   # neutral names
        with Image.open(f) as im:
            assert max(im.size) <= 1600 and im.format == "JPEG"
            assert len(im.getexif()) == 0 and "icc_profile" not in im.info
        with Image.open(out / meta["thumb"]) as th:
            assert max(th.size) <= 600
    assert (out / "manifest.json").exists() and (out / "selection.json").exists()
    assert "Total committed web assets" in capsys.readouterr().out


def test_near_duplicates_are_skipped(export):
    out = export / "out"
    result = pm.run(export / "src", out, export / "c.csv", per_event=12)
    # 5 photos, one exact duplicate -> 4 kept
    assert result["manifest"]["events"]["avigail-nuri"]["count"] == 4


def test_rotation_applied(export):
    out = export / "out"
    pm.run(export / "src", out, export / "c.csv", per_event=12)
    sizes = [tuple(Image.open(p).size) for p in (out / "avigail-nuri").glob("*.jpg")]
    assert (1067, 1600) in sizes          # the EXIF-rotated 2400x1600 landscape became portrait


def test_selection_override(export):
    out = export / "out"
    out.mkdir()
    (out / "selection.json").write_text(json.dumps({"avigail-nuri": {"include": ["d.png"], "exclude": ["a.jpg"]}}),
                                        encoding="utf-8")
    result = pm.run(export / "src", out, export / "c.csv", per_event=2)
    imgs = result["manifest"]["events"]["avigail-nuri"]["images"]
    assert len(imgs) == 2 and imgs[0]["width"] == imgs[0]["height"] == 800   # forced d.png comes first
    with Image.open(out / imgs[0]["file"]) as im:
        assert im.mode == "RGB"                                               # PNG alpha flattened


def test_budget_ladder_steps_down(export):
    out = export / "out"
    result = pm.run(export / "src", out, export / "c.csv", per_event=12, budget_mb=0.0001,
                    ladder=[(1600, 80), (800, 60)])
    assert result["manifest"]["settings"]["long_edge"] == 800


def test_slugify():
    assert pm.slugify("SHAINDEL&ַ MEIR") == "shaindel-meir"
    assert pm.slugify("BAR MITZVA DAVID COHEN") == "david-bar-mitzvah"
    assert pm.slugify("New Event 2026") == "new-event-2026"
