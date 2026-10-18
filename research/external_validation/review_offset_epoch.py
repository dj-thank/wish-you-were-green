#!/usr/bin/env python3
"""Review the brightest J1323 r-band point, flagged by epoch astrometry."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import simple_norm

from acquire import BASE, RAW, fetch
from analyze_ztf import propagated, angular_distance, finite_json


def main():
    epoch = pd.read_csv(BASE / "results/target_epoch_decisions.csv.gz", dtype={"oid": str, "expid": str, "gaia_source_id": str, "filefracday": str})
    star = epoch[(epoch.candidate == "J1323-0129") & (epoch.oid == "424210100006030")]
    event = star[star.expid == "214855443"].iloc[0]
    before = star[star.accepted & (star.mjd < event.mjd)].sort_values("mjd").iloc[-1]
    after = star[star.accepted & (star.mjd > event.mjd)].sort_values("mjd").iloc[0]
    gaia = pd.read_csv(RAW / "gaia_dr3_15arcsec_fields.csv", dtype={"source_id": str}).set_index("source_id").loc["3638333660492606976"]
    sources = [("before", before), ("offset_event", event), ("after", after)]
    jobs = []
    for label, row in sources:
        ffd = row.filefracday
        ccdid, qid = int(row.ccdid, 0), int(row.qid, 0)
        url = (f"https://irsa.ipac.caltech.edu/ibe/data/ztf/products/sci/{ffd[:4]}/{ffd[4:8]}/{ffd[8:]}/"
               f"ztf_{ffd}_{int(row.field):06d}_{row.filtercode}_c{ccdid:02d}_o_q{qid}_sciimg.fits")
        jobs.append((f"J1323_{label}_science_cutout", url,
                     dict(center=f"{gaia.ra},{gaia.dec}", size="50arcsec", gzip="false"), "fits"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        for r in pool.map(lambda j: fetch(*j), jobs):
            print(r, flush=True)
    if any(not (RAW / f"J1323_{label}_science_cutout.fits").exists() for label, _ in sources):
        raise RuntimeError("One or more public science cutouts could not be retrieved")
    fig = plt.figure(figsize=(13, 4.7))
    image_audit = []
    for i, (label, row) in enumerate(sources):
        with fits.open(RAW / f"J1323_{label}_science_cutout.fits") as hdul:
            hdu = next(h for h in hdul if h.data is not None and np.asarray(h.data).ndim == 2)
            data, header = np.asarray(hdu.data, float), hdu.header
            wcs = WCS(header)
        expected_ra, expected_dec = propagated(gaia, row.mjd)
        expected_x, expected_y = wcs.world_to_pixel_values(expected_ra, expected_dec)
        catalog_x, catalog_y = wcs.world_to_pixel_values(row.ra, row.dec)
        yy, xx = np.indices(data.shape)
        radius = np.hypot(xx-expected_x, yy-expected_y)
        background = np.median(data[(radius > 12) & (radius < 22)])
        bg_sigma = 1.4826 * np.median(abs(data[(radius > 12) & (radius < 22)] - background))
        ax = fig.add_subplot(1, 3, i+1)
        norm = simple_norm((data-background)/max(bg_sigma,1.e-9), "asinh", vmin=-2, vmax=20, asinh_a=.08)
        ax.imshow((data-background)/max(bg_sigma,1.e-9), origin="lower", cmap="gray_r", norm=norm)
        ax.scatter([expected_x], [expected_y], marker="+", s=140, c="#187bd1", linewidth=1.7, label="Gaia motion prediction")
        ax.scatter([catalog_x], [catalog_y], marker="o", s=100, facecolors="none", edgecolors="#cd4b1c", linewidth=1.5, label="ZTF detection centroid")
        ax.set_xlim(expected_x-12, expected_x+12)
        ax.set_ylim(expected_y-12, expected_y+12)
        ax.set_title(f"{label.replace('_',' ')} · MJD {row.mjd:.3f}\nr={row.mag:.3f}±{row.magerr:.3f}; offset {row.target_sep_epoch_arcsec:.2f}″", fontsize=10)
        ax.set_xlabel("Image x pixel")
        if i == 0:
            ax.set_ylabel("Image y pixel")
        # This merely reports the scene and FITS quality metadata. It does not
        # fit or subtract a PSF or establish the cause of the displaced point.
        image_audit.append(dict(label=label, expid=row.expid, mjd=float(row.mjd), r_native_mag=float(row.mag),
                                epoch_separation_arcsec=float(row.target_sep_epoch_arcsec), shape=list(data.shape),
                                expected_gaia_pixel=[float(expected_x),float(expected_y)],
                                detection_centroid_pixel=[float(catalog_x),float(catalog_y)],
                                local_background_DN=float(background), local_background_mad_sigma_DN=float(bg_sigma),
                                fits_metadata={k:header.get(k) for k in ["OBSJD","OBSMJD","SEEING","FWHM","MAGZP","MAGZPRMS","CLRCOEFF","INFOBITS","AIRMASS","EXPTIME"]}))
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False)
    fig.suptitle("J1323−0129: the apparent brightening has a displaced centroid", fontsize=15)
    fig.tight_layout(rect=[0,.09,1,.91])
    fig.savefig(BASE / "results/J1323_offset_event_review.png", dpi=170)
    plt.close(fig)
    report = dict(event_expid="214855443", candidate="J1323-0129", source_id="3638333660492606976",
                  event_catflags=int(event.catflags), event_mjd=float(event.mjd),
                  event_native_r=float(event.mag), neighboring_native_r=[float(before.mag),float(after.mag)],
                  event_offset_from_epoch_predicted_gaia_arcsec=float(event.target_sep_epoch_arcsec),
                  event_offset_from_unpropagated_gaia2016_arcsec=float(event.target_sep_gaia2016_arcsec),
                  images=image_audit,
                  conclusion="This detection is positionally inconsistent with the star at the adopted 1.5 arcsec threshold despite catflags=0. It is withheld from stellar-variability inference and retained in the epoch decision table. The science cutouts are a scene check, not a PSF/deblending or transient identification analysis; origin remains unresolved.",
                  alternatives_to_investigate=["A nearby moving/transient source", "A contaminated or biased PSF centroid", "A single-exposure image or extraction artifact"],
                  not_established=["A flare of the white dwarf", "The identity or physical cause of the excess image flux", "No astrophysical transient exists in the cutout"])
    (BASE / "results/J1323_offset_event_review.json").write_text(json.dumps(finite_json(report), indent=2, allow_nan=False)+"\n")
    print(json.dumps({k:report[k] for k in ["event_offset_from_epoch_predicted_gaia_arcsec","event_offset_from_unpropagated_gaia2016_arcsec","event_native_r","neighboring_native_r"]}, indent=2))


if __name__ == "__main__":
    main()
