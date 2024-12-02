// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

class Player {
  playbackNode = null;

  async init(sampleRate) {
    const audioContext = new AudioContext({ sampleRate });
    await audioContext.audioWorklet.addModule("static/playback-worklet.js");

    this.playbackNode = new AudioWorkletNode(audioContext, "playback-worklet");
    this.playbackNode.connect(audioContext.destination);
  }

  play(buffer) {
    if (this.playbackNode) {
      this.playbackNode.port.postMessage(buffer);
    }
  }

  clear() {
    if (this.playbackNode) {
      this.playbackNode.port.postMessage(null);
    }
  }
}
