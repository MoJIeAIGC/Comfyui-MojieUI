import configparser
from volcengine.imagex.v2.imagex_service import ImagexService
import random
import string
def upload_image_data_to_volcengine(img_url):
    # 读取配置文件
    config = configparser.ConfigParser()
    config.read('config/config.ini')

    # 获取配置信息
    access_key = config.get('volcengine', 'access_key')
    secret_key = config.get('volcengine', 'secret_key')
    service_id = config.get('volcengine', 'service_id')

    # 初始化 ImagexService
    imagex_service = ImagexService()
    imagex_service.set_ak(access_key)
    imagex_service.set_sk(secret_key)

    # 设置参数
    params = {
        'ServiceId': service_id,
        'SkipMeta': False,
        'SkipCommit': False
    }

    try:
        query = {
            'Action': 'GetSyncAuditResult',
            'Version': '2018-08-01',
        }
        all_chars = string.ascii_letters + string.digits
        random_data_id = ''.join(random.choice(all_chars) for i in range(16))
        body = {

            # "ImageUri": "https://qihuaimage.tos-cn-guangzhou.volces.com/template/6cFkST.jpg",
            "ImageUri": img_url,
            "AuditDimensions": [
                "porn",
                "sensitive1",
                "sensitive2"
            ],
            "AuditTextDimensions": [
                "ad"
            ],
            "AuditAbility": 1,
            "EnableLargeImageDetect": True,
            "DataId": random_data_id

        }
        print("查询参数:", query)
        print("请求体:", body)
        resp = imagex_service.get_sync_audit_result(query, body)
        print("查询图片审核结果成功:", resp)
        result = resp.get('Result', {})
        image_type = result.get('ImageType')
        if image_type == 'normal':
            return True
        else:
            return False

        return resp
    except Exception as e:
        print(f"上传图片数据时出错: {e}")
        return None