#!/usr/bin/env python3
"""
Web Visualization Server
提供WebSocket接口用于电梯调度可视化
"""
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles


class VisualizationServer:
    """可视化服务器"""

    def __init__(self):
        self.app = FastAPI(title="Elevator Saga Visualization")
        self.recordings_dir = Path(__file__).parent / "recordings"
        self.static_dir = Path(__file__).parent / "static"

        # 确保目录存在
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(parents=True, exist_ok=True)

        # 设置路由
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""

        @self.app.get("/")
        async def index():
            """主页"""
            index_file = self.static_dir / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            else:
                return HTMLResponse(
                    """
                    <html>
                        <head><title>Elevator Visualization</title></head>
                        <body>
                            <h1>电梯可视化系统</h1>
                            <p>前端文件缺失，请先创建 static/index.html</p>
                        </body>
                    </html>
                    """
                )

        @self.app.get("/api/recordings")
        async def list_recordings():
            """列出所有记录文件"""
            try:
                recordings = []
                for file_path in self.recordings_dir.glob("*.json"):
                    # 读取元数据
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        metadata = data.get("metadata", {})
                        recordings.append(
                            {
                                "filename": file_path.name,
                                "path": str(file_path),
                                "metadata": metadata,
                                "mtime": file_path.stat().st_mtime,  # 文件修改时间
                            }
                        )
                # 按文件修改时间倒序排列（最新的在前）
                recordings.sort(key=lambda x: x["mtime"], reverse=True)
                return {"success": True, "recordings": recordings}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.get("/api/recording/{filename}")
        async def get_recording(filename: str):
            """获取指定记录文件"""
            try:
                file_path = self.recordings_dir / filename
                if not file_path.exists():
                    return {"success": False, "error": "File not found"}

                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {"success": True, "data": data}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket端点，用于实时播放"""
            await websocket.accept()
            print("🔗 WebSocket连接已建立")

            try:
                while True:
                    # 接收客户端消息
                    message = await websocket.receive_json()
                    command = message.get("command")

                    if command == "load_recording":
                        # 加载记录文件
                        filename = message.get("filename")
                        await self._send_recording(websocket, filename)

                    elif command == "ping":
                        # 心跳
                        await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                print("🔌 WebSocket连接已断开")
            except Exception as e:
                print(f"❌ WebSocket错误: {e}")
                await websocket.close()

        # 挂载静态文件
        self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")

    async def _send_recording(self, websocket: WebSocket, filename: Optional[str]):
        """发送记录文件到客户端"""
        try:
            if not filename:
                # 如果没有指定文件名，发送最新的记录
                recordings = list(self.recordings_dir.glob("*.json"))
                if not recordings:
                    await websocket.send_json({"type": "error", "message": "No recordings found"})
                    return
                # 按文件修改时间倒序排列（最新的在前）
                recordings.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                file_path = recordings[0]
            else:
                file_path = self.recordings_dir / filename

            if not file_path.exists():
                await websocket.send_json({"type": "error", "message": f"File not found: {filename}"})
                return

            # 读取记录文件
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 发送元数据
            await websocket.send_json(
                {"type": "metadata", "data": data.get("metadata", {}), "filename": file_path.name}
            )

            # 发送历史数据
            await websocket.send_json({"type": "history", "data": data.get("history", [])})

            print(f"📤 已发送记录: {file_path.name}")

        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})

    def run(self, host: str = "127.0.0.1", port: int = 8080):
        """启动服务器"""
        import uvicorn

        print(f"🚀 启动可视化服务器...")
        print(f"📍 访问地址: http://{host}:{port}")
        print(f"📁 记录目录: {self.recordings_dir}")
        uvicorn.run(self.app, host=host, port=port)


def main():
    """主函数"""
    server = VisualizationServer()
    server.run()


if __name__ == "__main__":
    main()
