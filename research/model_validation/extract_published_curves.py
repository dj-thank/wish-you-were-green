#!/usr/bin/env python3
"""Re-extract compact vector curves from the authors' published fit PDFs.

Optional provenance refresh, not required for the offline scientific analysis.
Requires PyMuPDF and the tesseract executable in addition to requirements-core.
Full PDFs stay in --pdf-cache; only selected vector paths are written here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ocr(page, rectangle, fitz):
    with tempfile.TemporaryDirectory(prefix="wd-fit-label-") as temporary:
        image = Path(temporary) / "label.png"
        page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=fitz.Rect(*rectangle)).save(image)
        return subprocess.run(["tesseract", str(image), "stdout", "--psm", "7"],
                              capture_output=True, text=True, check=True).stdout.strip()


def extraction(page, family, fitz):
    drawings = page.get_drawings()
    left, right, top = 80.4, 570.72, 431.6
    y_ticks = []
    for drawing in drawings:
        if drawing["color"] != (0., 0., 0.):
            continue
        for item in drawing["items"]:
            if item[0] != "l":
                continue
            a, b = item[1:]
            if abs(a.y-b.y) < .01 and min(abs(a.x-left), abs(b.x-left)) < .02 and 4 < abs(a.x-b.x) < 8 and top < a.y < 737:
                y_ticks.append(a.y)
    y_ticks = np.unique(np.round(y_ticks, 4))
    assert len(y_ticks) == 6 and np.allclose(y_ticks, [446, 504.08, 562.16, 620.24, 678.32, 736.16], atol=.001), y_ticks
    # The numerical y labels were checked on the rendered source pages.
    y_values = np.array([1., .8, .6, .4, .2, 0.])
    y_fit = np.polyfit(y_ticks, y_values, 1)
    bottom = float(y_ticks[-1])
    x_ticks = []
    for drawing in drawings:
        if drawing["color"] != (0., 0., 0.):
            continue
        for item in drawing["items"]:
            if item[0] != "l":
                continue
            a, b = item[1:]
            if abs(a.x-b.x) < .01 and min(abs(a.y-bottom), abs(b.y-bottom)) < .02 and 4 < abs(a.y-b.y) < 8 and left < a.x < right:
                x_ticks.append(a.x)
    x_ticks = np.unique(np.round(x_ticks, 4))
    label = ocr(page, (80, 737, 571, 758), fitz)
    wavelengths = [int(s) for s in re.findall(r"\b\d{4}\b", label)]
    expected = [4000, 5000, 6000] if family == "DQ" else [4000, 5000, 6000, 7000]
    assert wavelengths == expected and len(x_ticks) == len(expected), (label, x_ticks)
    x_fit = np.polyfit(x_ticks, wavelengths, 1)
    axis = {"x_major_ticks_pdf_pt": x_ticks.tolist(), "x_major_tick_wavelength_angstrom": wavelengths,
            "x_tick_label_ocr": label, "x_to_wavelength_polynomial": x_fit.tolist(),
            "x_tick_fit_max_error_angstrom": float(np.max(np.abs(np.polyval(x_fit, x_ticks)-wavelengths))),
            "y_major_ticks_pdf_pt": y_ticks.tolist(), "y_major_tick_relative_fnu": y_values.tolist(),
            "y_to_relative_fnu_polynomial": y_fit.tolist(),
            "y_tick_fit_max_error_relative_fnu": float(np.max(np.abs(np.polyval(y_fit, y_ticks)-y_values))),
            "source_graphic_coordinate_quantum_pdf_pt": .24,
            "one_graphic_quantum_angstrom": float(abs(x_fit[0])*.24),
            "one_graphic_quantum_relative_fnu": float(abs(y_fit[0])*.24),
            "bottom_panel_bounds_pdf_pt": [left, top, right, bottom]}
    arrays, diagnostics = {}, {}
    for kind, color in (("observed", (0., 0., 0.)), ("model", (1., 0., 0.))):
        segments = []
        for drawing in drawings:
            items = drawing["items"]
            minimum_lines = 2 if kind == "model" else 20
            if drawing["color"] != color or len(items) < minimum_lines or not all(i[0] == "l" for i in items):
                continue
            lines = np.array([(i[1].x, i[1].y, i[2].x, i[2].y) for i in items])
            if not np.allclose(lines[1:, :2], lines[:-1, 2:], atol=.001, rtol=0):
                continue
            if np.any(lines[:, 2]-lines[:, 0] < -.001):
                continue
            points = np.vstack((lines[0, :2], lines[:, 2:]))
            if np.ptp(points[:, 0]) < .1:
                continue
            if points[:, 0].min() < left-.02 or points[:, 0].max() > right+.02 or points[:, 1].min() < top-.02 or points[:, 1].max() > bottom+.02:
                continue
            # At least 20 connected monotone-x line segments distinguish
            # the black spectrum from glyph outlines and axes. The bottom
            # panel has no red text or photometric symbols; preserve short
            # red start/end paths as well, so the model is not truncated.
            segments.append(points)
        assert len(segments) >= 8, (kind, len(segments))
        segments.sort(key=lambda s: s[0, 0])
        points = np.vstack(segments)
        segment_id = np.concatenate([np.full(len(s), n, np.int32) for n, s in enumerate(segments)])
        arrays[kind+"_pdf_xy"] = points.astype(np.float32)
        arrays[kind+"_segment_id"] = segment_id
        wave = np.polyval(x_fit, points[:, 0])
        diagnostics[kind] = {"vertices": len(points), "path_segments": len(segments),
                             "min_wavelength_angstrom": float(wave.min()), "max_wavelength_angstrom": float(wave.max()),
                             "max_join_gap_angstrom": float(max((b[0, 0]-a[-1, 0])*x_fit[0] for a, b in zip(segments[:-1], segments[1:])))}
    return axis, arrays, diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--pdf-cache", type=Path, required=True)
    parser.add_argument("--download", action="store_true", help="Download missing official PDFs into the specified cache")
    args = parser.parse_args()
    import fitz
    base = args.root.resolve()/"research/model_validation"
    manifest_path = base/"sources/published_curve_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    args.pdf_cache.mkdir(parents=True, exist_ok=True)
    documents = {}
    for source in manifest["pdf_sources"]:
        path = args.pdf_cache/source["file"]
        if not path.exists() and args.download:
            urllib.request.urlretrieve(source["url"], path)
        assert sha(path) == source["sha256"], path
        assert hashlib.md5(path.read_bytes()).hexdigest() == source["archive_md5"]
        documents[source["file"]] = fitz.open(path)
        assert len(documents[source["file"]]) == source["pages"]
    output = base/"sources/published_curves"
    output.mkdir(parents=True, exist_ok=True)
    for target in manifest["selected_pages"]:
        page = documents[target["archive"]][target["page_1based"]-1]
        label = ocr(page, (123, 83, 516, 111), fitz)
        assert target["source_id"] in "".join(label.split()), label
        family = "DQ" if "DQ" in target["archive"] else "DZ"
        axis, arrays, diagnostics = extraction(page, family, fitz)
        path = output/(target["source_id"]+".npz")
        np.savez_compressed(path, **arrays)
        target.update(label_ocr=label, gaia_ocr_exact_after_whitespace_removal=True,
                      axis=axis, vector_diagnostics=diagnostics,
                      compact_path=str(path.relative_to(args.root.resolve())), compact_sha256=sha(path))
        target.pop("gaia_ocr_exact", None)
    manifest["extraction_software"] = {"PyMuPDF": fitz.VersionBind,
        "tesseract": subprocess.run(["tesseract", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]}
    manifest["extraction_script_sha256"] = sha(Path(__file__))
    manifest_path.write_text(json.dumps(manifest, indent=2)+"\n")
    print(f"PASS vector extraction: {len(manifest['selected_pages'])} exact Gaia identities; original PDF hashes; labelled axes; both plotted curves retained")


if __name__ == "__main__":
    main()
