#!/usr/bin/env python3
"""Source-backed checks of selected v0.1 visual concerns; no new colour selection."""
from __future__ import annotations
import argparse, csv, gzip, hashlib, io, json, os, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "targeted_diagnostics"
RAW = OUT / "raw"
SELECTED_ROWS = [1250, 3004, 2714, 2930, 8376]
SOURCES = ["1060188315963488640", "3688869246424920448",
           "2629980411471669632", "2802900781266410112",
           "4573582236809330432", "2163612727665972096",
           "2002597083798483200", "5078976609103251456",
           "1245262790370992256"]
TABLE = ROOT / "research/precision/flux_units/corrected_record_screen.csv.gz"

def utc():
    return datetime.now(timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def records():
    with gzip.open(TABLE, "rt") as f:
        return list(csv.DictReader(f))

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def fetch_one(job):
    name, url, expected = job
    target = RAW / name
    meta = {"request_url": url, "query_started_utc": utc(),
            "expected_frozen_sha256": expected}
    try:
        req = Request(url, headers={"User-Agent": "wish-you-were-green research reproducibility"})
        with urlopen(req, timeout=45) as response:
            body = response.read()
            meta.update({"status": response.status, "resolved_url": response.url,
                         "content_type": response.headers.get("Content-Type"),
                         "http_date": response.headers.get("Date")})
        meta.update({"retrieved_utc": utc(), "bytes": len(body), "sha256": digest(body)})
        if expected is not None and digest(body) != expected:
            raise ValueError("Frozen SHA256 mismatch; not replacing expected input")
        target.write_bytes(body)
        meta.update({"saved_path": str(target.relative_to(ROOT)), "result": "ok"})
    except Exception as exc:
        meta.update({"retrieved_utc": utc(), "result": "error", "error": str(exc)})
    write_json(RAW / (name + ".provenance.json"), meta)
    return meta

def fetch():
    RAW.mkdir(parents=True, exist_ok=True)
    selected = [r for r in records() if int(r["row_index"]) in SELECTED_ROWS]
    jobs = [(f"row_{r['row_index']}.txt", r["source_url"], r["sha256"]) for r in selected]
    query = ("SELECT g.source_id,g.ra,g.dec,g.ref_epoch,g.pmra,g.pmdec,"
             "g.phot_g_mean_mag,g.bp_rp,g.ruwe,g.phot_variable_flag,g.has_xp_continuous,"
             "v.classifier_name,v.best_class_name,v.best_class_score "
             "FROM gaiadr3.gaia_source AS g LEFT OUTER JOIN gaiadr3.vari_classifier_result AS v "
             "ON g.source_id=v.source_id WHERE g.source_id IN (" + ",".join(SOURCES) + ") "
             "ORDER BY g.source_id")
    (OUT / "gaia_query.adql").write_text(query + "\n")
    url = "https://gea.esac.esa.int/tap-server/tap/sync?" + urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query})
    jobs.append(("gaia_feature_review.csv", url, None))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch_one, jobs))
    write_json(OUT / "retrieval.json", {"created_utc": utc(), "requests": results,
                                      "code_sha256": digest(Path(__file__).read_bytes()),
                                      "input_table_sha256": digest(TABLE.read_bytes())})
    print(json.dumps({"requests": len(results), "ok": sum(r["result"]=="ok" for r in results),
                      "errors": [r.get("error") for r in results if r["result"]!="ok"]}))
    return results

def load_export(path):
    import numpy as np
    raw = path.read_text().strip().splitlines()
    # MWDD exports contain one descriptive metadata line before the CSV header.
    # Keep that source-specific contract explicit, matching download_frozen_spectra.py.
    header_index = 1 if raw[0].startswith("wdid:") else 0
    delimiter = "," if "," in raw[header_index] else None
    header = raw[header_index]
    names = [s.strip().lstrip("#").strip() for s in (header.split(",") if delimiter else header.split())]
    data = np.loadtxt(io.StringIO("\n".join(raw[header_index+1:])), delimiter=delimiter, ndmin=2)
    return {name: data[:, j] for j, name in enumerate(names)}

