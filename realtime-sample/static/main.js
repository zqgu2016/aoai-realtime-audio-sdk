let ws;

let audioRecorder;
let audioPlayer;

let recordingActive = false;
let buffer = new Uint8Array();

const chatArea = document.querySelector("#chat-area");
const inputField = document.querySelector("#message-input");
const voiceBtn = document.querySelector("#voice-button");
const voiceIcon = document.querySelector("#voice-icon");

function makeNewTextBlock(text = "") {
  let newElement = document.createElement("p");
  newElement.textContent = text;
  chatArea.appendChild(newElement);
}

function appendToTextBlock(text) {
  let textElements = chatArea.children;
  if (textElements.length === 0) {
    makeNewTextBlock();
  }
  textElements[textElements.length - 1].textContent += text;
}

async function sendMessage() {
  return;
  const message = inputField.value.trim();

  if (!message) return;

  ws.send(JSON.stringify({
    type: "conversation.item.create",
    text: message,
  }));
  inputField.value = "";

  makeNewTextBlock("User: " + message);
  inputField.value = "";
  makeNewTextBlock("ChatBot: " + message);
}

function toggleVoiceInput() {
  recordingActive = !recordingActive;

  if (recordingActive) {
    startVoiceRecognition();
  } else {
    stopVoiceRecognition();
  }
}

function startVoiceRecognition() {
  voiceBtn.disabled = true;
  voiceBtn.classList.add("cursor-not-allowed");
  voiceBtn.classList.add("opacity-50");

  initWs();
  resetAudio(true);
}

function stopVoiceRecognition() {
  voiceIcon.src = "static/assets/microphone-solid.svg";
  ws.close();
  resetAudio(false);
}

function initWs() {
  const client_id = Date.now();
  ws = new WebSocket(`ws://localhost:8000/realtime?client_id=${client_id}`);

  ws.onopen = function () {
    console.log("Connected to server");
  };

  ws.onmessage = function (event) {
    const message = JSON.parse(event.data);

    let consoleLog = "" + message.type;

    switch (message.type) {
      // optional, 有些需要前端处理，有些需要后端处理
      case "response.function_call_arguments.done":
        handleFunctionCall(message);
        break;
      case "session.created":
        setFormInputState(InputState.ReadyToStop);
        makeNewTextBlock("<< Session Started >>");
        makeNewTextBlock();
        break;
      case "response.audio_transcript.delta":
        appendToTextBlock(message.delta);
        break;
      case "response.audio.delta":
        const binary = atob(message.delta);
        const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
        const pcmData = new Int16Array(bytes.buffer);
        audioPlayer.play(pcmData);
        break;

      case "input_audio_buffer.speech_started":
        makeNewTextBlock("<< Speech Started >>");
        if (enableAzureSpeech) {
          makeNewTextBlock("<< Azure Speech Started >>");
          let textElements = formReceivedTextContainer.children;
          latestInputSpeechBlock = textElements[textElements.length - 2];
          latestInputAzureSpeechBlock = textElements[textElements.length - 1];
        } else {
          let textElements = formReceivedTextContainer.children;
          latestInputSpeechBlock = textElements[textElements.length - 1];
        }
        makeNewTextBlock();
        audioPlayer.clear();
        break;
      case "conversation.item.input_audio_transcription.completed":
        latestInputSpeechBlock.textContent += " User: " + message.transcript;
        break;
      case "response.done":
        formReceivedTextContainer.appendChild(document.createElement("hr"));
        break;
      default:
        consoleLog = JSON.stringify(message, null, 2);
        break;
    }
    if (consoleLog) {
      console.log(consoleLog);
    }
  };

  ws.onclose = function (event) {
    console.log("Disconnected from server");
  };

  ws.onerror = function (error) {
    console.log(error.message);
  };
}

function combineArray(newData) {
  const newBuffer = new Uint8Array(buffer.length + newData.length);
  newBuffer.set(buffer);
  newBuffer.set(newData, buffer.length);
  buffer = newBuffer;
}

function processAudioRecordingBuffer(data) {
  const uint8Array = new Uint8Array(data);
  combineArray(uint8Array);
  // 采样率是24000，样本数4800，表示每次处理: 4800/24000 = 0.2秒
  // 1. 提供了稳定的音频流，通过合理的缓冲，确保音频数据传输的流畅性和有效性。
  // 2. 在实时音频应用中，合理的时间窗口可以确保低延迟和高质量的音频处理。
  if (buffer.length >= 4800) {
    const toSend = new Uint8Array(buffer.slice(0, 4800));
    buffer = new Uint8Array(buffer.slice(4800));
    const regularArray = String.fromCharCode(...toSend);
    const base64 = btoa(regularArray);
    if (recordingActive) {
      ws.send(JSON.stringify({
        type: "input_audio_buffer.append",
        audio: base64,
      }));
    }
  }
}

async function resetAudio(startRecording) {
  recordingActive = false;
  if (audioRecorder) {
    audioRecorder.stop();
  }

  if (audioPlayer) {
    audioPlayer.clear();
  }

  audioRecorder = new Recorder(processAudioRecordingBuffer);
  audioPlayer = new Player();
  audioPlayer.init(24000);

  if (startRecording) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    audioRecorder.start(stream);
    recordingActive = true;

    voiceBtn.disabled = false;
    voiceIcon.src = "static/assets/stop-solid.svg";
    voiceBtn.classList.remove("cursor-not-allowed");
    voiceBtn.classList.remove("opacity-50");
  }
}
