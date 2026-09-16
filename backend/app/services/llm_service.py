"""LLM服务模块"""

import time
from hello_agents import HelloAgentsLLM
from hello_agents.core.exceptions import HelloAgentsException
from ..config import get_settings

# 全局LLM实例
_llm_instance = None


class HelloAgentsLLMRetryProxy:
    """为 HelloAgentsLLM 提供简单 429 重试封装。"""

    def __init__(self, llm: HelloAgentsLLM, max_retries: int = 3, base_delay: float = 1.0):
        self._llm = llm
        self._max_retries = max_retries
        self._base_delay = base_delay

    def invoke(self, *args, **kwargs):
        last_exception = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return self._llm.invoke(*args, **kwargs)
            except HelloAgentsException as e:
                last_exception = e
                msg = str(e).lower()
                if any(term in msg for term in ["429", "rpm exhausted", "quota_exceeded", "quota exceeded", "rate limit"]):
                    if attempt == self._max_retries:
                        raise
                    delay = self._base_delay * attempt
                    print(f"⚠️ LLM rpm exhausted, retry {attempt}/{self._max_retries} after {delay:.1f}s")
                    time.sleep(delay)
                    continue
                raise
        raise last_exception

    def __getattr__(self, name):
        return getattr(self._llm, name)


def get_llm() -> HelloAgentsLLM:
    """
    获取LLM实例(单例模式)
    
    Returns:
        HelloAgentsLLM实例
    """
    global _llm_instance
    
    if _llm_instance is None:
        settings = get_settings()
        
        # HelloAgentsLLM会自动从环境变量读取配置
        base_llm = HelloAgentsLLM()
        _llm_instance = HelloAgentsLLMRetryProxy(base_llm)
        
        print(f"✅ LLM服务初始化成功")
        print(f"   提供商: {_llm_instance.provider}")
        print(f"   模型: {_llm_instance.model}")
    
    return _llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance
    _llm_instance = None

