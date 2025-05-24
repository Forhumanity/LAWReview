"""
配置管理模块
管理所有LLM API密钥、模型选择和全局参数
"""
import os
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class ReviewMode(Enum):
    """审查模式枚举"""
    REGULATION = "regulation"  # 法规审查：从法规中提取要求
    DOCUMENTATION = "documentation"  # 文档审查：检查文档是否满足要求


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7


@dataclass
class GlobalConfig:
    """全局配置"""
    # 审查模式
    review_mode: ReviewMode
    
    # LLM配置
    llm_configs: Dict[str, LLMConfig]
    
    # 路径配置
    input_path: str
    output_path: str
    
    # 处理参数
    categories_per_call: int = 2  # 每次API调用处理的类别数
    max_content_length: int = 15000  # 最大内容长度
    
    # 文件处理
    supported_extensions: tuple = ('.pdf', '.docx', '.doc', '.txt', '.md')
    
    # 输出格式
    save_individual_results: bool = True  # 是否保存每个LLM的单独结果
    save_consolidated_results: bool = True  # 是否保存合并结果
    

def get_default_config() -> GlobalConfig:
    """获取默认配置"""
    return GlobalConfig(
        review_mode=ReviewMode.REGULATION,
        llm_configs={
            "deepseek": LLMConfig(
                provider="deepseek",
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                model="deepseek-chat",
                base_url="https://api.deepseek.com"
            ),
            "openai": LLMConfig(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model="gpt-4o-mini",
                base_url=None
            ),
            "anthropic": LLMConfig(
                provider="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                model="claude-Opus-4-20250514",
                base_url=None
            )
        },
        input_path="./input_documents",
        output_path="./output_results",
        categories_per_call=2,
        max_content_length=15000
    )


def load_config_from_env() -> GlobalConfig:
    """从环境变量加载配置"""
    config = get_default_config()
    
    # 更新审查模式
    mode = os.getenv("REVIEW_MODE", "regulation").lower()
    config.review_mode = ReviewMode.REGULATION if mode == "regulation" else ReviewMode.DOCUMENTATION
    
    # 更新路径
    config.input_path = os.getenv("INPUT_PATH", config.input_path)
    config.output_path = os.getenv("OUTPUT_PATH", config.output_path)
    
    # 更新LLM配置
    for provider in ["deepseek", "openai", "anthropic"]:
        api_key_env = f"{provider.upper()}_API_KEY"
        model_env = f"{provider.upper()}_MODEL"
        
        if os.getenv(api_key_env):
            config.llm_configs[provider].api_key = os.getenv(api_key_env)
        if os.getenv(model_env):
            config.llm_configs[provider].model = os.getenv(model_env)
    
    return config