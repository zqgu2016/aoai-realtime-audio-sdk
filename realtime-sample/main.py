from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from realtime import handle as handle_realtime

load_dotenv(override=True)

app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def get():
    with open("static/index.html", "r") as f:
        return f.read()


@app.post("/message")
async def post_message(request: Request, client_id: str | None = None):
    data = await request.json()
    return data


@app.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket, client_id: str | None = None):
    await websocket.accept()
    await handle_realtime(websocket)
