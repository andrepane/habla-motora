// Display adapters only. Original values, reasons and exports are never rewritten.
export const reasonLabels={
 insufficient_intervals:'No hay suficientes intervalos para calcular esta medida',
 no_intervals:'No hay intervalos disponibles',
 insufficient_distributional_support:'No hay suficiente distribución temporal para calcular esta medida',
 insufficient_temporal_support:'No hay suficiente duración con F0 definida para calcular esta medida',
 review_pending:'Revisión pendiente',no_evidence:'Sin evidencia suficiente',
 no_groups:'No hay ciclos completos disponibles',praat_undefined:'Praat no pudo calcular esta medida',
 f0_not_detected:'No se detectó F0',insufficient_voiced_frames:'No hay suficientes frames con F0 definida',
 representative_attempt_not_selected:'Falta elegir explícitamente un intento para el Perfil',
};
export const displayReason=reason=>reasonLabels[reason]??reason;
export function displayUnit(unit,label=''){
 if(unit!=='count')return unit;
 return /sílabas/i.test(label)?'sílabas':/ciclos/i.test(label)?'ciclos':/pausas/i.test(label)?'pausas':'recuento';
}
export const secondsAt=(index,rate)=>Number.isInteger(index)&&Number.isFinite(rate)&&rate>0?index/rate:null;
export const sampleAtSeconds=(seconds,rate)=>Number.isFinite(seconds)&&seconds>=0&&Number.isFinite(rate)&&rate>0?Math.round(seconds*rate):null;
export function importMessage(error,data){
 return data?.schema_version==='motor_speech_profile_v1'&&error.message==='Paquete no compatible.'
 ? 'Este archivo parece ser un resumen de resultados. Para recuperar y continuar la evaluación necesitas la copia completa recuperable. Se obtiene en Perfil → Copia completa para recuperar esta evaluación.'
 : error.message;
}
export function pauseDisplay(audit){
 const status=audit?.current_response?.temporal_review?.status;
 if(status==='confirmed')return 'Resultado confirmado. Sin cambios posteriores pendientes.';
 if(status==='not_evaluable')return 'Revisión no evaluable. Consulta el motivo y las medidas disponibles.';
 if(audit?.history?.some(h=>(h.response??h.result)?.temporal_review?.status==='confirmed'))return 'Cambios pendientes posteriores al resultado confirmado. Este borrador todavía no está confirmado.';
 return 'Borrador de revisión: aún no confirmado.';
}
