#!/usr/bin/env python3
"""Self-contained current table/colour viewer with lossless compressed data."""
from __future__ import annotations
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'mpl-cache'))
import numpy as np
import pandas as pd
import colour_pipeline as c


def sha(blob):return hashlib.sha256(blob).hexdigest()


def js_value(value):
    if isinstance(value,(np.integer,np.floating,np.bool_)):value=value.item()
    if isinstance(value,float):
        if np.isnan(value):return None
        if np.isposinf(value):return 'Infinity'
        if np.isneginf(value):return '-Infinity'
    if pd.isna(value):return None
    return value


def columnar(frame):
    # Column-local repetition can be compressed without rounding any number,
    # dropping any field, or relying on external assets. Repeated strings use
    # an exact dictionary only when that representation is shorter.
    vectors=[]
    for key in frame.columns:
        values=[js_value(v) for v in frame[key]]
        seen={};dictionary=[];indices=[]
        for value in values:
            token=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))
            if token not in seen:seen[token]=len(dictionary);dictionary.append(value)
            indices.append(seen[token])
        direct={'values':values};coded={'dictionary':dictionary,'indices':indices}
        vectors.append(min([direct,coded],key=lambda v:len(json.dumps(v,ensure_ascii=False,separators=(',',':')))))
    return {'columns':list(frame.columns),'count':len(frame),'vectors':vectors}


def decode_columnar(table):
    vectors=[v['values'] if 'values' in v else [v['dictionary'][i] for i in v['indices']] for v in table['vectors']]
    return [dict(zip(table['columns'],values)) for values in zip(*vectors)]


