import websocket
import uuid
import json
import urllib.request
import urllib.parse
import io

class ComfyUIHelper:
    def __init__(self, server_address: str, workflow_file: str):
        """
        初始化工具类
        :param server_address: ComfyUI 服务器地址（例如 "127.0.0.1:8188"）
        :param workflow_file: 工作流 JSON 文件路径（例如 "test4.json"）
        """
        self.server_address = server_address
        self.workflow_file = workflow_file
        self.client_id = str(uuid.uuid4())  # 生成唯一的客户端 ID
        self.ws = None  # WebSocket 连接对象

    def _queue_prompt(self, prompt: dict) -> str:
        """
        将工作流发送到服务器并获取 prompt_id
        :param prompt: 工作流数据（字典格式）
        :return: prompt_id
        """
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')

        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())['prompt_id']

    def _get_video(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """
        从服务器下载视频
        :param filename: 文件名
        :param subfolder: 子文件夹
        :param folder_type: 文件夹类型
        :return: 视频的二进制数据
        """
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)

        with urllib.request.urlopen(f"http://{self.server_address}/view?{url_values}") as response:
            return response.read()

    def _get_history(self, prompt_id: str) -> dict:
        """
        获取工作流的执行历史
        :param prompt_id: 工作流的 prompt_id
        :return: 历史记录的 JSON 数据
        """
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def get_videos(self, prompt_updates: dict) -> dict:
        """
        执行工作流并下载生成的视频
        :param prompt_updates: 需要更新的工作流参数（例如 {"12": {"inputs": {"value": "Video description"}}}）
        :return: 生成的视频数据（字典格式，键为节点 ID，值为视频二进制数据列表）
        """
        # 加载工作流 JSON 文件
        with open(self.workflow_file, encoding="utf-8") as f:
            prompt = json.loads(f.read())

        # 更新工作流参数
        for node_id, updates in prompt_updates.items():
            if node_id in prompt:
                prompt[node_id]["inputs"].update(updates["inputs"])

        # 建立 WebSocket 连接
        self.ws = websocket.WebSocket()
        self.ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")

        # 发送工作流并获取 prompt_id
        prompt_id = self._queue_prompt(prompt)
        output_videos = {}

        # 监听 WebSocket 消息，直到工作流执行完成
        while True:
            out = self.ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break
            else:
                continue

        # 获取工作流执行历史
        history = self._get_history(prompt_id)[prompt_id]

        # 遍历历史记录中的每个节点
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            videos_output = []
            if 'videos' in node_output:
                for video in node_output['videos']:
                    video_data = self._get_video(video['filename'], video['subfolder'], video['type'])
                    videos_output.append(video_data)
            output_videos[node_id] = videos_output

        # 关闭 WebSocket 连接
        self.ws.close()

        return output_videos

    @staticmethod
    def save_video(video_data: bytes, file_path: str = None):
        """
        将视频数据保存到文件对象中
        :param video_data: 视频的二进制数据
        :param file_path: 文件保存路径（可选）
        :return: 文件对象（如果 file_path 为 None，则返回文件对象；否则保存到指定路径）
        """
        if file_path:
            # 如果指定了文件路径，保存视频到文件
            with open(file_path, 'wb') as f:
                f.write(video_data)
            return file_path
        else:
            # 如果没有指定文件路径，返回文件对象
            file_obj = io.BytesIO()
            file_obj.write(video_data)
            file_obj.seek(0)  # 将文件指针移动到开头
            return file_obj