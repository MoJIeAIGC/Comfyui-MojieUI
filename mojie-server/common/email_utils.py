import  yagmail
import configparser

# 读取配置文件
config = configparser.ConfigParser()
config.read('config/config.ini')

def send_test_email(receiver_email, verification_code):  # 添加 verification_code 参数
    """
    发送测试邮件
    :param receiver_email: 收件人邮箱地址
    :param verification_code: 验证码
    :return: 邮件发送成功返回 True，失败返回 False
    """
    try:
        # 从配置文件中获取发件人邮箱和授权码
        sender_email = config.get('email', 'sender_email')
        authorization_code = config.get('email', 'authorization_code')

        # 邮件主题和内容，包含验证码
        subject = '图灵摩诘'
        contents = f'欢迎注册奇画，您的验证码是：{verification_code}'

        # 初始化 yagmail 客户端
        yag = yagmail.SMTP(user=sender_email, password=authorization_code, host='smtp.exmail.qq.com')

        # 发送邮件
        yag.send(to=receiver_email, subject=subject, contents=contents)

        print('邮件发送成功')
        return True
    except Exception as e:
        print(f'邮件发送失败: {e}')
        return False