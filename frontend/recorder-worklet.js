class PCMRecorder extends AudioWorkletProcessor {
  process(inputs) {
    const channels = inputs[0];
    if (channels?.length)
      this.port.postMessage({
        samples: channels[0].slice(),
        channels: channels.length,
      });
    return true;
  }
}
registerProcessor("pcm-recorder", PCMRecorder);
