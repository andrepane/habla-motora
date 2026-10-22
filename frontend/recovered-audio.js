// Storage may return an ArrayBuffer or a view (including an imported subarray).
// Copy only the visible bytes; do not decode, resample or change the original.
export function exactAudioBuffer(bytes) {
  if (bytes instanceof ArrayBuffer) return bytes;
  if (ArrayBuffer.isView(bytes))
    return new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength).slice().buffer;
  throw new TypeError('No se pudo recuperar el WAV original.');
}
