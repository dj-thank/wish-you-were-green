'use strict';
// Static/native-JavaScript functional check, without a browser or network.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const payload=html.match(/<script id="payload"[^>]*>([\s\S]*?)<\/script>/)[1].trim();
const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
new vm.Script(script); // Parse every handler, including paths not selected below.
const elements=new Map(),ctx=new Proxy({}, {get:(target,key)=>target[key]??(()=>{})});
function element(id){if(!elements.has(id))elements.set(id,{value:id==='status'||id==='kind'?'all':'',
 textContent:id==='payload'?payload:'',innerHTML:'',width:1200,height:630,disabled:true,hidden:true,
 getContext:()=>ctx,querySelectorAll:()=>[],addEventListener:()=>{},removeAttribute:()=>{},
 getBoundingClientRect:()=>({left:0,top:0,width:1200,height:630})});return elements.get(id)}
const sandbox={document:{getElementById:element},location:{href:'file:///tmp/current_view.html'},
 console,DecompressionStream,Blob,Response,Uint8Array,atob,URL,setTimeout,clearTimeout};
vm.createContext(sandbox);
vm.runInContext(script.replace(/init\(\);\s*$/,'globalThis.__initPromise=init();'),sandbox);
(async()=>{await sandbox.__initPromise;
 assert.equal(element('load-error').textContent,'');
 const evaluate=code=>vm.runInContext(code,sandbox);
 assert.equal(evaluate('RECORDS.length'),9902);assert.equal(evaluate('OBJECTS.length'),6003);
 assert.equal(evaluate('RECORDS.filter(eligible).length'),8074);
 assert.equal(evaluate('RECORDS.filter(r=>r.flux_unit_overlay_version).length'),613);
 assert.equal(evaluate('RECORDS.every(r=>r.source_id===null||typeof r.source_id==="string")'),true);
 evaluate("$('status').value='nativeheld';update()");assert.equal(evaluate('FILTERED.length'),12);
 evaluate("$('status').value='recovered';update()");assert.equal(evaluate('FILTERED.length'),115);
 evaluate("$('status').value='all';update();selectRow(8295)");
 assert.equal(evaluate('eligible(PICKED)'),false);assert.equal(evaluate('PICKED.hex'),null);
 assert.match(element('detail-quality').textContent,/coverage gate/);
 assert.match(element('detail-sheet-note').textContent,/旧gate互換/);
 evaluate('selectRow(13)');assert.equal(evaluate('eligible(PICKED)'),true);
 assert.match(element('detail-assessment').textContent,/precision|precise|low SNR/);
 const annotationCases=[
  {row:6462,source:'767756877680612864',preserved:'DQ:',note:/AM CVn/,links:['root_targeted/README.md']},
  {row:7607,source:'4518692348609283712',preserved:'DAZH',note:/同じSDSS観測に DAZH/,links:['targeted_followup/README.md','targeted_followup/native_row_7607.png']},
  {row:8019,source:'2780975896637670528',preserved:'DZ',note:/カタログ分類の食い違い.*QSO\/BROADLINE.*AGN \/ VARIABLE/,links:['targeted_followup/README.md','targeted_followup/native_row_8019.png']},
  {row:7930,source:'3217759570831525120',preserved:'DBZAe',note:/6565\.98795.*AND・ORの双方にBADSKYCHI/,links:['targeted_followup/README.md','targeted_followup/native_row_7930.png']},
  {row:5827,source:'1242828982729309952',preserved:'DZ:',note:/ローカル確認のみ.*STAR\/CV.*6550\.88409/,links:['targeted_followup/README.md','targeted_followup/native_row_5827.png','targeted_followup/local_row_5827.json']}
 ];
 assert.equal(evaluate('DATA.classification_context.records.length'),annotationCases.length);
 for(const item of annotationCases){
  const original=evaluate(`JSON.stringify(BYROW.get(${item.row}),null,2)`);
  evaluate(`selectRow(${item.row})`);
  assert.equal(evaluate('PICKED.source_id'),item.source);
  assert.equal(evaluate(`DATA.classification_context.records.find(r=>r.row_index===${item.row}).source_id`),item.source);
  assert.equal(evaluate(`DATA.classification_context.records.find(r=>r.row_index===${item.row}).preserved_catalogue_spectype`),item.preserved);
  assert.equal(element('detail-annotation').hidden,false);
  assert.match(element('detail-annotation').textContent,item.note);
  assert.ok(element('detail-title').textContent.includes(item.source));
  for(const href of item.links)assert.ok(element('detail-links').innerHTML.includes(`href="${href}"`),`${item.row}: ${href}`);
  assert.equal(element('detail-json').textContent,original,'Annotation must not mutate original record fields');
  assert.equal(evaluate(`JSON.stringify(BYROW.get(${item.row}),null,2)`),original);
 }
 assert.match(element('detail-annotation').textContent,/新しい文献・Gaia・位置の検証はしていません/);
 evaluate('selectRow(13)');assert.equal(element('detail-annotation').hidden,true);
 assert.equal(element('detail-annotation').textContent,'');
 assert.doesNotMatch(element('detail-links').innerHTML,/targeted_followup\/|root_targeted\//);
 evaluate("$('search').value='3638333660492606976';update()");
 assert.equal(evaluate('FILTERED.length'),2);
 console.log(JSON.stringify({status:'PASS',records:9902,entities:6003,eligible:8074,
     native_colour_withheld:12,new_unit_records:613,source_ids_preserved_as_strings:true,
     classification_overlay_present:true,classification_annotation_rows_checked:annotationCases.length,
     annotation_source_ids_and_original_fields_verified:true,
     validation:'Node native decompression, data decoding, filtering and handlers; no browser rendering claim'}));
})().catch(error=>{console.error(error);process.exitCode=1});
