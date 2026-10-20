import { metricText } from './audio.js';
import { ProsodyState, sourceKey, identityKey, segments, edgeRegions, nearestFrame, displayTime, frameValue } from './phrase-prosody-state.js';

const labels = {
  f0_median_hz: 'F0 mediana · Hz', robust_range_st: 'Rango robusto · semitonos',
  slope_st_s: 'Tendencia global · semitonos/s', coverage_percent: 'Cobertura · %',
  f0_mean_hz: 'F0 media · Hz', f0_sd_hz: 'SD · Hz', f0_sd_st: 'SD · semitonos',
  p10_hz: 'P10 · Hz', p90_hz: 'P90 · Hz', robust_range_hz: 'Rango robusto P10–P90 · Hz',
  f0_min_hz: 'Mínimo · Hz', f0_max_hz: 'Máximo · Hz', raw_range_hz: 'Rango bruto · Hz',
  selection_duration_s: 'Duración exacta 7A · s',
};
const reasons = {
  insufficient_distributional_support: 'Soporte temporal/distribucional insuficiente',
  insufficient_temporal_support: 'Soporte temporal insuficiente',
  insufficient_defined_frames: 'Frames definidos insuficientes',
  no_defined_f0: 'Sin F0 definida', no_analysis_frames: 'Sin frames de análisis',
  praat_undefined: 'Valor indefinido en Praat', selection_unconfirmed: 'Selección 7A sin confirmar',
  insufficient_analysis_duration: 'Selección demasiado corta para el análisis',
  pitch_execution_failed: 'No se pudo completar la extracción', dependency_mismatch: 'Dependencias distintas',
  request_failed: 'No se obtuvo una respuesta de análisis',
};
const warningLabels = {
  LOW_F0_COVERAGE: 'Cobertura baja', UNDEFINED_F0_REGIONS: 'F0 indefinida y huecos',
  POSSIBLE_OCTAVE_JUMP: 'Posible salto de octava', EXTREME_DISCONTINUITY: 'Discontinuidad extrema',
  F0_NEAR_SEARCH_LIMIT: 'F0 próxima a límites de búsqueda', UPPER_FILTERED_BAND: 'F0 en la banda superior de extracción filtrada',
  POSSIBLE_DIGITAL_CLIPPING: 'Posible clipping digital', SHORT_SELECTION: 'Selección corta',
};
const statusLabels = {idle: 'Pendiente', processing: 'Procesando', completed: 'Completado',
  partial: 'Parcial', not_evaluable: 'No evaluable', failed: 'No completado', stale: 'Desactualizado'};