def classification_context(root=ROOT):
    """Separate, source-linked annotations; never overwrite numerical records."""
    base=Path(root)/'research/unit_resolution_followup'
    am_path=base/'root_targeted/classification_context.json'
    target_path=base/'targeted_followup/results.json'
    local_path=base/'targeted_followup/local_row_5827.json'
    am=json.loads(am_path.read_text())
    targets=json.loads(target_path.read_text())['records']
    local=json.loads(local_path.read_text())['record']
    rows=[{**am,'scope':'existing_literature_and_native_context',
        'summary_ja':'既知AM CVn連星の文献対応を位置とnative He輝線から支持：SDSS J113732.32+405458.3（Carter et al. 2014）。元のDQ:表記は保持していますが、単独光球のDQ吸収モデルの比較対照には適しません。 '+am['interpretation'],
        'source_file':'root_targeted/classification_context.json','source_record':am,
        'links':[{'href':'root_targeted/README.md','label':'既知AM CVnの文献・原画素追診断'}]}]
    for r in targets+[local]:
        index=r['row_index'];quality=r['automatic_SDSS_quality']
        preserved=r['MWDD_frozen_class']
        if index==7607:
            published=r['Kleinman2013_published_rows_within_2arcsec'][0]['spect_type']
            text=(f'原論文カタログの同じSDSS観測に {published} 分類があります。保存したMWDD分類は {preserved}、'
                f'SDSS自動分類は {quality["CLASS"]}/{quality["SUBCLASS"]} です。広い吸収状構造は多数の正IVAR・AND=0画素に残ります。'
                '原構造を保持し、新しい磁場・元素・遷移の同定とは扱いません。')
            status='existing_DAZH_same_observation_and_surviving_native_structure'
        elif index==8019:
            variable=r['Gaia_existing_variability_classification'][0]
            text=(f'カタログ分類の食い違い：保存したMWDD分類は {preserved}、原SDSSは '
                f'{quality["CLASS"]}/{quality["SUBCLASS"]}（ZWARNING={quality["ZWARNING"]}）、'
                f'Gaiaの既存分類は {variable["best_class_name"]} / {r["Gaia_DR3"]["phot_variable_flag"]}。'
                '過去のChandra BALクエーサー観測提案にも同じ名前・位置の対象があります。'
                '原論文のDZは同じ位置の別観測です。深い構造を保持し、専門分類で根拠を整理する対象とします。'
                '今回の確定再分類や新しい白色矮星の吸収発見ではなく、Gaiaのスコアも物理確率ではありません。')
            status='preserved_DZ_versus_existing_AGN_QSO_classification_conflict'
        elif index==7930:
            peak=r['narrow_peak_native_check']
            published=r['Kleinman2013_published_rows_within_2arcsec'][0]['spect_type']
            text=(f'原論文の同じ観測には {published} 分類があり、保存したMWDD分類は {preserved} です。'
                f'原格子の赤側極大は {peak["maximum_native_pixel_A"]:.5f} Å（真空）。'
                f'半ピーク超過の連続 {peak["contiguous_pixels_above_half_peak_excess"]} 画素はAND・ORの双方にBADSKYCHIがあります。'
                'ピークと元分類を保持し、今回の図だけから新しい輝線を確認したとはしません。'
                '品質フラグだけで天体由来の線が存在しないとも断定しません。')
            status='existing_DBZAE_label_and_native_BADSKYCHI_peak_warning'
        elif index==5827:
            peak=r['red_peak_native_check'];window=r['windows'][-1]
            text=(f'ローカル確認のみ：保存したMWDD分類 {preserved} と原SDSS自動分類 '
                f'{quality["CLASS"]}/{quality["SUBCLASS"]}（ZWARNING={quality["ZWARNING"]}）の食い違いを保持します。'
                '原図では赤側に隣り合う2つの山が分かれ、'
                f'極大は {peak["maximum_native_pixel_A"]:.5f} Å（真空、AND=OR=0）。'
                f'6400–6800 Åの {window["native_pixels"]} 画素はすべて正IVAR・AND=0です。'
                '既存の原配列・ヘッダー・分類だけを確認し、新しい文献・Gaia・位置の検証はしていません。'
                '物理的な再分類や線の同定は行わず、元の形を保持します。')
            status='local_only_DZ_colon_versus_automatic_CV_conflict'
        else:raise AssertionError(('Unexpected targeted annotation',index))
        rows.append({'row_index':index,'source_id':r['source_id'],
            'preserved_catalogue_spectype':preserved,'context_status':status,
            'scope':'local_native_arrays_and_existing_metadata_only' if index==5827 else 'new_public_catalogue_context_and_native_pixels',
            'summary_ja':text,'source_file':'targeted_followup/local_row_5827.json' if index==5827 else 'targeted_followup/results.json',
            'source_record':r,'links':[{'href':'targeted_followup/README.md','label':'分類・原画素の追診断と限界'},
                {'href':f'targeted_followup/native_row_{index}.png','label':f'row {index} 原画素図'},
                {'href':'targeted_followup/local_row_5827.json' if index==5827 else 'targeted_followup/results.json','label':'保存した分類・マスクの根拠'}]})
    assert {r['row_index'] for r in rows}=={6462,7607,8019,7930,5827}
    for r in rows:
        assert isinstance(r['source_id'],str)
        for link in r['links']:assert (base/link['href']).is_file()
    return {'records':rows,'scope':'Separate annotations preserve original catalogue and numerical fields; conflicting labels are not definitive reclassifications.',
        'source_document_sha256':{str(p.relative_to(root)):sha(p.read_bytes()) for p in [am_path,target_path,local_path]}}


def current_colour_plot(tab):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    sel=tab.usable_screen.eq(True)&tab.status.eq('ok')&tab.flux_units_validated.eq(True)
    q=tab[sel];new=q[q.flux_unit_overlay_version.notna()]
    fig,axes=plt.subplots(1,2,figsize=(12.8,6.2),layout='constrained')
    colors={'SDSS':'#82519b','DESI':'#237fa1','Gaia_XP':'#bf7e2a'}
    for kind,g in q.groupby('kind'):
        axes[0].scatter(g.u1960,g.v1960,s=8,alpha=.35,edgecolors='none',c=colors.get(kind,'.6'),label=f'{kind}: {len(g):,} records')
    old=q[q.flux_unit_overlay_version.isna()]
    axes[1].scatter(old.u1960,old.v1960,s=7,alpha=.25,edgecolors='none',c='#8798a1',label=f'Previously eligible: {len(old):,}')
    for convention,g in new.groupby('flux_input_convention'):
        axes[1].scatter(g.u1960,g.v1960,s=15,alpha=.75,edgecolors='none',
            c='#b94787' if convention=='fnu' else '#216da2',label=f'New {convention}: {len(g):,}')
    limits={'xlim':(min(.14,q.u1960.min()-.006),max(.32,q.u1960.max()+.006)),
        'ylim':(min(.247,q.v1960.min()-.006),max(.37,q.v1960.max()+.006))}
    for ax in axes:
        ax.plot(c._BB_UV[:,0],c._BB_UV[:,1],c='#273842',lw=1,label='Planck continuum locus')
        ax.set(**limits,xlabel='CIE 1960 u',ylabel='CIE 1960 v');ax.set_aspect('equal',adjustable='box')
        ax.legend(fontsize=7,loc='lower right');ax.grid(alpha=.13)
    axes[0].set_title(f'{len(q):,} eligible records in the scoped scientific view\n7,473 previous values are outside this native-support audit',fontsize=10)
    axes[1].set_title(f'{len(new):,} newly unit-resolved, native-supported records\n12 additional unit-resolved records have colours withheld',fontsize=10)
    fig.suptitle('2026-10-20 scoped native-support view | equal u/v geometric scales\n'
        'Native IVAR and fixed sky masks audited for 613 records; calibration fixed. Records need not be independent.',fontsize=12)
    path=OUT/'science_colour_plane.png';fig.savefig(path,dpi=165);plt.close(fig)


