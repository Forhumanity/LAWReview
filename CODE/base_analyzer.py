"""
基础分析器类
提供文档读取、LLM调用等通用功能
"""
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import PyPDF2
import docx

from config import GlobalConfig, LLMConfig
from prompt import REGULATORY_FRAMEWORK

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import anthropic
except ImportError:
    anthropic = None


class BaseAnalyzer(ABC):
    """基础分析器抽象类"""
    
    def __init__(self, config: GlobalConfig):
        self.config = config
        self.framework = REGULATORY_FRAMEWORK
        
    def read_document(self, file_path: str) -> str:
        """读取文档内容"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            return self._read_pdf(path)
        elif ext in {".docx", ".doc"}:
            return self._read_docx(path)
        elif ext in {".txt", ".md"}:
            return self._read_text(path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
    
    def _read_pdf(self, file_path: Path) -> str:
        """读取PDF文件"""
        content = []
        with open(file_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content.append(text)
        return "\n".join(content)
    
    def _read_docx(self, file_path: Path) -> str:
        """读取Word文档"""
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    
    def _read_text(self, file_path: Path) -> str:
        """读取文本文件"""
        with open(file_path, "r", encoding="utf-8") as fh:
            return fh.read()
    
    def split_framework(self, chunk_size: int) -> List[Dict[str, Any]]:
        """将框架分成小块以避免token限制"""
        items = list(self.framework.items())
        return [dict(items[i:i + chunk_size]) for i in range(0, len(items), chunk_size)]
    
    def call_llm(self, llm_config: LLMConfig, system_msg: str, user_msg: str) -> Dict[str, Any]:
        """调用LLM并返回JSON响应"""
        if llm_config.provider in ["deepseek", "openai"]:
            content = self._call_openai_compatible(llm_config, system_msg, user_msg)
        elif llm_config.provider == "anthropic":
            content = self._call_anthropic(llm_config, system_msg, user_msg)
        else:
            raise ValueError(f"未知的LLM提供商: {llm_config.provider}")
        
        try:
            clean_content = content.strip()
            if clean_content.startswith("```") and clean_content.endswith("```"):
                clean_content = clean_content[3:-3].strip()
                if clean_content.lower().startswith("json"):
                    clean_content = clean_content[4:].strip()
            return json.loads(clean_content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"来自 {llm_config.provider} 的无效JSON响应: {exc}\n响应内容: {content}"
            ) from exc
    
    def _call_openai_compatible(self, llm_config: LLMConfig, system_msg: str, user_msg: str) -> str:
        """调用OpenAI兼容的API"""
        if OpenAI is None:
            raise RuntimeError("OpenAI库未安装")
        
        client = OpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url
        )
        
        response = client.chat.completions.create(
            model=llm_config.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )
        return response.choices[0].message.content
    
    def _call_anthropic(self, llm_config: LLMConfig, system_msg: str, user_msg: str) -> str:
        """调用Anthropic API"""
        if anthropic is None:
            raise RuntimeError("anthropic库未安装")
        
        client = anthropic.Anthropic(api_key=llm_config.api_key)
        msg = client.messages.create(
            model=llm_config.model,
            max_tokens=llm_config.max_tokens,
            temperature=llm_config.temperature,
            system=system_msg,
            messages=[{"role": "user", "content": user_msg}],
            response_format={"type": "json_object"},
        )

        if isinstance(msg.content, list):
            content = "".join(
                block.text for block in msg.content if hasattr(block, "text")
            )
        else:
            content = str(msg.content)

        content = content.strip()
        if content.startswith("```") and content.endswith("```"):
            content = content[3:-3].strip()
            if content.lower().startswith("json"):
                content = content[4:].strip()
        return content
    
    @abstractmethod
    def create_analysis_prompt(self, document_content: str, framework_chunk: Dict[str, Any]) -> str:
        """创建分析提示词 - 由子类实现"""
        pass
    
    @abstractmethod
    def get_system_message(self) -> str:
        """获取系统消息 - 由子类实现"""
        pass
    
    def analyze_with_single_llm(self, file_path: str, llm_config: LLMConfig) -> Dict[str, Any]:
        """使用单个LLM分析文档"""
        document_content = self.read_document(file_path)
        document_content = document_content[:self.config.max_content_length]
        
        system_msg = self.get_system_message()
        results: Dict[str, Any] = {
            "文档名称": Path(file_path).name,
            "分析日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "LLM提供商": llm_config.provider,
            "LLM模型": llm_config.model,
            "详细分析": {}
        }
        
        # 分块处理框架
        for chunk in self.split_framework(self.config.categories_per_call):
            prompt = self.create_analysis_prompt(document_content, chunk)
            try:
                chunk_result = self.call_llm(llm_config, system_msg, prompt)
                
                # 合并结果
                if "详细分析" in chunk_result:
                    results["详细分析"].update(chunk_result["详细分析"])
                
                # 合并其他字段
                for key, value in chunk_result.items():
                    if key not in ["详细分析", "文档名称", "分析日期"]:
                        results[key] = value
                        
            except Exception as e:
                print(f"处理 {llm_config.provider} 时出错: {str(e)}")
                results[f"错误_{llm_config.provider}"] = str(e)
        
        return results
    
    def analyze_with_all_llms(self, file_path: str) -> Dict[str, Any]:
        """使用所有配置的LLM分析文档"""
        all_results = {
            "文档路径": str(file_path),
            "文档名称": Path(file_path).name,
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "审查模式": self.config.review_mode.value,
            "LLM分析结果": {}
        }
        
        for provider, llm_config in self.config.llm_configs.items():
            if not llm_config.api_key:
                print(f"跳过 {provider}: 未配置API密钥")
                continue
            
            print(f"使用 {provider} 分析中...")
            try:
                result = self.analyze_with_single_llm(file_path, llm_config)
                all_results["LLM分析结果"][provider] = result
            except Exception as e:
                print(f"{provider} 分析失败: {str(e)}")
                all_results["LLM分析结果"][provider] = {
                    "错误": str(e),
                    "状态": "失败"
                }
        
        return all_results