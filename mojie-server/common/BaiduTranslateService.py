import random
from hashlib import md5
import requests
from django.conf import settings


class BaiduTranslateService:
    """
    Django 百度翻译服务封装类
    从 settings.py 中读取配置信息
    """

    def __init__(self, from_lang=None, to_lang=None):
        """
        初始化翻译服务
        :param from_lang: 可选，源语言代码，如果为None则使用settings中的默认值
        :param to_lang: 可选，目标语言代码，如果为None则使用settings中的默认值
        """
        config = settings.BAIDU_TRANSLATE_CONFIG

        self.appid = config['APPID']
        self.appkey = config['APPKEY']
        self.from_lang = from_lang if from_lang else config['FROM_LANG']
        self.to_lang = to_lang if to_lang else config['TO_LANG']
        self.url = config['ENDPOINT'] + config['PATH']

    @staticmethod
    def _make_md5(s, encoding='utf-8'):
        """生成MD5签名"""
        return md5(s.encode(encoding)).hexdigest()

    def translate(self, text):
        """
        执行翻译操作
        :param text: 需要翻译的文本
        :return: 翻译后的文本，如果出错返回None
        """
        if not text.strip():
            return ""

        try:
            # 生成盐值和签名
            salt = random.randint(32768, 65536)
            sign = self._make_md5(self.appid + text + str(salt) + self.appkey)

            # 构建请求
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            payload = {
                'appid': self.appid,
                'q': text,
                'from': self.from_lang,
                'to': self.to_lang,
                'salt': salt,
                'sign': sign
            }

            # 发送请求并获取响应
            response = requests.post(self.url, params=payload, headers=headers)
            response.raise_for_status()  # 如果请求失败会抛出HTTPError异常

            result = response.json()

            # 检查是否有错误
            if 'error_code' in result:
                error_msg = result.get('error_msg', '未知错误')
                raise Exception(f"百度翻译API错误: {error_msg}")

            # 解析并返回翻译结果
            if 'trans_result' in result:
                return '\n'.join([item['dst'] for item in result['trans_result']])
            return None

        except requests.exceptions.RequestException as e:
            raise Exception(f"翻译请求失败: {str(e)}")
        except Exception as e:
            raise Exception(f"翻译过程中发生错误: {str(e)}")