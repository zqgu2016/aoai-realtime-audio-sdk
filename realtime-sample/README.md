# Configuration

> Create `.env` file and then fill out fields

# Server Side Setup

```shell
# wget https://github.com/Azure-Samples/aoai-realtime-audio-sdk/releases/download/py%2Fv0.5.2/rtclient-0.5.2-py3-none-any.whl

# Optional
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install rtclient-0.5.2-py3-none-any.whl

# dev mode
uvicorn main:app --reload

# prod mode
uvicorn main:app
```

# Frontend

> open `http://127.0.0.1:8000/`


# 前后端事件定义
- 1. FE: send `{
        type: "input_audio_buffer.append",
        audio: base64,
      }`
- 2. BE: decode base64 to byte_array -> `client.send_audio(byte_array)` -> realtime API
- 3. BE: client event type == "input_audio" -> receive `response.audio_transcript.delta` -> FE
- 3. BE: client event type == "response" -> 区分 message or function_call
- 4. BE: message区分audio or text
- 5. BE: 处理audio audio_chunks和transcript_chunks（send `response.audio.delta` and `response.audio_transcript.delta`） -> FE
- 6. BE：处理text -> FE