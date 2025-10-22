#!/usr/bin/env python3
"""
Web Visualization Server
提供WebSocket接口用于电梯调度可视化
"""
import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


class VisualizationServer:
    """可视化服务器"""

    def __init__(self):
        self.app = FastAPI(title="Elevator Saga Visualization")
        self.recordings_dir = Path(__file__).parent / "recordings"
        self.static_dir = Path(__file__).parent / "static"
        self.client_examples_dir = Path(__file__).parent.parent / "client_examples"
        self.traffic_dir = Path(__file__).parent.parent / "traffic"

        # 确保目录存在
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(parents=True, exist_ok=True)

        # 运行状态跟踪
        self.running_processes: Dict[str, subprocess.Popen] = {}

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

        @self.app.get("/api/algorithms")
        async def list_algorithms():
            """列出所有可用算法"""
            try:
                algorithms = []

                # 添加主controller.py
                controller_path = Path(__file__).parent.parent.parent / "controller.py"
                if controller_path.exists():
                    algorithms.append({
                        "filename": "controller.py",
                        "name": "LOOK V2 (Main)",
                        "description": "主算法 - 实时决策版本LOOK V2",
                    })

                # 列出client_examples目录中的所有算法文件
                for file_path in self.client_examples_dir.glob("*.py"):
                    # 跳过__init__.py
                    if file_path.name.startswith("__"):
                        continue

                    # 读取文件获取算法描述
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # 提取docstring中的描述
                        description = ""
                        lines = content.split("\n")
                        in_docstring = False
                        for line in lines:
                            if '"""' in line and not in_docstring:
                                in_docstring = True
                                desc_part = line.split('"""')[1] if len(line.split('"""')) > 1 else ""
                                if desc_part and not desc_part.startswith("\n"):
                                    description = desc_part.strip()
                                    break
                            elif in_docstring:
                                if '"""' in line:
                                    description = line.split('"""')[0].strip()
                                    break
                                else:
                                    description = line.strip()
                                    if description:
                                        break

                    # 显示名称
                    display_name = file_path.stem
                    # 如果有visual_前缀就去掉
                    if display_name.startswith("visual_"):
                        display_name = display_name[7:]

                    algorithms.append({
                        "filename": file_path.name,
                        "name": display_name,
                        "description": description or display_name,
                    })

                # 按文件名排序
                algorithms.sort(key=lambda x: x["filename"])
                return {"success": True, "algorithms": algorithms}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.get("/api/traffic_files")
        async def list_traffic_files():
            """列出所有流量文件"""
            try:
                traffic_files = []
                for file_path in self.traffic_dir.glob("*.json"):
                    # 读取文件获取元数据
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            building = data.get("building", {})
                            traffic_files.append({
                                "filename": file_path.name,
                                "name": file_path.stem,
                                "elevators": building.get("elevators", 0),
                                "floors": building.get("floors", 0),
                                "duration": building.get("duration", 0),
                                "passengers": len(data.get("traffic", [])),
                            })
                    except:
                        # 如果读取失败，添加基本信息
                        traffic_files.append({
                            "filename": file_path.name,
                            "name": file_path.stem,
                        })

                # 按文件名排序
                traffic_files.sort(key=lambda x: x["filename"])
                return {"success": True, "traffic_files": traffic_files}
            except Exception as e:
                return {"success": False, "error": str(e)}

        class RunRequest(BaseModel):
            algorithm: str
            traffic_file: str

        @self.app.post("/api/run_algorithm")
        async def run_algorithm(request: RunRequest):
            """运行指定算法和流量文件"""
            try:
                import httpx

                # 检查是否是controller.py（在项目根目录）
                if request.algorithm == "controller.py":
                    algorithm_file = Path(__file__).parent.parent.parent / "controller.py"
                else:
                    algorithm_file = self.client_examples_dir / request.algorithm

                traffic_file = self.traffic_dir / request.traffic_file

                if not algorithm_file.exists():
                    return {"success": False, "error": f"算法文件不存在: {request.algorithm}"}

                if not traffic_file.exists():
                    return {"success": False, "error": f"流量文件不存在: {request.traffic_file}"}

                # 生成记录文件名（去掉visual_前缀）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                algorithm_name = algorithm_file.stem
                if algorithm_name.startswith("visual_"):
                    algorithm_name = algorithm_name[7:]  # 去掉"visual_"前缀
                traffic_name = traffic_file.stem
                recording_filename = f"{algorithm_name}_{traffic_name}_{timestamp}.json"

                # 1. 先获取simulator的流量文件列表，找到目标流量文件的索引
                simulator_url = "http://127.0.0.1:8000"
                try:
                    # 绕过系统代理设置，直接连接localhost
                    async with httpx.AsyncClient(trust_env=False) as client:
                        # 获取当前流量信息
                        info_response = await client.get(f"{simulator_url}/api/traffic/info")
                        if info_response.status_code != 200:
                            return {"success": False, "error": "无法连接到模拟器服务器"}

                        info = info_response.json()
                        current_index = info.get("current_index", 0)
                        total_files = info.get("total_files", 0)

                        # 计算需要切换多少次才能到达目标流量文件
                        # 注意：这里假设traffic文件夹中的文件顺序与simulator加载的顺序一致
                        traffic_files = sorted([f.name for f in self.traffic_dir.glob("*.json")])
                        try:
                            target_index = traffic_files.index(request.traffic_file)
                        except ValueError:
                            return {"success": False, "error": f"流量文件不在列表中: {request.traffic_file}"}

                        # 切换到目标流量文件
                        while current_index != target_index:
                            next_response = await client.post(f"{simulator_url}/api/traffic/next",
                                                             json={"full_reset": True})
                            if next_response.status_code != 200 or not next_response.json().get("success"):
                                return {"success": False, "error": "切换流量文件失败"}

                            current_index = (current_index + 1) % total_files

                        print(f"✅ 已切换到流量文件: {traffic_name}")

                except Exception as e:
                    return {"success": False, "error": f"配置模拟器失败: {str(e)}"}

                # 2. 启动算法脚本
                print(f"🚀 启动算法: {algorithm_name}, 流量: {traffic_name}")

                # 使用subprocess运行Python脚本，设置UTF-8编码避免Windows下的emoji错误
                import os
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"  # 强制使用UTF-8编码

                process = subprocess.Popen(
                    [sys.executable, str(algorithm_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",  # 遇到无法编码的字符时替换而不是报错
                    env=env,
                )

                # 等待进程完成
                stdout, stderr = process.communicate(timeout=300)  # 5分钟超时

                if process.returncode == 0:
                    print(f"✅ 算法运行完成")
                    # 查找最新生成的记录文件
                    recordings = list(self.recordings_dir.glob("*.json"))
                    if recordings:
                        recordings.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        latest_recording = recordings[0]

                        # 重命名为规范格式
                        new_path = self.recordings_dir / recording_filename
                        if new_path.exists():
                            # 如果文件已存在，添加序号
                            i = 1
                            while new_path.exists():
                                new_path = self.recordings_dir / f"{algorithm_name}_{traffic_name}_{timestamp}_{i}.json"
                                i += 1
                        latest_recording.rename(new_path)

                        return {
                            "success": True,
                            "recording": new_path.name,
                            "message": "算法运行成功",
                        }
                    else:
                        return {
                            "success": False,
                            "error": "算法运行完成但未找到记录文件",
                        }
                else:
                    print(f"❌ 算法运行失败: {stderr}")
                    return {
                        "success": False,
                        "error": f"算法运行失败: {stderr}",
                    }

            except subprocess.TimeoutExpired:
                return {"success": False, "error": "算法运行超时（5分钟）"}
            except Exception as e:
                import traceback
                traceback.print_exc()
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