const ns = 'http://www.w3.org/2000/svg';
const svg = (tag, attrs = {}) => {
  const e = document.createElementNS(ns, tag);
  for (const [k,v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
};

export function mountProsody(s) {
  const state = new ProsodyState();
  const panel = document.createElement('fieldset');
  panel.className = 'prosodyPanel';
  panel.innerHTML = `<legend>8A/8B · Prosodia</legend>
    <h3>Curva de F0</h3>
    <p>Usa exactamente la selección confirmada de 7A, sin una segunda selección.</p>
    <p class="prosody-note">Medidas descriptivas de F0 sobre habla conectada. No constituyen una interpretación clínica automática.</p>
    <button type="button" data-pr="run" disabled>Analizar Prosodia sobre selección 7A</button>
    <p data-pr="state" role="status">Pendiente · Primero valida la selección confirmada de 7A.</p>
    <p data-pr="selection"></p>
    <div class="prosody-toolbar">
      <label>Unidad <select data-pr="unit"><option value="hz">Hz</option><option value="st">Semitonos</option></select></label>
      <label>Eje temporal <select data-pr="axis"><option value="seconds">Segundos</option><option value="percent">0–100 % de la selección</option></select></label>
      <button type="button" data-pr="zoomIn">Zoom +</button><button type="button" data-pr="zoomOut">Zoom −</button>
      <button type="button" data-pr="reset">Ver selección completa</button>
    </div>
    <p data-pr="reference"></p>
    <svg data-pr="chart" class="prosody-chart" viewBox="0 0 900 310" tabindex="0" role="img" aria-label="Curva temporal de F0. Usa los controles para ampliar y desplazar."></svg>
    <div class="prosody-legend"><span class="prosody-valid">F0 definida · puntos y segmentos</span><span class="prosody-gap">Sin F0</span><span class="prosody-edge">Borde sin análisis</span></div>
    <label>Desplazar vista <input data-pr="pan" type="range" min="0" max="1" step="0.001" value="0" disabled></label>
    <p data-pr="hover" class="prosody-hover" aria-live="off">Cursor: tiempo y F0 del frame real. No se interpolan huecos.</p>
    <button type="button" data-pr="play">Escuchar selección 7A</button>
    <button type="button" data-pr="playCursor" disabled>Escuchar entorno del cursor (±250 ms)</button>
    <div data-pr="primary" class="prosody-metrics"></div>
    <div data-pr="warnings" class="prosody-warnings"></div>
    <details><summary>Detalles técnicos y métricas secundarias</summary>
      <div data-pr="secondary" class="prosody-metrics"></div><p data-pr="counts"></p>
      <p>La cobertura usa los centros de frames existentes; no equivale al porcentaje de duración con análisis. El eje 0–100 % cambia solo la vista. Sin suavizado ni corrección automática de F0.</p>
      <pre data-pr="audit"></pre>
    </details>`;
  s.section.append(panel);
  const q = key => panel.querySelector(`[data-pr="${key}"]`);
  const geometry = () => q('chart').clientWidth < 600 ? {left:110,width:710} : {left:64,width:812};
  let controller = null, knownIdentity = null, identityRequest = 0;
  let view = {start: 0, end: 1}, cursor = null;
  const currentSource = () => s.state.contextResult;
  const duration = () => state.result?.metrics?.selection_duration_s?.value ??
    (state.result?.context?.selection && s.wav ?
      (state.result.context.selection.end_sample_exclusive-state.result.context.selection.start_sample)/s.wav.rate : 0);
  const visibleFrames = () => ['completed','partial','not_evaluable'].includes(state.status) && Array.isArray(state.result?.frames) ? state.result.frames : [];
  const exportView = () => ({unit: q('unit').value, time_axis: q('axis').value,
    viewport_seconds: {...view}, smoothing: false, interpolation: false});
  const exported = () => state.exported(exportView());
  function audit() { q('audit').textContent = JSON.stringify(exported(), null, 2); }
  function ready() {
    const source = currentSource();
    return !!(s.file && source?.context.selection_confirmed && source?.context.selection);
  }
  function invalidate(reason) {
    s.profileBridge?.invalidate(['prosody'], reason, s.id);
    controller?.abort(); identityRequest++; state.invalidate(reason); cursor = null;
    s.q('.audio').pause();
    render();
  }
  async function checkIdentity() {
    if (!state.result || !knownIdentity || state.status === 'processing') return;
    const request = ++identityRequest;
    try {
      const response = await fetch('/phrase-prosody-protocol', {cache: 'no-store'});
      if (!response.ok) throw Error('protocol');
      const p = await response.json();
      if (request !== identityRequest) return;
      if (identityKey(p) !== knownIdentity || p.phrase_config_sha256 !== currentSource()?.provenance.config_sha256)
        invalidate('configuration_engine_or_phrase_version_changed');
    } catch {
      if (request === identityRequest) invalidate('identity_unavailable');
    }
  }
  function metricCard(key, m) {
    const card = document.createElement('div'); card.className = 'metric'; card.dataset.metric = key;
    const label = document.createElement('span'), value = document.createElement('strong'), note = document.createElement('small');
    label.textContent = labels[key] ?? key;
    value.textContent = key === 'selection_duration_s' && Number.isFinite(m?.value) ? m.value.toFixed(6).replace('.', ',') : metricText(m);
    note.textContent = m?.reason ? `${reasons[m.reason] ?? m.reason} · ${m.reason}` : '';
    card.append(label, value, note); return card;
  }
  function render() {
    panel.dataset.status = state.status;
    q('state').textContent = `${statusLabels[state.status] ?? state.status}${state.reason ? ' · '+(reasons[state.reason] ?? state.reason) : ''}`;
    q('run').disabled = !ready() || state.status === 'processing';
    if (state.status === 'idle') q('state').textContent += ready() ? ' · Selección 7A validada. Lista para analizar.' : ' · Primero valida la selección confirmada de 7A.';
    for (const key of ['primary','secondary','warnings']) q(key).replaceChildren();
    const r = state.result;
    const showMetrics = r && ['completed','partial','not_evaluable'].includes(state.status);
    const selectionContext = r?.context ?? (ready() ? currentSource().context : null);
    const selection = selectionContext?.selection;
    q('selection').textContent = selection ? `Selección 7A: [${selection.start_sample}, ${selection.end_sample_exclusive}) muestras · intento ${selectionContext.attempt} · ${selectionContext.modality}` : '';
    q('counts').textContent = r?.counts?.total !== null && r?.counts?.total !== undefined
      ? `Frames totales: ${r.counts.total} · definidos: ${r.counts.defined} · indefinidos: ${r.counts.undefined}` : '';
    const reference = r?.reference_st?.value_hz;
    q('reference').textContent = Number.isFinite(reference)
      ? `Referencia de semitonos: mediana nativa de esta selección = ${reference.toFixed(6)} Hz · 0 ST. Tiempo relativo al inicio de 7A.`
      : 'Referencia de semitonos: no disponible hasta disponer de mediana nativa. Tiempo relativo al inicio de 7A.';
    q('unit').querySelector('[value="st"]').disabled = !Number.isFinite(reference);
    if (!Number.isFinite(reference) && q('unit').value === 'st') q('unit').value = 'hz';
    if (showMetrics) {
      for (const [key,m] of Object.entries(r.metrics)) {
        const main = ['f0_median_hz','robust_range_st','slope_st_s','coverage_percent'].includes(key);
        q(main ? 'primary' : 'secondary').append(metricCard(key,m));
      }
      const warnings = r.warnings ?? [];
      const missing = Object.entries(r.metrics).filter(([,m]) => m.value === null && m.reason);
      if (warnings.length || missing.length) {
        const heading = document.createElement('h4'); heading.textContent = 'Advertencia técnica'; q('warnings').append(heading);
        const list = document.createElement('ul');
        for (const w of warnings) {
          const item = document.createElement('li'); item.dataset.code = w.code;
          item.textContent = `${warningLabels[w.code] ?? w.code} · ${w.code}`;
          if (w.delta_t_s !== undefined) item.textContent += ` · Δt ${w.delta_t_s.toFixed(6)} s · ${w.delta_st.toFixed(3)} ST · ${w.direction}`;
          if (w.max_internal_s !== undefined) item.textContent += ` · hueco interior máximo ${w.max_internal_s.toFixed(3)} s`;
          if (w.rail_samples !== undefined) item.textContent += ` · ${w.rail_samples} muestras en límite digital`;
          list.append(item);
        }
        for (const [key,m] of missing) {
          const item = document.createElement('li');
          item.textContent = `${labels[key]}: ${reasons[m.reason] ?? m.reason} · ${m.reason}`; list.append(item);
        }
        q('warnings').append(list);
      }
    }
    q('play').disabled = !showMetrics;
    q('playCursor').disabled = !showMetrics || cursor === null;
    draw(); audit();
  }
  function draw() {
    const chart = q('chart'), frames = visibleFrames(), d = duration(); chart.replaceChildren();
    chart.dataset.pointCount = '0';
    q('pan').disabled = !frames.length || view.end-view.start >= d;
    if (!frames.length || !(d > 0)) {
      const text = svg('text', {x: 40, y: 145, fill: '#546f76'});
      text.textContent = state.status === 'stale' ? 'Curva desactualizada · vuelve a analizar la selección 7A.' : 'La curva aparecerá tras el análisis de la selección 7A.';
      chart.append(text); return;
    }
    const hop = state.result.configuration.profile.hop_s;
    const unit = q('unit').value, axis = q('axis').value;
    const runs = segments(frames, unit, hop);
    const values = runs.flat().filter(p=>p.frame.time_relative_s >= view.start && p.frame.time_relative_s <= view.end).map(p=>p.value);
    let low = values.length ? Math.min(...values) : 0, high = values.length ? Math.max(...values) : 1;
    const padding = Math.max((high-low)*.12, unit === 'hz' ? 1 : .1); low -= padding; high += padding;
    const {left,width} = geometry();
    const X = t => left+(t-view.start)/(view.end-view.start)*width;
    const Y = y => 260-(y-low)/(high-low)*238;
    chart.append(svg('rect',{x:left,y:22,width,height:238,fill:'#fafcfc'}));
    const regions = [...edgeRegions(frames,d,hop), ...(state.result.gaps ?? []).map(g=>({...g,kind:'gap'}))];
    for (const region of regions) {
      const a=Math.max(view.start,region.start_s), b=Math.min(view.end,region.end_s);
      if (b<=a) continue;
      const rect=svg('rect',{x:X(a),y:22,width:X(b)-X(a),height:238,fill:region.kind==='edge'?'#ccd6db':'#fae8c5'});
      rect.dataset.region=region.kind; const title=svg('title');
      title.textContent=`${region.kind==='edge'?'Borde sin análisis':'Sin F0'}: ${region.start_s.toFixed(6)}–${region.end_s.toFixed(6)} s`;
      rect.append(title); chart.append(rect);
    }
    for (let i=0;i<=4;i++) {
      const t=view.start+(view.end-view.start)*i/4, v=low+(high-low)*i/4;
      chart.append(svg('line',{x1:left,x2:left+width,y1:Y(v),y2:Y(v),stroke:'#dce6e9'}));
      if (values.length) {
        const y=svg('text',{x:left-7,y:Y(v)+4,'text-anchor':'end'}); y.textContent=v.toFixed(unit==='hz'?1:2); chart.append(y);
      }
      const x=svg('text',{x:X(t),y:284,'text-anchor':'middle'}); x.textContent=displayTime(t,d,axis).toFixed(2)+(axis==='percent'?' %':' s'); chart.append(x);
    }
    const ylabel=svg('text',{x:left,y:14}); ylabel.textContent=unit==='st'?'Semitonos · referencia: mediana nativa':'F0 · Hz'; chart.append(ylabel);
    if (!values.length) {
      const empty=svg('text',{x:450,y:145,'text-anchor':'middle'});empty.textContent='Sin F0 definida en esta vista';chart.append(empty);
    }
    const allVisible=[];
    for (const run of runs) {
      const points=run.filter(p=>p.frame.time_relative_s>=view.start && p.frame.time_relative_s<=view.end);
      if (!points.length) continue;
      const line=svg('polyline',{points:points.map(p=>`${X(p.frame.time_relative_s)},${Y(p.value)}`).join(' '),fill:'none',stroke:'#086b76','stroke-width':1.8});
      line.dataset.f0Segment='true'; chart.append(line);
      for (const p of points) {
        const point=svg('circle',{cx:X(p.frame.time_relative_s),cy:Y(p.value),r:1.7,fill:'#086b76'});
        point.dataset.frame=p.frame.frame_index; point.dataset.value=p.value; point.dataset.time=p.frame.time_relative_s;
        chart.append(point); allVisible.push(p);
      }
    }
    chart.dataset.unit=unit; chart.dataset.axis=axis;
    chart.dataset.viewStart=view.start; chart.dataset.viewEnd=view.end;
    chart.dataset.pointCount=allVisible.length;
    if (cursor !== null && cursor>=view.start && cursor<=view.end)
      chart.append(svg('line',{x1:X(cursor),x2:X(cursor),y1:22,y2:260,stroke:'#a56522','stroke-dasharray':'4 3','data-cursor':'true'}));
  }
  function chartTime(event) {
    const rect=q('chart').getBoundingClientRect();
    const pos=(event.clientX-rect.left)/rect.width*900;
    const {left,width}=geometry();
    return Math.max(view.start,Math.min(view.end,view.start+(pos-left)/width*(view.end-view.start)));
  }
  q('chart').onpointermove = event => {
    const frames=visibleFrames(); if (!frames.length) return;
    const time=chartTime(event), hop=state.result.configuration.profile.hop_s;
    const frame=nearestFrame(frames,time,hop); cursor=frame?.time_relative_s ?? time;
    const t=displayTime(cursor,duration(),q('axis').value);
    const v=frame ? frameValue(frame,q('unit').value) : null;
    q('hover').textContent=`${t.toFixed(6)} ${q('axis').value==='percent'?'%':'s'} · ${v===null?(frame?'F0 indefinida · '+frame.undefined_reason:'Borde sin análisis'):v.toFixed(6)+' '+(q('unit').value==='st'?'ST':'Hz')}${frame ? ' · frame '+frame.frame_index+' · WAV '+frame.time_absolute_s.toFixed(6)+' s' : ''}`;
    q('playCursor').disabled=false;
    // Cursor alone updates; the acoustic point set remains untouched.
    q('chart').querySelector('[data-cursor]')?.remove();
    const {left,width}=geometry();
    const x=left+(cursor-view.start)/(view.end-view.start)*width;
    q('chart').append(svg('line',{x1:x,x2:x,y1:22,y2:260,stroke:'#a56522','stroke-dasharray':'4 3','data-cursor':'true'}));
  };
  q('chart').onpointerdown = event => q('chart').onpointermove(event);
  function zoom(factor, anchor=cursor ?? (view.start+view.end)/2) {
    const d=duration(); if (!visibleFrames().length) return;
    const span=Math.min(d,Math.max(.05,(view.end-view.start)*factor));
    const start=Math.max(0,Math.min(d-span,anchor-span/2)); view={start,end:start+span};
    q('pan').value=d>span?start/(d-span):0; draw(); audit();
  }
  q('zoomIn').onclick=()=>zoom(.5); q('zoomOut').onclick=()=>zoom(2);
  q('reset').onclick=()=>{view={start:0,end:duration()};q('pan').value=0;draw();audit();};
  q('pan').oninput=()=>{
    const span=view.end-view.start, start=Number(q('pan').value)*(duration()-span);
    view={start,end:start+span};draw();audit();
  };
  q('chart').addEventListener('wheel',event=>{
    if (!visibleFrames().length) return;
    event.preventDefault();zoom(event.deltaY>0?1.25:.8,chartTime(event));
  },{passive:false});
  for (const key of ['unit','axis']) q(key).onchange=()=>{draw();audit();};
  function play(a,b) {
    if (!state.result || state.status==='stale') return;
    const audio=s.q('.audio'); audio.currentTime=a;
    audio.ontimeupdate=()=>{if(audio.currentTime>=b){audio.pause();audio.ontimeupdate=null;}};
    audio.play().catch(()=>{q('hover').textContent='No se pudo iniciar la reproducción.';});
  }
  q('play').onclick=()=>{
    const sel=state.result.context.selection;play(sel.start_sample/s.wav.rate,sel.end_sample_exclusive/s.wav.rate);
  };
  q('playCursor').onclick=()=>{
    if (cursor===null) return;
    const sel=state.result.context.selection, start=sel.start_sample/s.wav.rate;
    play(Math.max(start,start+cursor-.25),Math.min(sel.end_sample_exclusive/s.wav.rate,start+cursor+.25));
  };
  q('run').onclick=async()=>{
    if (!ready()) return;
    controller?.abort(); controller=new AbortController(); const signal=controller.signal;
    const source=structuredClone(currentSource()), file=s.file, key=sourceKey(source);
    const revision=state.begin(key); cursor=null; render();
    let requestedProtocol=null, requestedDependencies=null;
    try {
      const response=await fetch('/phrase-prosody-protocol',{signal,cache:'no-store'});
      if (!response.ok) throw Error('Identidad congelada no disponible.');
      const protocol=await response.json();
      requestedProtocol=protocol;
      if (revision!==state.revision || sourceKey(currentSource())!==key) return;
      if (protocol.phrase_config_sha256!==source.provenance.config_sha256) {
        invalidate('phrase_version_changed_revalidate_7a');return;
      }
      knownIdentity=identityKey(protocol);
      const selection=source.context.selection;
      const text=JSON.stringify({end_sample_exclusive:selection.end_sample_exclusive,start_sample:selection.start_sample});
      const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
      const selectionHash=Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
      const deps={file_sha256:source.provenance.file_sha256,context_sha256:source.provenance.context_sha256,
        selection_sha256:selectionHash,config_sha256:protocol.config_sha256,engine_sha256:protocol.engine_sha256};
      requestedDependencies=deps;
      const form=new FormData();form.append('file',file);form.append('context_json',JSON.stringify(source.context));
      form.append('expected_dependencies_json',JSON.stringify(deps));
      const result=await fetch('/phrase-prosody-analysis',{method:'POST',body:form,signal});
      const body=await result.json();
      if (!result.ok) throw Error(typeof body.detail==='string'?body.detail:'No se pudo completar Prosodia.');
      if (state.accept(body,revision,sourceKey(currentSource()))) {
        s.profileBridge?.save('prosody', body, file, s.capture, null, s.id);
        view={start:0,end:duration()};q('pan').value=0;render();
      }
    } catch(e) {
      if (e.name!=='AbortError' && revision===state.revision) {
        s.profileBridge?.failed('prosody', e.message, s.id);
        state.accept({status:'failed',reason:e.message,context:source.context,
          identity:requestedProtocol,dependencies:requestedDependencies,
          configuration:requestedProtocol?.configuration ?? null,
          protocol_version:requestedProtocol?.protocol_version ?? null,
          integration_version:requestedProtocol?.integration_version ?? null,
          metrics:Object.fromEntries(Object.keys(labels).map(k=>[k,{value:null,reason:'request_failed'}])),
          frames:null,counts:null,gaps:[],warnings:[],reference_st:{type:'selection_native_median_hz',value_hz:null,reason:'request_failed'},
          runtime:{praat_version:null,reason:'response_unavailable'}},revision,sourceKey(currentSource()));render();
      }
    }
  };
  window.addEventListener('focus',checkIdentity);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkIdentity();});
  let chartWidth=0;
  new ResizeObserver(()=>{
    const width=q('chart').clientWidth;
    if(width!==chartWidth){chartWidth=width;draw();}
  }).observe(q('chart'));
  render();
  return {invalidate,exported,checkIdentity,sourceUpdated(){
    if (state.source && state.source!==sourceKey(currentSource())) invalidate('7A:context_changed');
    if (state.status==='idle') render();
    q('run').disabled=!ready() || state.status==='processing';
  }};
}
