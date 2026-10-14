import { REQUESTED, encodeWav } from "./audio.js";
// Reuses the existing PCM AudioWorklet and WAV encoder, with bounded DDK capture.
export class DdkRecorder {
  constructor(onProgress) {
    this.onProgress = onProgress;
    this.active = null;
  }
  async dispose(rec) {
    rec.node?.disconnect();
    rec.source?.disconnect();
    rec.stream?.getTracks().forEach((t) => t.stop());
    if (rec.ctx && rec.ctx.state !== "closed") await rec.ctx.close();
  }
  async start() {
    const rec = { chunks: [], count: 0, stopping: false };
    this.active = rec;
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode)
        throw Error("Grabación requiere localhost/HTTPS y Web Audio.");
      rec.stream = await navigator.mediaDevices.getUserMedia({
        audio: REQUESTED,
      });
      if (this.active !== rec) {
        await this.dispose(rec);
        return false;
      }
      rec.ctx = new AudioContext();
      if (![44100, 48000].includes(rec.ctx.sampleRate))
        throw Error("Frecuencia incompatible; sube un WAV válido.");
      rec.capture = {
        requested_constraints: REQUESTED,
        track_settings: rec.stream.getAudioTracks()[0].getSettings(),
        track_constraints: rec.stream.getAudioTracks()[0].getConstraints(),
        audio_context_sample_rate: rec.ctx.sampleRate,
        encoding: "mono PCM16",
        channel_policy: "first_channel_only",
        observed_input_channels: [],
      };
      await rec.ctx.audioWorklet.addModule("/static/recorder-worklet.js");
      if (this.active !== rec) {
        await this.dispose(rec);
        return false;
      }
      rec.source = rec.ctx.createMediaStreamSource(rec.stream);
      rec.node = new AudioWorkletNode(rec.ctx, "pcm-recorder");
      rec.node.port.onmessage = ({ data }) => {
        if (this.active !== rec || rec.stopping) return;
        const room = Math.max(
          0,
          Math.floor(15 * rec.ctx.sampleRate) - rec.count,
        );
        const chunk = data.samples.slice(0, room);
        rec.chunks.push(chunk);
        rec.count += chunk.length;
        if (!rec.capture.observed_input_channels.includes(data.channels))
          rec.capture.observed_input_channels.push(data.channels);
        this.onProgress(rec.count / rec.ctx.sampleRate);
      };
      rec.source.connect(rec.node);
      rec.node.connect(rec.ctx.destination);
      await rec.ctx.resume();
      if (this.active !== rec) {
        await this.dispose(rec);
        return false;
      }
      return true;
    } catch (e) {
      const current = this.active === rec;
      if (current) this.active = null;
      await this.dispose(rec);
      if (current) throw e;
      return false;
    }
  }
  async stop() {
    const rec = this.active;
    if (!rec || rec.stopping) return null;
    rec.stopping = true;
    this.active = null;
    const rate = rec.ctx?.sampleRate;
    await this.dispose(rec);
    if (!rec.count) return null;
    const samples = new Float32Array(rec.count);
    let at = 0;
    for (const chunk of rec.chunks) {
      samples.set(chunk, at);
      at += chunk.length;
    }
    return {
      file: new File([encodeWav(samples, rate)], "ddk.wav", {
        type: "audio/wav",
      }),
      capture: rec.capture,
    };
  }
}
