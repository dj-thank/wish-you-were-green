#!/usr/bin/env python3
"""Render manually authored page/panel observations; this does not inspect images."""
from pathlib import Path
import csv,hashlib,json
from datetime import datetime,timezone

OUT=Path(__file__).resolve().parent
NOTES=OUT/"visual_notes_64_126.json"
INDEX=OUT/"contact_sheet_index.csv"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    notes=json.loads(NOTES.read_text())
    with INDEX.open() as f:
        index=list(csv.DictReader(f))
    rows=[]
    page_hashes={}
    for page,observations in sorted(notes["pages"].items(),key=lambda p:int(p[0])):
        p=int(page)
        assert 64<=p<=109
        items=sorted([x for x in index if int(x["page"])==p],key=lambda x:int(x["panel"]))
        assert len(items)==len(observations),(p,len(items),len(observations))
        for item,observation in zip(items,observations):
            assert len(observation)>=20 and "\n" not in observation
            unavailable=observation.startswith("Unavailable:")
            assert unavailable==(int(item["plotted_records"])==0),(p,item["panel"],observation)
            image=OUT/item["contact_sheet"]
            actual=page_hashes.setdefault(p,sha(image))
            assert notes["viewed_page_sha256"][str(p)]==actual,(p,"image differs from the bytes recorded at visual review")
            assert actual==item["contact_sheet_sha256"],(p,"sheet changed")
            rows.append({"page":p,"panel":int(item["panel"]),"entity_id":item["entity_id"],
              "source_id":item["source_id"],"visual_status":"unavailable_panel_inspected" if unavailable else "current_spectrum_panel_inspected",
              "observation":observation,
              "evidence_limits":"Prepared current F_lambda display only; 20 A mean and native cleaned min/max, supplied independent-pixel errors when available. No detector-image or covariance-based physical confirmation.",
              "all_row_indices":item["all_row_indices"],"plotted_row_indices":item["plotted_row_indices"],
              "unavailable_eligible_row_indices":item["unavailable_eligible_row_indices"],
              "all_records":item["all_records"],"eligible_records":item["eligible_records"],
              "plotted_records":item["plotted_records"],"unit_withheld_records":item["unit_withheld_records"],
              "other_withheld_records":item["other_withheld_records"],
              "contact_sheet":item["contact_sheet"],"contact_sheet_sha256":actual})
    assert len({r["entity_id"] for r in rows})==len(rows)
    complete=len(rows)==736 and set(page_hashes)==set(range(64,110))
    if complete:
        assigned={x["entity_id"] for x in index if 64<=int(x["page"])<=109}
        assert {r["entity_id"] for r in rows}==assigned
    keys=list(rows[0]) if rows else ["page","panel","entity_id","visual_status","observation","evidence_limits"]
    with (OUT/"visual_review_64_126.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    unavailable=sum(r["visual_status"]=="unavailable_panel_inspected" for r in rows)
    lines=["# Visual review of the remaining queue: pages 64–109","",
      "**Status: "+("completed" if complete else "in progress")+".** "+str(len(rows))+" of 736 assigned entity panels have actually been viewed, across "+str(len(page_hashes))+" of 46 assigned pages. "+
      str(len(rows)-unavailable)+" panels contain current eligible spectra; "+str(unavailable)+" were inspected as explicit unavailable panels, without a claim to have viewed a missing spectrum.","",
      "Reviewer: ChatGPT-assisted visual audit, 19 October 2026 UTC. The final assignment is followup_index 1008–1743 (zero based), pages 64–109. Pages 110–126 were reassigned to a separate reviewer before they were viewed here; the original ledger filename is retained. The preceding 1,008 and final 263 entities are assigned separately. These 736 entities are outside the 337 objects inspected in the previous audit.","",
      "## What the display means","",
      "Every observation below was manually authored after opening its corresponding contact sheet in the image viewer. This ledger-rendering script only joins those notes to the stable index and validates page hashes; it does not perform or substitute for image inspection.","",
      "The generator uses the current unit-validated F_lambda screen, the stored accepted photometric calibration and a per-spectrum normalization near 5350 A (with its documented fallback). The 20 A arithmetic means are display aids. Vertical strokes retain the minimum and maximum of cleaned native samples within a bin; shaded errors, if present, assume independent supplied pixels and omit calibration uncertainty and covariance. Gaia XP oscillations cannot be interpreted as independent resolved spectral lines. The plotted ordinate includes the shown extrema; a rare excursion can make the broad continuum difficult to inspect.","",
      "Unknown-unit and other ineligible records are withheld, including when another eligible record of the same entity is shown. No curve in such a blank panel was visually reviewed. Signed flux is retained and the generator's existing narrow sky-window exclusions apply. A visually smooth curve does not establish source cleanliness; an apparent discontinuity does not diagnose its cause or prove missing wavelength samples.","",
      "No new colour, line identification, abundance, variability detection, posterior probability or candidate rejection was inferred from these pictures alone. The separate [targeted follow-up](targeted_diagnostics/README.md) checks selected earlier concerns against export samples and an official Gaia query.","",
      "## Per-panel observations",""]
    for p in sorted(page_hashes):
        items=[r for r in rows if r["page"]==p]
        lines += [f"### Page {p:03d}", "", f"[Open contact sheet]({items[0]['contact_sheet']})", "",
          "| Panel | Entity | Plotted rows | Observation |","|---:|---|---|---|"]
        for r in items:
            lines.append(f"| {r['panel']} | {r['entity_id']} | {r['plotted_row_indices'].replace('|', ', ') or '—'} | {r['observation'].replace('|',' / ')} |")
        lines.append("")
    lines += ["## Audit linkage","",
      "The [CSV](visual_review_64_126.csv) retains record identifiers, withheld counts, a per-panel visual status and the actual contact-sheet SHA256. [Manually authored notes](visual_notes_64_126.json) are the input to [the ledger renderer](build_visual_ledger_64_126.py). The full record-level availability ledger belongs to the sheet generator and remains separate from visual judgments.",""]
    (OUT/"visual_review_64_126.md").write_text("\n".join(lines))
    result={"updated_utc":datetime.now(timezone.utc).isoformat(),"assigned_entities":736,"assigned_pages":[64,109],"viewed_entity_panels":len(rows),
        "viewed_spectrum_panels":len(rows)-unavailable,"viewed_unavailable_panels":unavailable,"pages_viewed":sorted(page_hashes),
        "complete":complete,"manual_notes_sha256":sha(NOTES),"contact_sheet_index_sha256_at_render":sha(INDEX),
        "ledger_renderer_sha256":sha(Path(__file__)),"page_sha256":{str(k):v for k,v in page_hashes.items()}}
    (OUT/"visual_review_64_126.summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"complete":complete,"entity_panels":len(rows),"pages":len(page_hashes),"unavailable_panels":unavailable}))

if __name__=="__main__":build()
