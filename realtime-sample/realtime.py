import asyncio
import base64
import os

from azure.core.credentials import AzureKeyCredential
from fastapi import WebSocket, WebSocketDisconnect
from rtclient import (
    InputAudioTranscription,
    RTAudioContent,
    RTClient,
    RTFunctionCallItem,
    RTInputAudioItem,
    RTMessageItem,
    RTResponse,
    ServerVAD,
)
from sample_tools import signature_search_from_web


async def send_audio(client: RTClient, websocket: WebSocket):
    while True:
        try:
            message = await websocket.receive_json()
            base64_audio = message["audio"]
            # TODO: 目前只处理音频输入
            if base64_audio:
                try:
                    byte_array = bytearray(base64.b64decode(base64_audio))
                except Exception as e:
                    print(f"Decode error: {e}")
                await client.send_audio(byte_array)

        except WebSocketDisconnect:
            break


async def receive_message_item(item: RTMessageItem, websocket: WebSocket):
    prefix = f"[response={item.response_id}][item={item.id}]"
    async for contentPart in item:
        if contentPart.type == "audio":

            async def collect_audio(audioContentPart: RTAudioContent):
                audio_data = bytearray()
                async for chunk in audioContentPart.audio_chunks():
                    audio_data.extend(chunk)
                    await websocket.send_json(
                        {
                            "type": "response.audio.delta",
                            "delta": base64.b64encode(chunk).decode("utf-8"),
                        }
                    )
                return audio_data

            async def collect_transcript(audioContentPart: RTAudioContent):
                audio_transcript: str = ""
                async for chunk in audioContentPart.transcript_chunks():
                    audio_transcript += chunk
                    await websocket.send_json(
                        {"type": "response.audio_transcript.delta", "delta": chunk}
                    )
                return audio_transcript

            audio_task = asyncio.create_task(collect_audio(contentPart))
            transcript_task = asyncio.create_task(collect_transcript(contentPart))
            audio_data, audio_transcript = await asyncio.gather(
                audio_task, transcript_task
            )
            print(prefix, f"Audio received with length: {len(audio_data)}")
            print(prefix, f"Audio Transcript: {audio_transcript}")
        elif contentPart.type == "text":
            text_data = ""
            async for chunk in contentPart.text_chunks():
                text_data += chunk
            print(prefix, f"Text: {text_data}")


async def receive_function_call_item(item: RTFunctionCallItem):
    prefix = f"[function_call_item={item.id}]"
    await item
    print(prefix, f"Function call arguments: {item.arguments}")
    print(f"{item.id}.function_call.json")


async def receive_response(
    client: RTClient, response: RTResponse, websocket: WebSocket
):
    prefix = f"[response={response.id}]"
    async for item in response:
        print(prefix, f"Received item {item.id}")
        if item.type == "message":
            asyncio.create_task(receive_message_item(item, websocket))
        elif item.type == "function_call":
            asyncio.create_task(receive_function_call_item(item))

    print(prefix, f"Response completed ({response.status})")
    # if response.status == "completed":
    #     await client.close()


async def receive_input_item(item: RTInputAudioItem, websocket: WebSocket):
    prefix = f"[input_item={item.id}]"
    await item
    print(prefix, f"Transcript: {item.transcript}")
    print(prefix, f"Audio Start [ms]: {item.audio_start_ms}")
    print(prefix, f"Audio End [ms]: {item.audio_end_ms}")
    await websocket.send_json(
        {"type": "response.audio_transcript.delta", "delta": item.transcript}
    )


async def receive_events(client: RTClient, websocket: WebSocket):
    async for event in client.events():
        if event.type == "input_audio":
            asyncio.create_task(receive_input_item(event, websocket))
        elif event.type == "response":
            asyncio.create_task(receive_response(client, event, websocket))


async def receive_messages(client: RTClient, websocket: WebSocket):
    await asyncio.gather(
        receive_events(client, websocket),
    )


async def run(client: RTClient, websocket: WebSocket):
    print("Configuring Session...", end="", flush=True)
    await client.configure(
        turn_detection=ServerVAD(
            threshold=0.2, prefix_padding_ms=300, silence_duration_ms=500
        ),
        input_audio_transcription=InputAudioTranscription(model="whisper-1"),
        instructions="You are a helpful assistant. Reply in Chinese.",
        temperature=0.6,
        tools=[signature_search_from_web],
        # modalities={"text", "audio"},
        # voice="alloy",
        # input_audio_format="pcm16",
        # output_audio_format="pcm16",
    )
    print("Done")

    await asyncio.gather(
        send_audio(client, websocket), receive_messages(client, websocket)
    )
    print("Session closed")


async def handle(websocket: WebSocket):
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

    async with RTClient(
        url=endpoint,
        key_credential=AzureKeyCredential(key),
        azure_deployment=deployment,
    ) as client:
        await run(client, websocket)
