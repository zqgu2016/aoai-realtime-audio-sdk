from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from realtime import handle as handle_realtime

load_dotenv(override=True)

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)


@app.get("/")
async def main():
    return {"message": "Hello World"}


@app.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket, client_id: str | None = None):
    await websocket.accept()
    await handle_realtime(websocket)
