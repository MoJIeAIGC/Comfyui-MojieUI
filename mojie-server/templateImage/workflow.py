from datetime import time
from templateImage.workflowUtils import ComfyUIHelper
from typing import List
from threading import Event
import io
import time


class Workflow:
    @staticmethod
    def generate_images(server_address: str, workflow_file: str, prompt_updates: dict) -> List[io.BytesIO]:
        """完整版本"""
        helper = ComfyUIHelper(server_address, workflow_file)
        done_event = Event()
        result = {'images': {}, 'error': None}  # 默认images为字典

        def callback(images, error):
            """可靠的回调函数"""
            nonlocal result
            try:
                if error:
                    result['error'] = error
                else:
                    result['images'] = images if images else {}
            finally:
                done_event.set()  # 确保事件一定会触发

        try:
            # 提交任务
            task_id = helper.enqueue_workflow(prompt_updates, callback)
            print(f"任务已排队，ID: {task_id}")

            # 等待完成
            if not done_event.wait(timeout=300):
                raise TimeoutError("任务执行超时")

            # 检查结果
            if result['error']:
                raise RuntimeError(result['error'])

            # 处理图像
            file_objects = []
            for node_id, image_list in result['images'].items():
                for img_data in image_list:
                    file_obj = helper.save_image(img_data)
                    file_objects.append(file_obj)

            print(f"任务完成，生成 {len(file_objects)} 张图像")
            return file_objects

        except Exception as e:
            print(f"任务失败: {str(e)}")
            return []

    @staticmethod
    def generate_images_from_custom_node(
            server_address: str,
            workflow_file: str,
            prompt_updates: dict,
            target_node_id: str
    ) -> List[io.BytesIO]:
        """
        改进版：从指定节点获取生成的图像文件对象（带队列管理和健壮性处理）
        :param server_address: ComfyUI 服务器地址
        :param workflow_file: 工作流 JSON 文件路径
        :param prompt_updates: 需要更新的工作流参数
        :param target_node_id: 目标节点 ID
        :return: 图像文件对象列表
        """
        helper = ComfyUIHelper(server_address, workflow_file)
        done_event = Event()
        result = {'images': [], 'error': None}  # 默认images为列表

        def callback(images, error):
            """可靠的回调函数"""
            nonlocal result
            try:
                if error:
                    result['error'] = error
                else:
                    # 确保images是列表类型，即使为空
                    result['images'] = list(images) if images else []
            finally:
                done_event.set()  # 确保事件一定会触发

        try:
            # 提交任务到队列
            task_id = helper.enqueue_workflow(
                prompt_updates,
                callback,
                target_node_id=target_node_id
            )
            print(f"任务已提交，ID: {task_id}，目标节点: {target_node_id}")

            # 等待任务完成（带超时）
            if not done_event.wait(timeout=300):  # 5分钟超时
                raise TimeoutError("等待任务完成超时")

            # 检查错误
            if result['error']:
                raise RuntimeError(result['error'])

            # 处理图像结果
            file_objects = []
            for image_data in result['images']:
                try:
                    file_obj = helper.save_image(image_data)
                    file_objects.append(file_obj)
                    print(f"已从节点 {target_node_id} 生成图像")
                except Exception as e:
                    print(f"保存图像失败: {e}")

            print(f"任务完成，共生成 {len(file_objects)} 张图像")
            return file_objects

        except Exception as e:
            print(f"任务失败: {str(e)}")
            return []