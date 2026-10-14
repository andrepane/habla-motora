// Small real HTTP check for the exact Preview; synthetic events, no human speech.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const base=process.env.BASE_URL;
if(!base)throw Error('BASE_URL is required.');
const wav=fs.readFileSync(process.env.DDK_TEST_WAV||'/tmp/ddk-clean.wav');
let checks=0;const check=v=>{assert.ok(v);checks++;};
async function post(buffer=wav,fields={}){const f=new FormData();f.append('file',new Blob([buffer],{type:'audio/wav'}),'synthetic.wav');for(const[k,v]of Object.entries(fields))f.append(k,String(v));const r=await fetch(base+'/ddk-analysis',{method:'POST',body:f});return {status:r.status,body:await r.json()};}
check((await fetch(base+'/health')).status===200);
const html=(await (await fetch(base+'/ddk')).text()).replace(/\s+/g,' ');check(html.includes('DDK')&&html.includes('habla humana pendiente'));
check((await fetch(base+'/static/ddk.js')).status===200);
const r=await post();check(r.status===200);check(r.body.provenance.file_sha256===createHash('sha256').update(wav).digest('hex'));
check(r.body.automatic_original.detection.events.length===21);check(r.body.validation.phonetic_recognition===false);check(r.body.reviewed_result===null);
const anchor=r.body.automatic_original.detection.events[0].id;
const g=await post(wav,{anchor_id:anchor});check(g.body.automatic_original.metrics.group_count.value===7);
const operations=r.body.automatic_original.detection.events.map((e,i)=>({action:'label',id:e.id,label:['pa','ta','ka'][i%3]}));
const reviewed=await post(wav,{anchor_id:anchor,review_json:JSON.stringify({operations,confirmed:true}),expected_file_sha256:r.body.provenance.file_sha256});
check(reviewed.status===200);check(reviewed.body.reviewed_result.metrics.group_count.value===7);
check(JSON.stringify(reviewed.body.automatic_original.detection)===JSON.stringify(r.body.automatic_original.detection));
check((await post(Buffer.from('bad'))).status===422);
check((await post(wav,{review_json:'{}',expected_file_sha256:'wrong'})).status===422);
check((await post(Buffer.alloc(4000001))).status===413);
const silence=Buffer.from(wav);silence.fill(0,44);const empty=await post(silence);
check(empty.status===200&&empty.body.stages.detection.status==='empty');check(empty.body.automatic_original.metrics.event_rate_per_s.value===null);
console.log(JSON.stringify({preview:base,checks,file_sha256:r.body.provenance.file_sha256,configuration_sha256:r.body.provenance.configuration_sha256,status:'passed',note:'Synthetic HTTP integration only; not speech validation.'},null,2));
