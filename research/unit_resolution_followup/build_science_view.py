#!/usr/bin/env python3
"""Add a scoped native-support layer without replacing the compatibility view.

The 8084-record screen and its reviewed images preserve the existing recipe.
This view changes only the 613 newly unit-resolved records, uses corresponding
native pixels with positive IVAR, and holds colours failing the same numerical
coverage gate. Existing calibration coefficients remain fixed.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(OUT))
import numpy as np
import pandas as pd
from build_current import aggregate
from native_quality_audit import COLOUR_FIELDS, SKY_WINDOWS_A

COVERAGE_FIELDS=['wave_min_A','wave_max_A','coverage_eligible','cmf_min_coverage',
    'n_visible_pixels','visible_negative_fraction','largest_visible_gap_A']
RECIPE_FIELDS=COLOUR_FIELDS+COVERAGE_FIELDS+['usable_screen','status','uv_tilt_stress_max']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def derive(compatibility,quality):
    table=compatibility.copy()
    # The old raw-without-calibration calculation is a compatibility result;
    # its support has not silently acquired native inverse variances.
    table=table.rename(columns={key:'compatibility_'+key for key in table.columns
        if key.startswith('raw_') and key not in ['raw_path','raw_sha256']})
    native=quality[quality['mode'].eq('native_positive_ivar')].set_index('row_index')
    sensitivity=quality[quality['mode'].eq('native_positive_ivar_AND_zero')].set_index('row_index')
    assert len(native)==613 and native.index.is_unique
    table['science_view_version']='2026-10-20-scoped-native-support-1'
    table['native_support_audit_scope']='outside_new_613_native_support_audit'
    table['science_quality_status']='previous_unit_validated_view_retained_outside_native_audit_scope'
    table['science_quality_reason']='The numerical result is retained from the previous unit-aware view; this native-pixel support audit did not assess this record.'
    for key in RECIPE_FIELDS:table['compatibility_recipe_'+key]=None
    for index,record in native.iterrows():
        i=int(index);before=compatibility.loc[i]
        assert int(before.row_index)==i and before.entity_id==record.entity_id
        for key in RECIPE_FIELDS:
            if key in before:table.at[i,'compatibility_recipe_'+key]=before[key]
        table.at[i,'native_support_audit_scope']='new_613_strict_same_observation_pixel_correspondence'
        table.at[i,'native_support_external_reference_id']=record.external_reference_id
        table.at[i,'native_support_original_reference_sha256']=record.direct_original_sha256
        table.at[i,'native_support_mask_policy']=record.support_mask_policy
        for key in ['native_visible_samples','native_visible_samples_with_export_correspondence',
                    'native_visible_samples_without_export_correspondence',
                    'max_native_to_export_wavelength_difference_A']:
            table.at[i,key]=record[key]
        table.at[i,'science_minus_compatibility_uv']=record.get('delta_uv_from_MWDD_recipe',np.nan)
        table.at[i,'native_support_gate_pass']=bool(record.same_numeric_coverage_gate)
        table.at[i,'native_AND_zero_sensitivity_gate_pass']=bool(sensitivity.loc[i].same_numeric_coverage_gate)
        table.at[i,'native_AND_zero_sensitivity_delta_uv']=sensitivity.loc[i].get('delta_uv_from_MWDD_recipe',np.nan)
        table.at[i,'visible_median_pixel_snr']=record.native_reference_snr
        for key in COVERAGE_FIELDS:table.at[i,key]=record.get(key,np.nan)
        # The prior calibration acceptance remains a condition. Native support
        # is additional evidence, not an opportunity to refit to a desired hue.
        usable=bool(before.usable_screen) and bool(record.same_numeric_coverage_gate) and record.status=='ok'
        table.at[i,'usable_screen']=usable
        table.at[i,'uv_tilt_stress_max']=np.nan  # Old stress result did not use the new support.
        if usable:
            for key in COLOUR_FIELDS:table.at[i,key]=record.get(key,np.nan)
            table.at[i,'status']='ok'
            table.at[i,'science_quality_status']='native_support_gate_pass_quality_limitations_remain'
            table.at[i,'science_quality_reason']='Strictly corresponding native pixels, finite positive IVAR, and the fixed narrow sky windows; the existing calibration coefficients are unchanged. Pixel statistical errors omit calibration, covariance and target-association uncertainty.'
        else:
            for key in COLOUR_FIELDS:table.at[i,key]=None
            table.at[i,'status']='native_support_withheld'
            table.at[i,'science_quality_status']='native_colour_withheld'
            if record.status!='ok':reason=str(record.get('error','Native integration failed'))
            elif not bool(record.same_numeric_coverage_gate):
                reason=f"Native positive-IVAR support fails the existing numerical coverage gate: endpoint coverage={record.get('coverage_eligible')}, CMF proxy={record.get('cmf_min_coverage'):.8g}, maximum visible gap={record.get('largest_visible_gap_A'):.6f} A."
            else:reason='The prior recipe was ineligible; the native audit does not override its other gate.'
            table.at[i,'science_quality_reason']=reason
            table.at[i,'error']=reason
    return table


def build():
    compatibility=pd.read_csv(OUT/'current_record_screen.csv.gz',dtype={'source_id':'string'},low_memory=False)
    quality=pd.read_csv(OUT/'native_quality_metrics.csv.gz',dtype={'source_id':'string'},low_memory=False)
    table=derive(compatibility,quality)
    assert np.array_equal(table.row_index,np.arange(9902)) and table.entity_id.nunique()==6003
    table.to_csv(OUT/'science_record_view.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    objects=aggregate(table)
    objects['view_scope']='Only 613 newly resolved records have the new native-support audit; other eligible records retain the preceding view.'
    objects.to_csv(OUT/'science_object_view.csv',index=False)
    eligible=table.usable_screen.eq(True)&table.status.eq('ok')&table.flux_units_validated.eq(True)
    new=table.flux_unit_overlay_version.notna()
    strong=eligible&table.distance_planck_uv.ge(.01)
    held=new&~eligible
    previous_unavailable=table.previously_unavailable_panel.eq(True)
    summary={'input_records':len(table),'entity_keys':table.entity_id.nunique(),
        'newly_unit_resolved_records':int(new.sum()),'native_support_audited_records':int(new.sum()),
        'previously_eligible_records_outside_native_support_scope':int((eligible&~new).sum()),
        'compatibility_eligible_records':int(compatibility.usable_screen.eq(True).sum()),
        'current_eligible_records':int(eligible.sum()),'current_strong_records':int(strong.sum()),
        'current_strong_entities':table[strong].entity_id.nunique(),
        'newly_resolved_native_supported_eligible_records':int((eligible&new).sum()),
        'newly_resolved_native_supported_strong_records':int((strong&new).sum()),
        'newly_resolved_native_supported_green_records':int((eligible&new&table.green_dominant.eq(True)).sum()),
        'newly_resolved_colour_withheld_records':int(held.sum()),
        'newly_withheld_after_compatibility_gate_records':int((held&compatibility.usable_screen.eq(True)).sum()),
        'newly_withheld_after_compatibility_gate_row_indices':table[held&compatibility.usable_screen.eq(True)].row_index.astype(int).tolist(),
        'previously_unavailable_entities_with_units_resolved':table[new&previous_unavailable].entity_id.nunique(),
        'previously_unavailable_entities_with_native_supported_colour':table[new&previous_unavailable&eligible].entity_id.nunique(),
        'remaining_MWDD_SDSS_unresolved_records':966,
        'default_native_mask_policy':{'positive_finite_IVAR_required':True,'finite_export_pixel_correspondence_tolerance_A':.02,
            'native_comparison_window_A':[3600,8300],'sky_windows_centre_halfwidth_A':SKY_WINDOWS_A,
            'AND_OR_blanket_exclusion':False,'AND_zero':'Separate diagnostic sensitivity; not adopted as a general mask.'},
        'coverage_gate':'Existing endpoint gate, CMF proxy > 0.995 and maximum visible gap < 150 A. The CMF proxy integrates across gaps and is not direct observed support; this gate remains exploratory.',
        'calibration_policy':'Hold the existing full-grid SDSS gri or fallback PS1 coefficients fixed. Do not refit after native-mask selection.',
        'statistical_error_limits':'Native diagonal pixel-noise propagation only; covariance, calibration and source-centering errors are absent.',
        'scope':'This is a scoped improvement for 613 records. The other 9289 rows did not receive a new native support audit; 7473 previously eligible values are retained. The total is not a claim that all records passed the new native gate.',
        'contact_sheet_scope':'39 reviewed contact sheets remain frozen compatibility-recipe displays; current native-support withheld colours must not be inferred from their old Duv labels.',
        'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [OUT/'current_record_screen.csv.gz',OUT/'native_quality_metrics.csv.gz',OUT/'compact_manifest.json',OUT/'overlay_registry.json',OUT/'contact_sheet_manifest.json']},
        'output_sha256':{p.name:sha(p) for p in [OUT/'science_record_view.csv.gz',OUT/'science_object_view.csv']}}
    (OUT/'science_view_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':build()
