import asyncio
import json
import os

from azure.core.credentials import AzureKeyCredential
from fastapi import WebSocket, WebSocketDisconnect
from rtclient import (
    FunctionCallOutputItem,
    InputAudioTranscription,
    InputTextContentPart,
    RTAudioContent,
    RTClient,
    RTFunctionCallItem,
    RTInputAudioItem,
    RTMessageItem,
    RTResponse,
    ServerVAD,
    UserMessageItem,
)
from sample_tools import search_from_web, signature_search_from_web


async def send_input(client: RTClient, websocket: WebSocket):
    while True:
        try:
            message = await websocket.receive()
            if "text" in message:
                text = message["text"]
                data = json.loads(text)
                await client.send_item(
                    UserMessageItem(content=[InputTextContentPart(text=data["text"])])
                )
                await client.generate_response()
            elif "bytes" in message:
                # TODO: 目前只处理音频输入
                base64_audio = message["bytes"]
                await client.send_audio(base64_audio)

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
                    await websocket.send_bytes(chunk)
                return audio_data

            async def collect_transcript(audioContentPart: RTAudioContent):
                audio_transcript: str = ""
                async for chunk in audioContentPart.transcript_chunks():
                    audio_transcript += chunk
                    await websocket.send_json(
                        {"type": "text_delta", "delta": chunk, "id": item.id}
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
                await websocket.send_json(
                    {"type": "text_delta", "delta": chunk, "id": item.id}
                )
            print(prefix, f"Text: {text_data}")


async def receive_function_call_item(client: RTClient, item: RTFunctionCallItem):
    prefix = f"[function_call_item={item.id}]"
    await item
    print(prefix, f"Function call arguments: {item.arguments}")
    print(f"{item.id}.function_call.json")
    if item.function_name == "search_from_web":
        arguments = json.loads(item.arguments)
        result = await search_from_web(**arguments)
        await client.send_item(
            FunctionCallOutputItem(call_id=item.call_id, output=result),
            previous_item_id=item.id,
        )
        await client.generate_response()


async def receive_response(
    client: RTClient, response: RTResponse, websocket: WebSocket
):
    prefix = f"[response={response.id}]"
    async for item in response:
        print(prefix, f"Received item {item.id}")
        if item.type == "message":
            asyncio.create_task(receive_message_item(item, websocket))
        elif item.type == "function_call":
            asyncio.create_task(receive_function_call_item(client, item))

    print(prefix, f"Response completed ({response.status})")


async def receive_input_item(item: RTInputAudioItem, websocket: WebSocket):
    prefix = f"[input_item={item.id}]"
    await item
    print(prefix, f"Transcript: {item.transcript}")
    print(prefix, f"Audio Start [ms]: {item.audio_start_ms}")
    print(prefix, f"Audio End [ms]: {item.audio_end_ms}")
    await websocket.send_json(
        {"type": "transcription", "text": item.transcript, "id": item.id}
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
        send_input(client, websocket), receive_messages(client, websocket)
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
