from templateVideo.workflowUtils import ComfyUIHelper

class Workflow:
    @staticmethod
    def generate_videos(server_address: str, workflow_file: str, prompt_updates: dict):
        """
        执行 ComfyUI 工作流并返回生成的视频文件对象
        :param server_address: ComfyUI 服务器地址（例如 "127.0.0.1:8188"）
        :param workflow_file: 工作流 JSON 文件路径（例如 "test4.json"）
        :param prompt_updates: 需要更新的工作流参数（例如 {"12": {"inputs": {"value": "Video description"}}}）
        :return: 视频文件对象列表（每个元素是一个 io.BytesIO 对象）
        """
        # 初始化工具类
        comfy_ui = ComfyUIHelper(server_address, workflow_file)

        # 执行工作流并获取视频
        try:
            videos = comfy_ui.get_videos(prompt_updates)
            print("工作流执行成功，生成的视频数据已获取。")
        except Exception as e:
            print(f"工作流执行失败: {e}")
            return []

        # 保存视频到文件并返回文件对象
        file_objects = []
        for node_id, video_list in videos.items():
            for idx, video_data in enumerate(video_list):
                file_obj = comfy_ui.save_video(video_data)  # 返回文件对象
                file_objects.append(file_obj)
                print(f"视频文件对象已生成: {file_obj}")

        return file_objects