def analyze():
    import numpy as np
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-feature-mpl")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(ROOT))
    import colour_pipeline as colour
    OUT.mkdir(parents=True, exist_ok=True)
    selected = [r for r in records() if int(r["row_index"]) in SELECTED_ROWS]
    summaries = []
    fig, axes = plt.subplots(2, 3, figsize=(16, 8), constrained_layout=True)
    detail_fig, detail_axes = plt.subplots(2, 3, figsize=(14, 7), constrained_layout=True)
    desi_number = 0
    for ax, r in zip(axes.flat, selected):
        path = RAW / f"row_{r['row_index']}.txt"
        if not (r["flux_units_validated"] == "True" and r["flux_input_convention"] == "flambda" and r["status"] == "ok"):
            raise ValueError(f"row {r['row_index']}: not a currently validated F_lambda input")
        if not path.exists():
            ax.set_title(f"row {r['row_index']}: unavailable"); ax.axis("off"); continue
        assert digest(path.read_bytes()) == r["sha256"]
        a = load_export(path)
        wave_key = next(k for k in a if k.lower() in ("wavelength", "wavelength_angstrom", "wave"))
        flux_key = next(k for k in a if k.lower() in ("flux", "flux_original", "flux_flam"))
        w, f = a[wave_key], a[flux_key]
        order = np.argsort(w); w, f = w[order], f[order]
        visible = (w >= 3600) & (w <= 8300) & np.isfinite(f) & np.isfinite(w)
        anchor = (w >= 5200) & (w <= 5500) & np.isfinite(f)
        norm = np.median(f[anchor])
        if not np.isfinite(norm) or norm <= 0: norm = np.median(np.abs(f[visible]))
        values = {"row_index": int(r["row_index"]), "source_id": r["source_id"], "kind": r["kind"],
                  "wdid": r["wdid"], "source_url": r["source_url"], "raw_sha256": r["sha256"],
                  "flux_convention": r["flux_input_convention"], "columns": list(a),
                  "samples": int(len(w)), "visible_samples": int(visible.sum()),
                  "visible_negative_samples": int((f[visible] < 0).sum()),
                  "largest_visible_step_A": float(np.diff(w[visible]).max()),
                  "normalization_median_5200_5500": float(norm),
                  "current_stored_Duv": float(r["duv"]), "current_calibrated": r["calibrated"],
                  "raw_spectrum_not_recalibrated_here": True}
        windows = []
        for center, width in [(4861,80),(5577,30),(6563,100),(5890,80)]:
            m=visible & (np.abs(w-center)<=width)
            if not m.any(): continue
            j=np.where(m)[0][np.argmax(f[m])]
            k=np.where(m)[0][np.argmin(f[m])]
            windows.append({"window_center_A": center,"halfwidth_A":width,
                            "finite_samples":int(m.sum()),"maximum_A":float(w[j]),
                            "maximum_flux_over_anchor":float(f[j]/norm),
                            "minimum_A":float(w[k]),"minimum_flux_over_anchor":float(f[k]/norm)})
        values["predeclared_feature_windows"] = windows
        ivar_key = next((k for k in a if k.lower() in ("ivar", "inverse_variance")),None)
        error_key = next((k for k in a if k.lower() in ("error", "flux_error", "sigma")),None)
        flag_key = next((k for k in a if k.lower() in ("flag", "mask")),None)
        if ivar_key:
            ivar = a[ivar_key][order]
            values["visible_nonpositive_ivar_samples"] = int((ivar[visible]<=0).sum())
            values["visible_median_pixel_snr"] = float(np.median(f[visible]*np.sqrt(np.maximum(ivar[visible],0))))
        if error_key:
            err = a[error_key][order]
            values["visible_nonpositive_error_samples"] = int((err[visible]<=0).sum())
            pos = visible & np.isfinite(err) & (err>0)
            values["visible_median_pixel_snr"] = float(np.median(f[pos]/err[pos]))
            ax.fill_between(w[visible]/10,(f[visible]-err[visible])/norm,
                            (f[visible]+err[visible])/norm,color="#9dbfe0",alpha=.28,linewidth=0)
        if flag_key:
            flags=a[flag_key][order]
            u,c=np.unique(flags[visible],return_counts=True)
            values["export_flag_values_counts"]={str(int(x)):int(n) for x,n in zip(u,c)}
            values["export_flag_semantics"]="Not assumed to equal native DESI camera MASK; retained, not used to reject samples."
        if r["kind"] == "DESI" and error_key:
            iv = np.divide(1.,err**2,out=np.zeros_like(err),where=np.isfinite(err)&(err>0))
            baseline = colour.integrate_colour(w,f,iv,mask_sky=False)
            masked = colour.integrate_colour(w,f,iv,mask_sky=True)
            keep5577 = np.abs(w-5577.34)>8
            only5577 = colour.integrate_colour(w[keep5577],f[keep5577],iv[keep5577],mask_sky=False)
            values["raw_mask_sensitivity"] = {
                "definition": "Current F_lambda export before PS1 recalibration; compare retaining all signed finite samples with named window removal. No error distribution is inferred.",
                "all_samples_duv": baseline["duv"],
                "standard_five_sky_windows_duv": masked["duv"],
                "only_5577_34_pm8A_removed_duv": only5577["duv"],
                "standard_windows_delta_uv": float(np.hypot(baseline["u1960"]-masked["u1960"],baseline["v1960"]-masked["v1960"])),
                "only_5577_window_delta_uv": float(np.hypot(baseline["u1960"]-only5577["u1960"],baseline["v1960"]-only5577["v1960"]))}
            values["native_window_samples"] = []
            for j,(center,halfwidth) in enumerate([(5577.34,30),(5890,45),(6300.30,30)]):
                m=visible & (np.abs(w-center)<=halfwidth)
                da=detail_axes[desi_number,j]
                da.errorbar(w[m],f[m]/norm,yerr=err[m]/norm,fmt=".-",lw=.7,markersize=2,elinewidth=.6,color="#15549a")
                da.axvline(center,color="gray",ls=":",lw=.6);da.axhline(0,color="black",lw=.5)
                da.set_title(f"row {r['row_index']} / {center:g} ± {halfwidth:g} Å",fontsize=9)
                da.set_xlabel("Wavelength (Å)");da.set_ylabel("Normalized Fλ ± export σ")
                da.grid(alpha=.12)
                if j==0:
                    mm=visible & (np.abs(w-center)<=12)
                    values["native_window_samples"]=[{"wavelength_A":float(ww),"flux":float(ff),"sigma":float(ss)} for ww,ff,ss in zip(w[mm],f[mm],err[mm])]
            desi_number+=1
        ax.plot(w[visible]/10,f[visible]/norm,lw=.6,color="#15549a")
        for x in [486.1,557.7,656.3]: ax.axvline(x,color="gray",lw=.5,ls=":")
        ax.axhline(0,color="black",lw=.4)
        ax.set_title(f"{r['source_id']} / {r['kind']} / row {r['row_index']}",fontsize=8)
        ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Fλ / median Fλ at 520–550 nm")
        ax.grid(alpha=.12); summaries.append(values)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(0,.95,"Targeted native-grid follow-up\n\n"
        "No display binning; signed samples retained.\n"
        "DESI grid: archived export, not CCD pixels.\n"
        "MWDD Gaia XP samples are a reconstruction,\nnot independent detector pixels.\n\n"
        "Window extrema are descriptive, not line\nidentification or detection significance.\n\n"
        "Original export flags are not assumed to be\nnative camera masks.\n\n"
        "Unresolved-unit SDSS curves are not plotted.",va="top",fontsize=11)
    fig.savefig(OUT/"native_grid_overview.png",dpi=160)
    fig.savefig(OUT/"native_grid_overview.svg")
    detail_fig.suptitle("DESI export samples: narrow features with supplied uncertainties; no line detection or native camera-mask claim",fontsize=11)
    detail_fig.savefig(OUT/"desi_native_windows.png",dpi=160)
    detail_fig.savefig(OUT/"desi_native_windows.svg")
    result={"created_utc":utc(),"code_sha256":digest(Path(__file__).read_bytes()),
            "input_table_sha256":digest(TABLE.read_bytes()),"records":summaries,
            "limitations":["No new formal line detection, equivalent width, or pixel-covariance likelihood.",
                           "Gaia variability classifier shares Gaia observations with XP; not independent photons.",
                           "NOT_AVAILABLE does not establish nonvariability; classifier scores are not posterior probabilities.",
                           "Local continuum normalization is for display only, not an absolute calibration."]}
    if (RAW/"gaia_feature_review.csv").exists():
        result["gaia_official_rows"]=list(csv.DictReader((RAW/"gaia_feature_review.csv").open()))
    write_json(OUT/"diagnostics.json",result)
    print(json.dumps({"analyzed_records":len(summaries),"gaia_rows":len(result.get("gaia_official_rows",[]))}))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--fetch",action="store_true");p.add_argument("--analyze",action="store_true")
    a=p.parse_args()
    if not (a.fetch or a.analyze):p.error("Choose --fetch and/or --analyze")
    if a.fetch:fetch()
    if a.analyze:analyze()

if __name__=="__main__": main()
