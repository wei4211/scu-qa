function connectVoice(input, status, button, enabled) {
  const limits = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"];
  const format = window.MediaRecorder && limits.find(type => MediaRecorder.isTypeSupported(type));
  const elapsed = document.getElementById("voice-timer");
  const recordingLimit = 30;
  let recorder;
  let timer;
  let activeStream;
  let attempt = 0;
  let state = "idle";

  function update(next, notice) {
    state = next;
    const recording = state === "recording";
    button.setAttribute("aria-pressed", String(recording));
    button.setAttribute("aria-label", recording ? UI.voice_stop : UI.voice_start);
    button.disabled = state === "starting" || state === "transcribing";
    status.textContent = notice;
    elapsed.hidden = !recording;
  }

  if (!enabled || !format || !navigator.mediaDevices?.getUserMedia) {
    button.disabled = true;
    button.title = !enabled
      ? UI.voice_disabled
      : UI.voice_unsupported;
    return () => {};
  }

  function release() {
    clearInterval(timer);
    activeStream?.getTracks().forEach(track => track.stop());
    activeStream = undefined;
  }

  async function sendAudio(blob, id) {
    release();
    if (!blob.size) {
      update("idle", UI.voice_empty);
      return;
    }
    update("transcribing", UI.voice_transcribing);
    try {
      const data = new FormData();
      data.append("audio", blob, "recording");
      data.append("lang", UI.lang);
      const response = await fetch("/api/transcribe", { method: "POST", body: data });
      const result = await response.json();
      if (id !== attempt) return;
      if (!response.ok) throw new Error(result.error);
      const combined = [input.value.trim(), result.text].filter(Boolean).join(" ");
      input.value = combined.slice(0, input.maxLength);
      input.dispatchEvent(new Event("input"));
      input.focus();
      update("idle", combined.length > input.maxLength
        ? UI.voice_truncated
        : UI.voice_filled);
    } catch (error) {
      if (id !== attempt) return;
      update("idle", error.message || UI.voice_failed);
    }
  }

  function finish() {
    if (recorder.state !== "recording") return;
    update("transcribing", UI.voice_transcribing);
    recorder.stop();
  }

  button.addEventListener("click", async () => {
    if (state === "recording") {
      finish();
      return;
    }
    if (state !== "idle") return;
    const id = ++attempt;
    update("starting", UI.voice_waiting);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (id !== attempt) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      activeStream = stream;
      recorder = new MediaRecorder(stream, { mimeType: format });
      const chunks = [];
      recorder.addEventListener("dataavailable", event => {
        if (event.data.size) chunks.push(event.data);
      });
      recorder.addEventListener("stop", () => {
        if (id === attempt) sendAudio(new Blob(chunks, { type: format.split(";")[0] }), id);
      }, { once: true });
      recorder.addEventListener("error", () => {
        if (id !== attempt) return;
        attempt++;
        release();
        update("idle", UI.voice_interrupted);
      }, { once: true });
      recorder.start();
      elapsed.textContent = `0 / ${recordingLimit} ${UI.seconds}`;
      update("recording", UI.voice_recording);
      const started = performance.now();
      timer = setInterval(() => {
        const seconds = Math.floor((performance.now() - started) / 1000);
        elapsed.textContent = `${Math.min(seconds, recordingLimit)} / ${recordingLimit} ${UI.seconds}`;
        if (seconds >= recordingLimit) finish();
      }, 250);
    } catch (error) {
      if (id !== attempt) return;
      release();
      update("idle", error.name === "NotAllowedError"
        ? UI.voice_denied
        : UI.voice_no_mic);
    }
  });
  return () => {
    if (state === "idle") {
      status.textContent = "";
      return;
    }
    attempt++;
    if (recorder?.state === "recording") recorder.stop();
    release();
    update("idle", "");
  };
}