HTML='''<!doctype html>
<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wish you were green — 追加単位検証後の現行ビュー</title>
<style>
:root{font:15px/1.65 system-ui,sans-serif;color:#20313c;background:#f3f5f4}*{box-sizing:border-box}body{max-width:1400px;margin:auto;padding:24px}h1{font-size:28px;margin:0}h2{font-size:19px;margin:10px 0}p{margin:8px 0}.card{background:white;border:1px solid #d7dedb;border-radius:10px;padding:20px;margin:16px 0}.muted{color:#5c6f78;font-size:13px}.metric{display:inline-block;margin-right:25px;padding:6px 0}.metric strong{font-size:24px;color:#204d43}a{color:#216799}.tools{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}input,select,button{font:inherit;padding:7px;border:1px solid #acbcb5;border-radius:5px;background:#fff}input{min-width:280px;flex:1}button{cursor:pointer}button:disabled{opacity:.5}canvas{display:block;width:100%;max-height:700px;background:#fff;border:1px solid #dde4e1}.scroll{overflow:auto;max-height:620px}table{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}td,th{text-align:left;border-bottom:1px solid #e2e7e5;padding:8px}th{background:#edf1ef;position:sticky;top:0}tr[data-row]{cursor:pointer}tr[data-row]:hover{background:#eef5fb}.swatch{display:inline-block;width:18px;height:18px;border:1px solid #71858d;vertical-align:middle;margin-right:6px}.warn{background:#fff6dc;border-left:4px solid #b28023;padding:12px}.ok{color:#246649}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f4;padding:12px;max-height:520px;overflow:auto;font-size:12px}#sheet-image{max-width:100%;height:auto}#load-error{color:#a2302b}.split{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:750px){body{padding:12px}.split{grid-template-columns:1fr}h1{font-size:22px}}</style>
<header><h1>追加の原観測照合を反映した現行ビュー</h1>
<p>2026-10-20 · frozen 9,902 records / 6,003 entity keys · additive units + scoped native support</p>
<p class="muted">単位保留1,579記録を再調査し、613記録のFν/Fλを原SDSS観測の画素一致で追加確定しました。過去の記録・図・保留判断は保存し、このビューで追加根拠を明示します。</p>
</header>
<section class="card"><div id="metrics">データを展開しています…</div>
<p class="warn">単位の一致、対象天体の対応、分光測光の品質、学術的な新規性は別の問題です。強外れは探索用の distance ≥ 0.01。記録数には同じ観測の別表現も含まれます。較正は元格子への既存SDSS gri → PS1 gri手順で、従来のclean格子による標準化headlineとは定義を分けています。</p>
<p class="warn">今回のnative支持監査は追加613記録に限定し、正のIVARと明示した狭い空輝マスクを使い、既存較正係数を固定しました。601記録の色を採用し、12記録の色を保留しています。その他の9,289記録は今回のnative支持監査範囲外で、従来適格7,473記録の数値を保持しています。39枚の比較画像は旧gate互換の表示を保存しており、現在保留した色をその図から採用しません。</p>
<p><a href="science_record_view.csv.gz">現行・全9,902記録 CSV</a> · <a href="science_object_view.csv">現行・全6,003天体 CSV</a> · <a href="native_quality_metrics.csv.gz">native支持・感度分析 CSV</a> · <a href="individual_review.csv">613件の実見台帳</a> · <a href="current_record_screen.csv.gz">旧gate互換 8,084記録の比較 CSV</a> · <a href="README.md">方法と限界</a> · <a href="j1323/README.md">J1323の再判定</a> · <a href="../outlier_audit/object_audit.html">前版の凍結ビュー</a></p>
<p id="load-error" role="alert"></p></section>
<section class="card"><h2>現行の色度分布と全記録</h2>
<div class="tools"><input id="search" placeholder="Gaia source ID、名前、row ID、record ID を検索" aria-label="記録を検索" disabled>
<select id="status" aria-label="状態で絞り込み" disabled><option value="all">すべての記録</option><option value="new">今回の単位追加確定613記録</option><option value="eligible">現行eligible</option><option value="strong">現行強外れ ≥ 0.01</option><option value="nativeheld">native支持・色保留12記録</option><option value="unverified">単位未確認</option><option value="recovered">以前Unavailableから単位解決115件</option></select>
<select id="kind" aria-label="観測種別" disabled><option value="all">全観測種別</option><option>SDSS</option><option>DESI</option><option>Gaia_XP</option></select><button id="reset" disabled>リセット</button></div>
<p class="muted" id="selection-count"></p><canvas id="plane" width="1200" height="630" aria-label="現在選択した記録のうちeligibleなものだけを示すCIE 1960色度図"></canvas>
<p class="muted">u/vは等しい幾何尺度。フィルター後のeligible点をすべて表示します。点または表の行を選ぶと根拠を表示します。SDSSは紫、DESIは青、Gaia XPは橙。今回追加した点は輪郭を付けています。</p>
<div class="tools"><button id="prev" disabled>前の100記録</button><span id="page-info"></span><button id="next" disabled>次の100記録</button></div>
<div class="scroll"><table><thead><tr><th>row</th><th>source ID / 名称</th><th>種別</th><th>単位の根拠</th><th>Duv</th><th>色</th><th>較正</th><th>現行状態</th></tr></thead><tbody id="rows"></tbody></table></div>
</section>
<section class="card" id="detail"><h2>記録別の根拠</h2><p id="detail-title">点または表の行を選んでください。</p><p id="detail-assessment"></p><p id="detail-quality" class="warn"></p><p id="detail-annotation" class="warn" hidden></p><p id="detail-links"></p><p id="detail-sheet-note" class="muted"></p><img id="sheet-image" hidden alt="単位追加確定後の固定比較図・現在のnative支持gateより前の表示"><details><summary>全フィールド（legacy_ / compatibility_ は現在の採用値と区別した過去・比較計算）</summary><pre id="detail-json"></pre></details></section>
<footer class="muted">埋込データはgzipで可逆圧縮しています。展開機能がないブラウザーではCSVを利用してください。画像は同じディレクトリのcontact_sheetsから読み込みます。数値データの表示に外部JavaScriptライブラリーやネットワークAPIは使いません。</footer>
<script id="payload" type="application/octet-stream" data-sha256="__DATA_SHA__">__PAYLOAD__</script>
<script>
'use strict';
let DATA=null,RECORDS=[],OBJECTS=[],BYROW=new Map(),BYENTITY=new Map(),SHEETS=new Map(),FILTERED=[],PAGE=0,PICKED=null,PLOT=[];
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const unpack=t=>{const vectors=t.vectors.map(v=>v.values??v.indices.map(i=>v.dictionary[i]));return Array.from({length:t.count},(_,row)=>Object.fromEntries(t.columns.map((key,i)=>[key,vectors[i][row]])))};
const eligible=r=>r.usable_screen===true&&r.status==='ok'&&r.flux_units_validated===true&&Number.isFinite(r.u1960)&&Number.isFinite(r.v1960);
const fmt=x=>Number.isFinite(x)?x.toFixed(6):'—';
const safeURL=s=>{try{const u=new URL(s,location.href);return ['https:','http:'].includes(u.protocol)?u.href:null}catch{return null}};
function predicate(r){const query=$('search').value.trim().toLowerCase(),status=$('status').value,kind=$('kind').value;
 if(query&&![r.source_id,r.wdid,r.entity_id,r.row_index,r.record_id].some(x=>String(x??'').toLowerCase().includes(query)))return false;
 if(kind!=='all'&&r.kind!==kind)return false;
 if(status==='new'&&!r.flux_unit_overlay_version)return false;
 if(status==='eligible'&&!eligible(r))return false;
 if(status==='strong'&&!(eligible(r)&&r.distance_planck_uv>=.01))return false;
 if(status==='unverified'&&r.status!=='unit_unverified')return false;
 if(status==='nativeheld'&&r.status!=='native_support_withheld')return false;
 if(status==='recovered'&&r.previously_unavailable_panel!==true)return false;
 return true;
}
function draw(){const canvas=$('plane'),ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;
 ctx.clearRect(0,0,W,H);const q=FILTERED.filter(eligible);
 let u0=.14,u1=.32,v0=.247,v1=.37;
 for(const r of q){u0=Math.min(u0,r.u1960-.006);u1=Math.max(u1,r.u1960+.006);v0=Math.min(v0,r.v1960-.006);v1=Math.max(v1,r.v1960+.006)}
 const scale=Math.min((W-110)/(u1-u0),(H-85)/(v1-v0)),left=65+(W-110-(u1-u0)*scale)/2,top=25+(H-85-(v1-v0)*scale)/2;
 const xy=(u,v)=>[left+(u-u0)*scale,top+(v1-v)*scale];
 ctx.strokeStyle='#dfe6e2';ctx.fillStyle='#52656e';ctx.font='12px system-ui';
 for(let u=Math.ceil(u0/.02)*.02;u<=u1;u+=.02){const [x]=xy(u,v0);ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,xy(u,v0)[1]);ctx.stroke();ctx.fillText(u.toFixed(2),x-12,xy(u,v0)[1]+19)}
 for(let v=Math.ceil(v0/.02)*.02;v<=v1;v+=.02){const [,y]=xy(u0,v);ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(xy(u1,v)[0],y);ctx.stroke();ctx.fillText(v.toFixed(2),left-38,y+4)}
 ctx.save();ctx.beginPath();ctx.rect(left,top,(u1-u0)*scale,(v1-v0)*scale);ctx.clip();ctx.strokeStyle='#253841';ctx.lineWidth=1.3;ctx.beginPath();
 DATA.planck_uv.forEach(([u,v],i)=>{const [x,y]=xy(u,v);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();
 PLOT=[];for(const r of q){const [x,y]=xy(r.u1960,r.v1960);PLOT.push({x,y,r});ctx.fillStyle=({SDSS:'#805392',DESI:'#247a9f',Gaia_XP:'#bc7d2e'}[r.kind]||'#88969d');ctx.globalAlpha=r.flux_unit_overlay_version?.8:.33;ctx.beginPath();ctx.arc(x,y,r.flux_unit_overlay_version?3:2,0,2*Math.PI);ctx.fill();if(r.flux_unit_overlay_version){ctx.globalAlpha=.8;ctx.strokeStyle='#263d48';ctx.lineWidth=.4;ctx.stroke()}}
 if(PICKED&&eligible(PICKED)){const [x,y]=xy(PICKED.u1960,PICKED.v1960);ctx.globalAlpha=1;ctx.strokeStyle='#162b34';ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,8,0,2*Math.PI);ctx.stroke()}
 ctx.restore();ctx.globalAlpha=1;ctx.fillStyle='#263e48';ctx.font='14px system-ui';ctx.fillText('CIE 1960 u',W/2-30,H-8);ctx.save();ctx.translate(17,H/2+20);ctx.rotate(-Math.PI/2);ctx.fillText('CIE 1960 v',0,0);ctx.restore();
 $('selection-count').textContent=`選択 ${FILTERED.length.toLocaleString()} 記録 / 全 ${RECORDS.length.toLocaleString()} 記録 · 図に表示できるeligible点 ${q.length.toLocaleString()} · 単位未確定とineligibleは表に保持`;
}
function renderRows(){const totalPages=Math.max(1,Math.ceil(FILTERED.length/100));PAGE=Math.min(PAGE,totalPages-1);const shown=FILTERED.slice(PAGE*100,PAGE*100+100);
 $('rows').innerHTML=shown.map(r=>`<tr data-row="${r.row_index}"><td>${r.row_index}</td><td>${esc(r.source_id)}<br>${esc(r.wdid)}</td><td>${esc(r.kind)}</td><td>${r.flux_unit_overlay_version?'追加確認 · ':''}${esc(r.flux_input_convention)}${r.flux_conversion_applied?' → Fλ':''}</td><td>${eligible(r)?fmt(r.duv):'—'}</td><td>${eligible(r)?`<span class="swatch" style="background:${/^#[0-9A-Fa-f]{6}$/.test(r.hex)?r.hex:'#fff'}"></span>${esc(r.hex)}`:'—'}</td><td>${r.calibrated?esc(r.cal_system)+' gri':'unanchored'}</td><td>${eligible(r)?'eligible':esc(r.status==='ok'?'ineligible':r.status)}</td></tr>`).join('');
 for(const row of $('rows').querySelectorAll('[data-row]'))row.addEventListener('click',()=>selectRow(Number(row.dataset.row)));
 $('page-info').textContent=`${PAGE+1} / ${totalPages} ページ`;$('prev').disabled=PAGE===0;$('next').disabled=PAGE>=totalPages-1;
}
function update(){FILTERED=RECORDS.filter(predicate);PAGE=0;draw();renderRows()}
function selectRow(index){const r=BYROW.get(index);if(!r)return;PICKED=r;const object=BYENTITY.get(r.entity_id),sheet=SHEETS.get(index);
 $('detail-title').textContent=`row ${r.row_index} · ${r.wdid} · ${r.source_id??r.entity_id}`;
 const context=DATA.classification_context?.records?.find(x=>x.row_index===r.row_index&&x.source_id===r.source_id);
 $('detail-assessment').textContent=r.science_assessment||object?.assessment||'';
 $('detail-annotation').hidden=!context;$('detail-annotation').textContent=context?'文献・原画素の追加注記（元分類は保持）： '+context.summary_ja:'';
 $('detail-quality').textContent=r.science_quality_reason||'今回のnative支持監査の対象外です。';
 const source=safeURL(r.source_url);$('detail-links').innerHTML=(source?`<a href="${esc(source)}" target="_blank" rel="noopener">元データ</a>`:'')+(sheet?` · <a href="${esc(sheet.contact_sheet)}" target="_blank">固定比較図 ${sheet.page} / panel ${sheet.panel}</a>`:'')+(context?context.links.map(link=>` · <a href="${esc(link.href)}">${esc(link.label)}</a>`).join(''):'');
 $('detail-json').textContent=JSON.stringify(r,null,2);const img=$('sheet-image');img.hidden=!sheet;
 if(sheet){$('detail-sheet-note').textContent=`実見済みの固定比較図：ページ ${sheet.page}、パネル ${sheet.panel}。40 Å表示集約とnative min/max。図中Duvは旧gate互換の値で、現在のnative支持判定より前の比較用です。特に現在保留した色や欠損を直線で結んだ区間を採用値・観測連続光と読まないでください。`;img.src=sheet.contact_sheet;img.onerror=()=>{$('detail-sheet-note').textContent+=' 画像を表示できない場合は、contact_sheetsをHTMLと同じフォルダーに置くか上の画像リンクを開いてください。';img.hidden=true}}else{$('detail-sheet-note').textContent='この記録は今回の追加613パネルの対象ではありません。過去の凍結レビューと原データを参照できます。';img.removeAttribute('src')}
 draw();
}
async function init(){try{if(typeof DecompressionStream==='undefined')throw new Error('このブラウザーはgzip展開に対応していません。上のCSVリンクをご利用ください。');
 const text=$('payload').textContent.trim(),bytes=Uint8Array.from(atob(text),c=>c.charCodeAt(0));
 const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
 DATA=JSON.parse(await new Response(stream).text());RECORDS=unpack(DATA.records);OBJECTS=unpack(DATA.objects);
 if(RECORDS.length!==9902||OBJECTS.length!==6003)throw new Error('埋込データ件数が検証済みの範囲と一致しません。CSVを利用してください。');
 BYROW=new Map(RECORDS.map(r=>[r.row_index,r]));BYENTITY=new Map(OBJECTS.map(r=>[r.entity_id,r]));SHEETS=new Map(unpack(DATA.contact_index).map(r=>[r.row_index,r]));
 $('metrics').innerHTML=`<span class="metric"><strong>${DATA.summary.current_eligible_records.toLocaleString()}</strong> 現行eligible（監査範囲を明記）</span><span class="metric"><strong>613</strong> 単位追加確定</span><span class="metric"><strong>112</strong> Unavailableから支持付き色が回復（単位解決115）</span><span class="metric"><strong>${DATA.summary.current_strong_records}</strong> 強外れ記録 / ${DATA.summary.current_strong_entities}天体</span><span class="metric"><strong>966</strong> MWDD SDSS単位保留</span>`;
 for(const id of ['search','status','kind','reset'])$(id).disabled=false;
 $('search').addEventListener('input',update);$('status').addEventListener('change',update);$('kind').addEventListener('change',update);$('reset').addEventListener('click',()=>{$('search').value='';$('status').value='all';$('kind').value='all';update()});
 $('prev').addEventListener('click',()=>{PAGE--;renderRows()});$('next').addEventListener('click',()=>{PAGE++;renderRows()});
 $('plane').addEventListener('click',e=>{const b=$('plane').getBoundingClientRect(),x=(e.clientX-b.left)*$('plane').width/b.width,y=(e.clientY-b.top)*$('plane').height/b.height;let nearest=null,d=144;for(const p of PLOT){const n=(p.x-x)**2+(p.y-y)**2;if(n<d){d=n;nearest=p.r}}if(nearest)selectRow(nearest.row_index)});
 update();
 }catch(error){$('metrics').textContent='ビューアーを展開できませんでした。';$('load-error').textContent=String(error.message||error)}}
init();
</script></html>'''


