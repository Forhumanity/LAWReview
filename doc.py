import json
import os
from typing import Any, Dict
from pathlib import Path

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
  
# Framework definition based on the Excel file
REGULATORY_FRAMEWORK = {
    "一、治理与战略": [
        {"number": 1, "name": "海外业务治理与决策管理办法", "scope": "董事会、海外事业部", "keyPoints": "决策层级、重大事项清单、决策流程、监管备案"},
        {"number": 2, "name": "董事会海外风险监督细则", "scope": "董事会审计与风险委员会", "keyPoints": "年度风险计划、监督频次、信息披露要求"},
        {"number": 3, "name": "海外子公司管理授权与责任制度", "scope": "海外子公司/项目公司", "keyPoints": "\u201c三道防线\u201d职责、授权限额、越级报告通道"},
        {"number": 4, "name": "战略规划与投资决策流程规范", "scope": "战略部、投资部", "keyPoints": "立项准入标准、可研模板、风险-回报阈值"}
    ],
    "二、全面风险管理": [
        {"number": 5, "name": "海外全面风险管理基本制度", "scope": "全体海外单位", "keyPoints": "风险管理目标、原则、流程与角色说明"},
        {"number": 6, "name": "风险偏好与容忍度政策", "scope": "高管层", "keyPoints": "各类风险限额、红线指标设定及调整机制"},
        {"number": 7, "name": "风险识别评估与分级管理办法", "scope": "风控部、各业务线", "keyPoints": "分级标准、5\u00d75 \u77e9\u9635、评估频次、工作底稿"},
        {"number": 8, "name": "风险监测预警与报告制度", "scope": "风控、财务、运营", "keyPoints": "KRI\u91c7\u96c6\u53e3\u5f84\u3001\u9600\u503c\u989c\u8272\u706f\u53f7\u3001\u9884\u8b66\u6d41\u7a0b"},
        {"number": 9, "name": "风险应对与缓释措施管理办法", "scope": "责任部门", "keyPoints": "规避/减缓/转移/接受策略、资源审批"},
        {"number": 10, "name": "风险事件管理与调查制度", "scope": "安全、法务、审计", "keyPoints": "事件分级、调查程序、经验教训共享"},
        {"number": 11, "name": "风险管理成熟度与绩效评估制度", "scope": "审计部", "keyPoints": "COSO 要素评分模型、改进闭环"}
    ],
    "三、合规与法律": [
        {"number": 12, "name": "全球合规管理体系文件（ISO 37301 对标）", "scope": "法务与各海外单位", "keyPoints": "合规风险评估、监测、报告、文化建设"},
        {"number": 13, "name": "反腐败与反贿赂政策", "scope": "全员及第三方", "keyPoints": "禁止行为清单、礼品与待客上限、举报渠道"},
        {"number": 14, "name": "贸易制裁与出口管制合规指引", "scope": "采购、贸易", "keyPoints": "制裁名单筛查、双用途物项管控、许可管理"},
        {"number": 15, "name": "数据保护与隐私合规制度", "scope": "IT、HR、营销", "keyPoints": "个人信息分类、跨境传输、数据主体权利"},
        {"number": 16, "name": "竞争法与反垄断合规指引", "scope": "销售、采购", "keyPoints": "禁止垄断协议、信息交换边界、 dawn-raid 应对"},
        {"number": 17, "name": "第三方尽职调查和诚信审查程序", "scope": "采购、投融资", "keyPoints": "风险评分模型、分层尽调、持续监控"}
    ],
    "四、财务与市场风险": [
        {"number": 18, "name": "外汇风险管理政策", "scope": "财务总部与各海外财务", "keyPoints": "敞口识别、套保工具、VAR 监控"},
        {"number": 19, "name": "商品价格对冲管理办法", "scope": "贸易、财务", "keyPoints": "套期保值策略、对冲授权、绩效评估"},
        {"number": 20, "name": "信用风险管理制度", "scope": "贸易、财务", "keyPoints": "客户评级模型、授信限额、坏账准备"},
        {"number": 21, "name": "资金集中与流动性管理办法", "scope": "财务共享", "keyPoints": "现金池、融资安排、备付金底线"}
    ],
    "五、运营与 HSE": [
        {"number": 22, "name": "海外 HSE 管理体系标准", "scope": "全体生产经营单位", "keyPoints": "安全责任、风险评价、作业许可、PPE"},
        {"number": 23, "name": "环境与气候变化管理办法（ESG）", "scope": "HSE、能源", "keyPoints": "绿色矿山、碳排放目标、信息披露"},
        {"number": 24, "name": "生产安全事故预防与应急制度", "scope": "矿山、冶炼", "keyPoints": "SOP、应急响应级别、演练计划"},
        {"number": 25, "name": "供应链风险与可持续采购政策", "scope": "采购、物流", "keyPoints": "供应商 ESG 准入、产地溯源、童工禁限"},
        {"number": 26, "name": "设备资产完整性管理制度", "scope": "生产技术", "keyPoints": "关键设备定检、状态监测、残余寿命评估"}
    ],
    "六、安全与危机": [
        {"number": 27, "name": "海外安全防护与人员安保管理办法", "scope": "安全保卫部", "keyPoints": "护卫级别、外派人员培训、承包商准入"},
        {"number": 28, "name": "危机管理与业务连续性计划(BCP)制度", "scope": "各单位", "keyPoints": "情景触发条件、指挥链条、备份设施"},
        {"number": 29, "name": "政治风险保险与风险转移指引", "scope": "保险、财务", "keyPoints": "适用情形、投保流程、索赔协作"}
    ],
    "七、信息与网络安全": [
        {"number": 30, "name": "网络安全与信息系统管理制度", "scope": "IT部", "keyPoints": "等保合规、漏洞管理、日志留存"},
        {"number": 31, "name": "工控系统安全规范", "scope": "冶炼、电解", "keyPoints": "分层隔离、白名单、补丁管理"},
        {"number": 32, "name": "信息分类分级与保密管理办法", "scope": "全员", "keyPoints": "信息分级规则、涉密载体管控、泄密处置"}
    ],
    "八、社会责任与人力": [
        {"number": 33, "name": "社区关系与社会责任(CSR)政策", "scope": "ESG 委员会", "keyPoints": "社区沟通、基础设施支持、公益投入"},
        {"number": 34, "name": "人权与劳工标准政策", "scope": "HR、供应链", "keyPoints": "国际劳工公约、平等雇佣、强迫劳动禁令"},
        {"number": 35, "name": "海外员工健康与福利管理制度", "scope": "HR、HSE", "keyPoints": "医疗保险、心理援助、疫病预案"}
    ]
}


