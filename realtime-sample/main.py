from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from realtime import handle as handle_realtime

load_dotenv(override=True)

app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket, client_id: str | None = None):
    await websocket.accept()
    await handle_realtime(websocket)
