import configparser
import tos
from typing import Optional

class VolcengineTOSUtils:
    def __init__(self):
        # 读取配置文件
        config = configparser.ConfigParser()
        config.read('config/config.ini')

        # 获取配置信息
        self.access_key_id = config.get('oss', 'access_key_id')
        self.access_key_secret = config.get('oss', 'access_key_secret')
        self.endpoint = config.get('oss', 'endpoint')
        self.region = config.get('oss', 'region')
        self.bucket_name = config.get('oss', 'bucket_name')

        # 初始化 TOS 客户端
        self.client = tos.TosClientV2(
            ak=self.access_key_id,
            sk=self.access_key_secret,
            endpoint=self.endpoint,
            region=self.region
        )

    def upload_image(self, object_name: str, file_path: Optional[str] = None, file_data: Optional[bytes] = None) -> str:
        """
        上传图片到火山引擎 TOS
        :param object_name: 对象名称（在 TOS 中的存储路径和文件名）
        :param file_path: 本地文件路径
        :param file_data: 文件字节数据
        :return: 图片的访问 URL
        """
        try:
            if file_path:
                # 从文件路径上传
                self.client.put_object_from_file(
                    bucket=self.bucket_name,
                    key=object_name,
                    file_path=file_path
                )
            elif file_data:
                # 从字节数据上传
                self.client.put_object(
                    bucket=self.bucket_name,
                    key=object_name,
                    content=file_data
                )
            else:
                raise ValueError("必须提供 file_path 或 file_data 之一")

            # 生成图片的访问 URL
            image_url = f"https://{self.bucket_name}.{self.endpoint.replace('https://', '')}/{object_name}"
            return image_url
        except Exception as e:
            print(f"上传图片失败: {e}")
            return ""
            
    def delete_object(self, full_object_name: str) -> bool:
        """
        删除火山引擎 TOS 中的对象
        :param full_object_name: 完整对象名称，格式为 folder_name/img_name
        :return: 删除是否成功
        """
        try:
            # 删除指定桶下的指定对象
            resp = self.client.delete_object(self.bucket_name, full_object_name)
            print(f"删除对象成功: {full_object_name}")
            return True
        except tos.exceptions.TosClientError as e:
            # 操作失败，捕获客户端异常，一般情况为非法请求参数或网络异常
            print(f"删除对象失败，客户端错误: {e.message}, 原因: {e.cause}")
            return False
        except tos.exceptions.TosServerError as e:
            # 操作失败，捕获服务端异常，可从返回信息中获取详细错误信息
            print(f"删除对象失败，服务端错误:")
            print(f"错误码: {e.code}")
            print(f"请求ID: {e.request_id}")
            print(f"错误信息: {e.message}")
            print(f"HTTP状态码: {e.status_code}")
            print(f"EC: {e.ec}")
            print(f"请求URL: {e.request_url}")
            return False
        except Exception as e:
            print(f"删除对象失败，未知错误: {e}")
            return False