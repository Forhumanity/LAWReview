import json
from typing import Any, Dict

from doc import RegulatoryDocumentAnalyzer, call_llm


class GovernmentRegulationAnalyzer(RegulatoryDocumentAnalyzer):
    """Analyzer tailored for government regulations with Chinese output."""

    def create_analysis_prompt(
        self, document_content: str, framework: Dict[str, Any] | None = None
    ) -> str:
        framework = framework or self.framework
        return (
            "你是一名政府监管专家，请根据以下监管框架审阅给出的法规内容，"
            "判断其是否覆盖各项要求并提供相应章节和句子。\n\n"
            f"法规内容:\n{document_content[:15000]}\n\n"
            f"分析框架:\n{json.dumps(framework, ensure_ascii=False, indent=2)}\n\n"
            "分析要求:\n"
            "1. 对每项要求说明法规是否提及，并评估其相关性和细化程度；\n"
            "2. 给出对应的章节和句子；\n"
            "3. 根据情况给出覆蓋等级：\"完全覆盖\"、\"部分覆盖\"、\"未提及\"或\"不适用\"；\n"
            "4. 如有不足，提供改进建议；\n\n"
            "请按照以下 JSON 格式、使用中文返回结果：\n"
            "{\n"
            "  \"document_title\": \"文档标题\",\n"
            "  \"analysis_date\": \"YYYY-MM-DD\",\n"
            "  \"detailed_analysis\": {\n"
            "    \"分类名称\": [\n"
            "      {\n"
            "        \"requirement_number\": 1,\n"
            "        \"requirement_name\": \"框架要求名称\",\n"
            "        \"coverage_level\": \"完全覆盖/部分覆盖/未提及/不适用\",\n"
            "        \"relevance\": \"高/中/低\",\n"
            "        \"detail_level\": \"高/中/低\",\n"
            "        \"relevant_sentences\": [\"原文句子\"],\n"
            "        \"sections\": [\"章节或条款\"],\n"
            "        \"recommendations\": \"改进建议\"\n"
            "      }\n"
            "    ]\n"
            "  }\n"
            "}\n"
        )

    def analyze_document(self, file_path: str, categories_per_call: int = 2) -> Dict[str, Any]:
        document_content = self.read_document(file_path)
        system_msg = "你是政府监管合规专家，请使用中文回复。"
        results: Dict[str, Any] = {}
        for chunk in self.split_framework(categories_per_call):
            prompt = self.create_analysis_prompt(document_content, chunk)
            part = call_llm(self.provider, system_msg, prompt, self.api_key)
            for key, value in part.items():
                if (
                    key in results
                    and isinstance(value, dict)
                    and isinstance(results[key], dict)
                ):
                    results[key].update(value)
                elif (
                    key in results
                    and isinstance(value, list)
                    and isinstance(results[key], list)
                ):
                    results[key].extend(value)
                else:
                    results[key] = value
        return results


def main() -> None:
    import os
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    analyzer = GovernmentRegulationAnalyzer(api_key)
    document_path = "path/to/your/government-regulation.pdf"
    try:
        analysis_results = analyzer.analyze_document(document_path)
        analyzer.save_analysis(analysis_results, "regulation_analysis.json")
        summary = analyzer.generate_summary_report(analysis_results)
        print(summary)
    except Exception as exc:
        print(f"Error during analysis: {exc}")


if __name__ == "__main__":
    main()
