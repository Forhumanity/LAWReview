import os
import sys
import types
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

sys.modules.setdefault('PyPDF2', types.SimpleNamespace(PdfReader=None))
sys.modules.setdefault('docx', types.SimpleNamespace(Document=None))

from base_analyzer import BaseAnalyzer
from config import GlobalConfig, LLMConfig, ReviewMode

class DummyAnalyzer(BaseAnalyzer):
    def create_analysis_prompt(self, document_content: str, framework_chunk: dict) -> str:
        return ""

    def get_system_message(self) -> str:
        return ""

def test_call_llm_parses_anthropic_response(monkeypatch):
    cfg = GlobalConfig(
        review_mode=ReviewMode.REGULATION,
        llm_configs={},
        input_path="",
        output_path="",
    )
    analyzer = DummyAnalyzer(cfg)
    llm = LLMConfig(provider="anthropic", api_key="key", model="model")

    def fake_call(self, llm_config, system_msg, user_msg):
        return "```json\n{\"ok\": true}\n```"

    monkeypatch.setattr(BaseAnalyzer, "_call_anthropic", fake_call)
    result = analyzer.call_llm(llm, "sys", "user")
    assert result == {"ok": True}
