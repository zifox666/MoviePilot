import json
from typing import Any

from fastapi import APIRouter, WebSocket, BackgroundTasks

from app.api.endpoints.message import start_message_chain
from app.core.config import settings
from app.log import logger
from app.utils.http import RequestUtils

onebot11_router = APIRouter(tags=['onebot11'])
onebot11_websocket = None


@onebot11_router.websocket("/v11/ws/")
async def onebot11_ws(websocket: WebSocket, background_tasks: BackgroundTasks) -> Any:
    """
    onebot11 ws反向服务器连接
    """
    global onebot11_websocket
    onebot11_websocket = websocket
    _ds_url = f"http://127.0.0.1:{settings.PORT}/api/v1/message?token={settings.API_TOKEN}&source=onebot11"
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        logger.info(data)
        if data.get("post_type", None) == "message":
            # background_tasks.add_task(start_message_chain, data, None, {"source": "onebot11"})
            logger.info(RequestUtils(timeout=5).post_res(_ds_url, json=data))


@onebot11_router.get("/v11/http")
async def get():
    return {
        "code": 200,
        "msg": "IAA 云天明 程心"
    }


def get_ob11_websocket():
    global onebot11_websocket
    return onebot11_websocket


def stop_ob11_websocket():
    global onebot11_websocket
    onebot11_websocket = None
