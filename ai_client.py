"""
ai_client.py
AI 接口封装模块
支持所有兼容 OpenAI 接口格式的大模型：
ChatGPT / DeepSeek / Kimi / 通义千问 / 智谱 GLM / 文心一言 等
"""

import time
import logging
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class AIClient:
    """
    封装 OpenAI 兼容接口的 AI 客户端。
    内置自动重试机制，应对网络抖动和限流错误。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        timeout: int = 120,
        request_delay: float = 0.5,
    ):
        self.model_name = model_name
        self.request_delay = request_delay

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        """
        发送一次对话请求，返回 AI 的文本回复。
        temperature 设置较低（0.3）以保证输出的稳定性和一致性。
        """
        response = self._chat_with_retry(system_prompt, user_message, temperature)
        time.sleep(self.request_delay)
        return response

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _chat_with_retry(
        self, system_prompt: str, user_message: str, temperature: float
    ) -> str:
        """带自动重试的实际请求方法（最多重试5次，指数退避）。"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    def test_connection(self) -> bool:
        """测试 API 连接是否正常。"""
        try:
            result = self.chat(
                system_prompt="你是一个助手。",
                user_message="请回复'连接成功'这四个字。",
            )
            return "连接成功" in result or len(result) > 0
        except Exception as e:
            logger.error(f"API 连接测试失败: {e}")
            return False