def build(*,render_plot=True):
    table=pd.read_csv(OUT/'science_record_view.csv.gz',dtype={'source_id':'string'},low_memory=False)
    objects=pd.read_csv(OUT/'science_object_view.csv',dtype={'source_id':'string'},low_memory=False)
    index=pd.read_csv(OUT/'contact_sheet_index.csv',dtype={'source_id':'string'},low_memory=False)
    summary=json.loads((OUT/'science_view_summary.json').read_text())
    annotations=classification_context(ROOT)
    byrow=table.set_index('row_index')
    for annotation in annotations['records']:
        assert byrow.loc[annotation['row_index'],'source_id']==annotation['source_id'], 'Annotation source ID mismatch'
    if render_plot:current_colour_plot(table)
    payload={'records':columnar(table),'objects':columnar(objects),'contact_index':columnar(index),
        'summary':summary,'planck_uv':c._BB_UV[::8].tolist(),
        'classification_context':annotations,
        'frozen_input_sha256':{name:sha((ROOT/f'results/screen_input_{name}.json.gz').read_bytes()) for name in ['mwdd','sdss']},
        'serialization':'Column vectors with reversible dictionaries and exact JSON numbers; CSV missing values become null, infinite endpoints are the explicit strings Infinity/-Infinity. No finite float rounding is applied.'}
    for name,frame in [('records',table),('objects',objects),('contact_index',index)]:
        expected=[{key:js_value(value) for key,value in row.items()} for row in frame.to_dict('records')]
        assert decode_columnar(payload[name])==expected, 'Lossless column codec changed a value'
    encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
    compressed=gzip.compress(encoded,compresslevel=9,mtime=0)
    assert gzip.decompress(compressed)==encoded
    text=HTML.replace('__DATA_SHA__',sha(encoded)).replace('__PAYLOAD__',base64.b64encode(compressed).decode('ascii'))
    destination=OUT/'current_view.html';destination.write_text(text)
    manifest={'records':len(table),'entities':len(objects),'full_record_fields':len(table.columns),
        'html_sha256':sha(destination.read_bytes()),'html_bytes':destination.stat().st_size,
        'decoded_json_sha256':sha(encoded),'decoded_json_bytes':len(encoded),'gzip_bytes':len(compressed),
        'codec':'gzip + base64, native DecompressionStream; clear CSV fallback',
        'lossless_gzip_roundtrip_verified':True,'finite_numeric_values_rounded':False,
        'input_sha256':{**{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [OUT/'science_record_view.csv.gz',OUT/'science_object_view.csv',OUT/'contact_sheet_index.csv',OUT/'science_view_summary.json']},**annotations['source_document_sha256']},
        'classification_annotation_rows':[r['row_index'] for r in annotations['records']],
        'science_colour_plane_sha256':sha((OUT/'science_colour_plane.png').read_bytes()),
        'complete_column_codec_equality_verified':True}
    (OUT/'current_view_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':build(render_plot='--html-only' not in sys.argv)
