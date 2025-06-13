import time
from openai import OpenAI


class QwenOmniTurboClient:
    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        """
        初始化 Qwen-Omni-Turbo 客户端
        :param api_key: 百炼 API Key
        :param base_url: API 基础地址，默认使用兼容模式
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate_text(
            self,
            text: str,
            image_url: str = None,
            system_prompt: str = "You are a helpful assistant.",
            stream: bool = False,
            print_char_delay: float = 0.05
    ) -> str:
        """
        生成文本（支持图文多模态输入）
        :param text: 用户输入的文本指令
        :param image_url: 图片URL（可选）
        :param system_prompt: 系统提示词（默认简单助手）
        :param stream: 是否使用流式输出（逐字打印效果）
        :param print_char_delay: 逐字打印时的延迟秒数（stream=True时生效）
        :return: 生成的文本结果
        """
        # 构建消息内容
        content = []
        if image_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
        content.append({"type": "text", "text": text})

        # 调用API
        completion = self.client.chat.completions.create(
            model="qwen-omni-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            modalities=["text"],
            stream=stream
        )

        # 处理结果
        if stream:
            full_response = []
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_response.append(text_chunk)
                    for char in text_chunk:
                        print(char, end="", flush=True)
                        time.sleep(print_char_delay)
            print()  # 最后换行
            return "".join(full_response)
        else:
            return completion.choices[0].message.content
