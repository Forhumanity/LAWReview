import unittest
import os
import sys
import types

sys.modules.setdefault('PyPDF2', types.SimpleNamespace(PdfReader=None))
sys.modules.setdefault('docx', types.SimpleNamespace(Document=lambda x: []))

class FakeMsg:
    def __init__(self, content):
        self.content = content

class FakeMessages:
    def create(self, *args, **kwargs):
        return FakeMsg("```json\n{\"a\":1}\n```")

class FakeAnthropic:
    def __init__(self, **kwargs):
        self.messages = FakeMessages()

sys.modules.setdefault('anthropic', types.SimpleNamespace(Anthropic=FakeAnthropic))

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "CODE"))

from base_analyzer import BaseAnalyzer
from config import GlobalConfig, LLMConfig, ReviewMode

class DummyAnalyzer(BaseAnalyzer):
    def create_analysis_prompt(self, document_content, framework_chunk):
        return ""

    def get_system_message(self):
        return ""

class TestAnthropicParsing(unittest.TestCase):
    def test_call_llm_strips_code_fences(self):
        cfg = GlobalConfig(review_mode=ReviewMode.REGULATION, llm_configs={}, input_path='', output_path='')
        analyzer = DummyAnalyzer(cfg)
        llm_cfg = LLMConfig(provider='anthropic', api_key='k', model='model')
        result = analyzer.call_llm(llm_cfg, 'sys', 'user')
        self.assertEqual(result, {"a": 1})

if __name__ == '__main__':
    unittest.main()
