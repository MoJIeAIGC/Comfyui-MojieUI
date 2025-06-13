import requests
from urllib.parse import urlencode
from configparser import ConfigParser
import os
import random
class SMSUtils:
    def __init__(self):
        config = ConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), '../config/config.ini'))
        self.account = config.get('message', 'appid')
        self.password = config.get('message', 'api_key')
        self.url = 'https://106.ihuyi.com/webservice/sms.php?method=Submit'

    def send_sms(self, mobile,method='POST'):
        """
        发送短信
        :param mobile: 手机号码
        :param content: 短信内容
        :param method: 提交方式(POST/GET)
        :return: 返回结果
        """
        # 自动生成4位验证码
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        
        
        content = f"您的验证码是：{verification_code}。请不要把验证码泄露给其他人。"
        
        data = {
            'account': self.account,
            'password': self.password,
            'mobile': mobile,
            'content': content,
        }
        print("发送短信数据:", data)  # 打印发送的数据

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
        }

        try:
            if method.upper() == 'POST':
                response = requests.post(self.url, data=urlencode(data), headers=headers)
            else:
                response = requests.get(f"{self.url}&{urlencode(data)}", headers=headers)
            
            # result = response.json() if response.status_code == 200 else None
            # print("短信发送结果:", result)  # 直接打印结果
            return verification_code
        except Exception as e:
            print(f"发送短信失败: {str(e)}")
            return None

    @staticmethod
    def parse_result(result):
        """
        解析短信发送结果
        :param result: 接口返回结果
        :return: 解析后的结果
        """
        if not result:
            return {'success': False, 'message': '请求失败'}
        
        code = result.get('code', 0)
        return {
            'success': code == 2,
            'code': code,
            'smsid': result.get('smsid', '0'),
            'message': result.get('msg', '未知错误')
        }