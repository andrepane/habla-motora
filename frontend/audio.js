export const MAX_BYTES = 10 * 1024 * 1024;
export const REQUESTED = {
  channelCount: 1,
  echoCancellation: false,
  noiseSuppression: false,
  autoGainControl: false,
};
export function parseWav(buffer) {
  const v = new DataView(buffer),
    str = (p, n) => String.fromCharCode(...new Uint8Array(buffer, p, n));
  if (
    buffer.byteLength > MAX_BYTES ||
    buffer.byteLength < 44 ||
    str(0, 4) !== "RIFF" ||
    str(8, 4) !== "WAVE"
  )
    throw Error("Archivo WAV inválido o superior a 10 MiB.");
  let fmt = null,
    data = null;
  for (let p = 12; p + 8 <= buffer.byteLength; ) {
    const id = str(p, 4),
      size = v.getUint32(p + 4, true),
      at = p + 8;
    if (at + size > buffer.byteLength) throw Error("WAV truncado.");
    if (id === "fmt " && size >= 16)
      fmt = {
        format: v.getUint16(at, true),
        channels: v.getUint16(at + 2, true),
        rate: v.getUint32(at + 4, true),
        align: v.getUint16(at + 12, true),
        bits: v.getUint16(at + 14, true),
      };
    if (id === "data" && !data) data = { at, size };
    p = at + size + (size % 2);
  }
  if (
    !fmt ||
    !data ||
    fmt.format !== 1 ||
    fmt.channels !== 1 ||
    ![16, 24, 32].includes(fmt.bits) ||
    ![44100, 48000].includes(fmt.rate) ||
    fmt.align !== fmt.bits / 8 ||
    !data.size ||
    data.size % fmt.align
  )
    throw Error(
      "Se necesita WAV mono PCM 16/24/32 bits a 44.100 o 48.000 Hz. No se convierte el archivo.",
    );
  const samples = new Float32Array(data.size / fmt.align);
  for (let i = 0; i < samples.length; i++) {
    const p = data.at + i * fmt.align;
    let x;
    if (fmt.bits === 16) x = v.getInt16(p, true);
    else if (fmt.bits === 32) x = v.getInt32(p, true);
    else {
      x = v.getUint8(p) | (v.getUint8(p + 1) << 8) | (v.getUint8(p + 2) << 16);
      if (x & 0x800000) x -= 0x1000000;
    }
    samples[i] = x / 2 ** (fmt.bits - 1);
  }
  return {
    samples,
    rate: fmt.rate,
    bits: fmt.bits,
    duration: samples.length / fmt.rate,
  };
}
export function encodeWav(samples, rate) {
  if (![44100, 48000].includes(rate))
    throw Error("Frecuencia de captura incompatible; no se remuestrea.");
  const buffer = new ArrayBuffer(44 + samples.length * 2),
    v = new DataView(buffer);
  const s = (p, x) =>
    [...x].forEach((c, i) => v.setUint8(p + i, c.charCodeAt(0)));
  s(0, "RIFF");
  v.setUint32(4, 36 + samples.length * 2, true);
  s(8, "WAVE");
  s(12, "fmt ");
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true);
  v.setUint16(22, 1, true);
  v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  s(36, "data");
  v.setUint32(40, samples.length * 2, true);
  samples.forEach((x, i) =>
    v.setInt16(
      44 + i * 2,
      Math.round(Math.max(-1, Math.min(1, x)) * (x < 0 ? 32768 : 32767)),
      true,
    ),
  );
  return buffer;
}
export function centralInterval(start, end, duration) {
  if (
    !Number.isFinite(start) ||
    !Number.isFinite(end) ||
    start < 0 ||
    end > duration ||
    end - start < 3
  )
    return null;
  const mid = (start + end) / 2;
  return { start_s: mid - 1.5, end_s: mid + 1.5 };
}
export function metricText(metric) {
  const value = metric?.value;
  if (value === null || value === undefined) return "No calculable";
  if (value !== 0 && Math.abs(value) < 0.001)
    return value.toExponential(2).replace(".", ",");
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits: 3 }).format(
    value,
  );
}
