import json
import os
from typing import Any, Dict
from pathlib import Path
from prompt import REGULATORY_FRAMEWORK

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

try:
    import anthropic
except ImportError:  # pragma: no cover - optional dependency
    anthropic = None  # type: ignore

import PyPDF2
import docx


class AIProvider:
    """Utility class to call different LLM providers with a unified interface."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _call_openai(
        self, base_url: str, model: str, system_msg: str, user_msg: str
    ) -> str:
        if OpenAI is None:
            raise RuntimeError("OpenAI library is not available")
        client = OpenAI(api_key=self.api_key, base_url=base_url or None)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=1,
            max_tokens=4000,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, model: str, system_msg: str, user_msg: str) -> str:
        if anthropic is None:
            raise RuntimeError("anthropic library is not available")
        client = anthropic.Anthropic(api_key=self.api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=1,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )
        return "".join(part.text for part in msg.content)

    def query(self, provider: str, system_msg: str, user_msg: str) -> Dict[str, Any]:
        """Call the selected provider and return the parsed JSON response."""
        if provider == "deepseek":
            content = self._call_openai(
                base_url="https://api.deepseek.com",
                model="deepseek-chat",
                system_msg=system_msg,
                user_msg=user_msg,
            )
        elif provider == "openai":
            content = self._call_openai(
                base_url="",
                model="gpt-4o-mini",
                system_msg=system_msg,
                user_msg=user_msg,
            )
        elif provider == "anthropic":
            content = self._call_anthropic(
                model="claude-opus-4-20250514",
                system_msg=system_msg,
                user_msg=user_msg,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON response from {provider}: {exc}") from exc


def call_llm(provider: str, system_message: str, user_message: str, api_key: str) -> Dict[str, Any]:
    """Public helper to query an LLM and return JSON."""
    client = AIProvider(api_key)
    return client.query(provider, system_message, user_message)

class RegulatoryDocumentAnalyzer:
    def __init__(self, api_key: str, provider: str = "deepseek"):
        self.api_key = api_key
        self.provider = provider
        self.framework = REGULATORY_FRAMEWORK

    def read_document(self, file_path: str) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext == ".pdf":
            return self._read_pdf(path)
        if ext in {".docx", ".doc"}:
            return self._read_docx(path)
        if ext in {".txt", ".md"}:
            return self._read_text(path)
        raise ValueError(f"Unsupported file format: {ext}")

    def _read_pdf(self, file_path: Path) -> str:
        content = []
        with open(file_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                content.append(page.extract_text())
        return "\n".join(content)

    def _read_docx(self, file_path: Path) -> str:
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    def _read_text(self, file_path: Path) -> str:
        with open(file_path, "r", encoding="utf-8") as fh:
            return fh.read()

    def split_framework(self, chunk_size: int) -> list[Dict[str, Any]]:
        """Split the framework into smaller chunks to avoid token limits."""
        items = list(self.framework.items())
        return [dict(items[i : i + chunk_size]) for i in range(0, len(items), chunk_size)]

    def create_analysis_prompt(
        self, document_content: str, framework: Dict[str, Any] | None = None
    ) -> str:
        framework = framework or self.framework
        return (
            "You are an expert in corporate governance, risk management, and compliance (GRC).\n\n"
            "Please analyze the following regulatory document against the predefined framework for overseas business risk management.\n\n"
            f"REGULATORY DOCUMENT CONTENT:\n{document_content[:15000]}\n\n"
            f"ANALYSIS FRAMEWORK:\n{json.dumps(framework, ensure_ascii=False, indent=2)}\n\n"
            "ANALYSIS REQUIREMENTS:\n"
            "1. For each category in the framework, evaluate whether the regulatory document addresses the requirements\n"
            "2. Assess the coverage level: \"Full\", \"Partial\", \"Not Covered\", or \"Not Applicable\"\n"
            "3. Extract relevant clauses or sections that address each requirement\n"
            "4. Identify any gaps or missing elements\n"
            "5. Provide recommendations for improvement\n\n"
            "Please structure your analysis in the following JSON format:\n"
            "{\n"
            "    \"document_title\": \"Title of the analyzed document\",\n"
            "    \"analysis_date\": \"YYYY-MM-DD\",\n"
            "    \"overall_assessment\": {\n"
            "        \"coverage_score\": \"Percentage of requirements covered\",\n"
            "        \"strengths\": [\"List of well-covered areas\"],\n"
            "        \"weaknesses\": [\"List of gaps or weaknesses\"]\n"
            "    },\n"
            "    \"detailed_analysis\": {\n"
            "        \"Category Name\": [\n"
            "            {\n"
            "                \"requirement_number\": 1,\n"
            "                \"requirement_name\": \"Requirement name from framework\",\n"
            "                \"coverage_level\": \"Full/Partial/Not Covered/Not Applicable\",\n"
            "                \"relevant_sections\": [\"Section or clause numbers/names\"],\n"
            "                \"key_findings\": \"What was found in the document\",\n"
            "                \"gaps\": \"What is missing\",\n"
            "                \"recommendations\": \"Specific improvements needed\"\n"
            "            }\n"
            "        ]\n"
            "    },\n"
            "    \"priority_actions\": [\"Top 5-10 priority actions to improve compliance\"]\n"
            "}\n\n"
            "Provide a thorough and detailed analysis."
        )

    def analyze_document(self, file_path: str, categories_per_call: int = 2) -> Dict[str, Any]:
        document_content = self.read_document(file_path)
        system_msg = (
            "You are a GRC expert specializing in overseas business risk management and regulatory compliance."
        )
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

    def save_analysis(self, analysis: Dict[str, Any], output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(analysis, fh, ensure_ascii=False, indent=2)
        print(f"Analysis saved to: {output_path}")

    def generate_summary_report(self, analysis: Dict[str, Any]) -> str:
        report: list[str] = []
        report.append("=" * 80)
        report.append("REGULATORY DOCUMENT ANALYSIS SUMMARY")
        report.append("=" * 80)
        report.append("")

        if "document_title" in analysis:
            report.append(f"Document: {analysis['document_title']}")
            report.append(f"Analysis Date: {analysis.get('analysis_date', 'N/A')}")
            report.append("")

        if "overall_assessment" in analysis:
            assessment = analysis["overall_assessment"]
            report.append("OVERALL ASSESSMENT")
            report.append("-" * 40)
            report.append(f"Coverage Score: {assessment.get('coverage_score', 'N/A')}")
            report.append("")

            if "strengths" in assessment:
                report.append("Strengths:")
                for strength in assessment["strengths"]:
                    report.append(f"  \u2022 {strength}")
                report.append("")

            if "weaknesses" in assessment:
                report.append("Weaknesses:")
                for weakness in assessment["weaknesses"]:
                    report.append(f"  \u2022 {weakness}")
                report.append("")

        if "priority_actions" in analysis:
            report.append("PRIORITY ACTIONS")
            report.append("-" * 40)
            for i, action in enumerate(analysis["priority_actions"], 1):
                report.append(f"{i}. {action}")
            report.append("")

        return "\n".join(report)


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "sk-6c47857f51a949d58473188b00e6f4aa")
    analyzer = RegulatoryDocumentAnalyzer(api_key)
    document_path = "国务院办公厅转发国家发展改革委商务部人民银行外交部关于进一步引导和规范境外投资方向指导意见的通知_对外经贸合作_中国政府网.pdf"
    try:
        analysis_results = analyzer.analyze_document(document_path)
        analyzer.save_analysis(analysis_results, "analysis_results.json")
        summary = analyzer.generate_summary_report(analysis_results)
        print(summary)
        with open("analysis_summary.txt", "w", encoding="utf-8") as fh:
            fh.write(summary)
    except Exception as exc:
        print(f"Error during analysis: {exc}")


if __name__ == "__main__":
    main()