class RegulatoryDocumentAnalyzer:
    def __init__(self, api_key: str, provider: str = "openai"):
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

    def create_analysis_prompt(self, document_content: str) -> str:
        return f"""You are an expert in corporate governance, risk management, and compliance (GRC).\n\nPlease analyze the following regulatory document against the predefined framework for overseas business risk management.\n\nREGULATORY DOCUMENT CONTENT:\n{document_content[:15000]}\n\nANALYSIS FRAMEWORK:\n{json.dumps(self.framework, ensure_ascii=False, indent=2)}\n\nANALYSIS REQUIREMENTS:\n1. For each category in the framework, evaluate whether the regulatory document addresses the requirements\n2. Assess the coverage level: \"Full\", \"Partial\", \"Not Covered\", or \"Not Applicable\"\n3. Extract relevant clauses or sections that address each requirement\n4. Identify any gaps or missing elements\n5. Provide recommendations for improvement\n\nPlease structure your analysis in the following JSON format:\n{{\n    \"document_title\": \"Title of the analyzed document\",\n    \"analysis_date\": \"YYYY-MM-DD\",\n    \"overall_assessment\": {{\n        \"coverage_score\": \"Percentage of requirements covered\",\n        \"strengths\": [\"List of well-covered areas\"],\n        \"weaknesses\": [\"List of gaps or weaknesses\"]\n    }},\n    \"detailed_analysis\": {{\n        \"Category Name\": [\n            {{\n                \"requirement_number\": 1,\n                \"requirement_name\": \"Requirement name from framework\",\n                \"coverage_level\": \"Full/Partial/Not Covered/Not Applicable\",\n                \"relevant_sections\": [\"Section or clause numbers/names\"],\n                \"key_findings\": \"What was found in the document\",\n                \"gaps\": \"What is missing\",\n                \"recommendations\": \"Specific improvements needed\"\n            }}\n        ]\n    }},\n    \"priority_actions\": [\"Top 5-10 priority actions to improve compliance\"]\n}}\n\nProvide a thorough and detailed analysis."""

    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        document_content = self.read_document(file_path)
        prompt = self.create_analysis_prompt(document_content)
        system_msg = (
            "You are a GRC expert specializing in overseas business risk management and regulatory compliance."
        )
        return call_llm(self.provider, system_msg, prompt, self.api_key)

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
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    analyzer = RegulatoryDocumentAnalyzer(api_key)
    document_path = "path/to/your/regulatory-document.pdf"
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
