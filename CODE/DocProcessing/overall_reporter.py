"""
overall_reporter_anthropic.py
· 使用 Anthropic API（Claude 3 系列）生成合规总体报告
· 输出:
    ├── <doc>_overall.json   机器可读结构
    └── <doc>_overall.docx   格式化 Word
依赖:
    pip install anthropic python-docx

重要说明:
    使用RequirementID (1-35) 作为主键追踪风险类别，避免因文本名称差异导致的匹配问题
"""

from __future__ import annotations
import os, json, textwrap, collections, re
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import anthropic
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from prompt import REGULATORY_FRAMEWORK


# ───────────────────────── Anthropic 调用辅助 ─────────────────────────
def _call_anthropic(system_msg: str, user_msg: str,
                    model="claude-opus-4-20250514",
                    temperature=0.2,
                    max_tokens=1024,
                    api_key: str | None = None) -> str:
    """
    Wrapper: 返回纯字符串（去掉 ```json``` 包裹）
    """
    api_key='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'
    client = anthropic.Anthropic(api_key=api_key)
    
    # 判断是否需要JSON格式
    needs_json = "JSON" in user_msg or "json" in user_msg
    
    if needs_json:
        enhanced_user_msg = (
            user_msg +
            "\n\n请确保返回有效的JSON格式，不要包含markdown代码块标记，也不要额外解释。"
        )
    else:
        enhanced_user_msg = user_msg
        
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_msg,
        messages=[{"role": "user", "content": enhanced_user_msg}],
    )
    # content 可能是 list(blocks)
    if isinstance(msg.content, list):
        content = "".join(b.text for b in msg.content if hasattr(b, "text"))
    else:
        content = str(msg.content)
    content = content.strip()
    
    # 只有在需要JSON时才清理JSON标记
    if needs_json:
        if content.startswith("```json") and content.endswith("```"):
            content = content[7:-3].strip()
        elif content.startswith("```") and content.endswith("```"):
            content = content[3:-3].strip()
    
    return content


# ───────────────────────── JSON 解析辅助 ─────────────────────────
def _safe_json_loads(text: str) -> Dict:
    """更稳健地解析可能被额外文本包裹的JSON字符串"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        raise


# ───────────────────────── 分析报告解析 ─────────────────────────
def _parse_analysis_report(text: str) -> tuple[list[list[str]], list[list[str]]]:
    """将文本形式的分析报告解析为表格数据"""
    import re

    llm_rows: list[list[str]] = []
    cat_rows: list[list[str]] = []

    # 解析总体统计中的LLM数据
    llm_re = re.compile(
        r"^([A-Z]+):\s*$\n\s+- 平均得分: ([0-9.]+)\s*$\n\s+- 覆盖率: ([0-9.]+)%\s*$\n\s+- 高分项目数 .*: (\d+)",
        re.MULTILINE,
    )
    for m in llm_re.finditer(text):
        llm_rows.append([m.group(1), m.group(2), m.group(3) + "%", m.group(4)])

    # 解析类别分析部分
    cat_block_re = re.compile(
        r"^([一二三四五六七八]、[^:]+):\n((?:\s*[a-z]+: [^\n]+\n)+)",
        re.MULTILINE,
    )
    provider_re = re.compile(
        r"\s*(deepseek|openai|anthropic):\s*平均([0-9.]+)分,\s*最高([0-9.]+)分,\s*覆盖([0-9.]+)%"
    )

    for block in cat_block_re.finditer(text):
        cat = block.group(1)
        lines = block.group(2)
        for pm in provider_re.finditer(lines):
            cat_rows.append(
                [cat, pm.group(1), pm.group(2), pm.group(3), pm.group(4) + "%"]
            )

    return llm_rows, cat_rows


def _insert_table(doc: Document, headers: list[str], rows: list[list[str]]):
    """在文档中插入带标题的表格"""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.autofit = True

    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = header
        for paragraph in hdr_cells[i].paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.name = 'Arial'
                run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        shading_elm = OxmlElement('w:shd')
        shading_elm.set(qn('w:fill'), 'E0E0E0')
        hdr_cells[i]._element.get_or_add_tcPr().append(shading_elm)

    for row in rows:
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            row_cells[i].text = str(val)
            for paragraph in row_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.name = 'Times New Roman'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    return table


# ───────────────────────── 创建ID映射 ─────────────────────────
def _create_id_mappings():
    """
    创建ID到名称的映射和名称到ID的模糊匹配映射
    
    使用RequirementID (1-35) 作为主键的原因：
    - 避免因不同LLM返回的名称差异（如"与"和"和"的区别）导致的匹配失败
    - 确保所有36个风险子类别都被准确追踪和分析
    - 支持通过ID或名称查找要求
    """
    id_to_name = {}
    name_to_id = {}
    
    for cat, items in REGULATORY_FRAMEWORK.items():
        for item in items:
            id_to_name[item["number"]] = {
                "category": cat,
                "name": item["name"],
                "scope": item["scope"],
                "keyPoints": item["keyPoints"]
            }
            # 创建多个可能的名称变体用于匹配
            name_to_id[item["name"]] = item["number"]
            # 简化版本（去除标点）
            simplified = item["name"].replace("（", "(").replace("）", ")").replace("、", "")
            name_to_id[simplified] = item["number"]
    
    return id_to_name, name_to_id

def _find_requirement_id(name: str, name_to_id: dict) -> int | None:
    """根据名称查找requirement ID，支持模糊匹配"""
    # 精确匹配
    if name in name_to_id:
        return name_to_id[name]
    
    # 模糊匹配 - 查找包含关系
    for stored_name, req_id in name_to_id.items():
        if name in stored_name or stored_name in name:
            return req_id
    
    # 如果还找不到，尝试提取数字
    import re
    numbers = re.findall(r'\d+', name)
    if numbers and 1 <= int(numbers[0]) <= 35:
        return int(numbers[0])
    
    return None

# ───────────────────────── 数据聚合 ─────────────────────────
_COV_RANK = {"未覆盖": 1, "部分覆盖": 2, "完全覆盖": 3}

def _gather(json_path: Path):
    """解析综合 JSON → 覆盖矩阵、发现、建议"""
    raw = json.loads(Path(json_path).read_text(encoding="utf-8"))
    
    # 创建映射
    id_to_name, name_to_id = _create_id_mappings()
    
    # 使用ID作为key的覆盖矩阵
    cov_by_id = {}  # {req_id: {"coverage": lvl, "category": cat, "name": name}}
    findings, advice = [], []
    
    # 使用ID组织的详细数据
    detailed_data_by_id = collections.defaultdict(list)

    for pdata in raw["LLM分析结果"].values():
        # 覆盖
        for cat, items in pdata["详细分析"].items():
            for it in items:
                # 尝试获取requirement ID
                req_id = it.get("框架要求编号")
                if not req_id:
                    # 如果没有ID，尝试通过名称查找
                    req_id = _find_requirement_id(it.get("框架要求名称", ""), name_to_id)
                
                if req_id and req_id in id_to_name:
                    lvl = it["法规覆盖情况"]
                    
                    # 更新覆盖情况
                    if req_id not in cov_by_id or _COV_RANK[lvl] > _COV_RANK[cov_by_id[req_id]["coverage"]]:
                        cov_by_id[req_id] = {
                            "coverage": lvl,
                            "category": id_to_name[req_id]["category"],
                            "name": id_to_name[req_id]["name"]
                        }
                    
                    # 收集详细数据
                    detailed_data_by_id[req_id].append({
                        "覆盖情况": lvl,
                        "法规要求内容": it.get("法规要求内容", []),
                        "实施要求": it.get("实施要求", ""),
                        "处罚措施": it.get("处罚措施", "")
                    })
                
        findings.extend(pdata.get("关键发现", []))
        advice.extend(pdata.get("合规建议", []))

    # 转换回按类别组织的格式，确保所有36个子类别都被包含
    cov = collections.defaultdict(dict)
    detailed_data = collections.defaultdict(lambda: collections.defaultdict(list))
    
    # 确保所有36个要求都被包含
    for req_id, info in id_to_name.items():
        cat = info["category"]
        name = info["name"]
        
        if req_id in cov_by_id:
            cov[cat][name] = cov_by_id[req_id]["coverage"]
            detailed_data[cat][name] = detailed_data_by_id[req_id]
        else:
            # 未提及的要求标记为"未覆盖"
            cov[cat][name] = "未覆盖"
            detailed_data[cat][name] = [{
                "覆盖情况": "未覆盖",
                "法规要求内容": [],
                "实施要求": "该法规未涉及此要求",
                "处罚措施": "不适用"
            }]

    findings = list(dict.fromkeys(findings))  # 去重保持顺序
    advice   = list(dict.fromkeys(advice))
    return cov, findings, advice, detailed_data


# ───────────────────────── 逐大类评估 ─────────────────────────
def _build_category_reports(cov, findings, advice, detailed_data,
                            model="claude-opus-4-20250514") -> List[Dict]:
    reports = []
    
    # 构建子类别详细信息字符串
    def build_subcategory_details(cat, sub_map):
        details = []
        # 检查detailed_data中是否有该类别
        if cat in detailed_data:
            for sub_name, data_list in detailed_data[cat].items():
                sub_info = f"\n子类别：{sub_name}\n"
                for item in data_list:
                    if item["法规要求内容"]:
                        sub_info += f"  法规要求：\n"
                        for req in item["法规要求内容"]:
                            sub_info += f"    - 条款{req.get('条款编号', '')}：{req.get('具体要求', '')}\n"
                    if item["实施要求"]:
                        sub_info += f"  实施要求：{item['实施要求']}\n"
                    if item["处罚措施"]:
                        sub_info += f"  处罚措施：{item['处罚措施']}\n"
                details.append(sub_info)
        
        # 如果没有详细数据，返回说明
        if not details:
            return "该法规对此大类没有具体要求。"
        
        return "".join(details)
    
    # 确保所有8个大类都被分析
    for cat_name in REGULATORY_FRAMEWORK.keys():
        # 如果某个大类在cov中不存在，创建空的覆盖信息
        if cat_name not in cov:
            cov[cat_name] = {}
        
        sub_map = cov[cat_name]
        # 获取该大类的子类别信息
        cat_subcategories = REGULATORY_FRAMEWORK.get(cat_name, [])
        subcategory_info = "\n".join([
            f"- {sub['number']}. {sub['name']} (关注点: {sub['keyPoints']})"
            for sub in cat_subcategories
        ])
        
        # 确保所有子类别都在sub_map中（即使是"未覆盖"）
        for sub in cat_subcategories:
            if sub['name'] not in sub_map:
                sub_map[sub['name']] = "未覆盖"
        
        # 构建详细的子类别数据
        detailed_info = build_subcategory_details(cat_name, sub_map)
        
        prompt = textwrap.dedent(f"""
        你是一名资深法律分析专家，专注于企业境外投资合规法律分析。

        **重要说明**：
        1. 这是一个法律分析任务，你需要分析该法规对企业在特定风险类别下的要求，而不是评判法规本身的质量或完整性。
        2. 你的任务是理解和解释法规对企业的具体要求，如果法规对某个风险子类别没有要求，请明确说明"该法规对此子类别无相关要求"。
        3. 多个来源的信息可能重复、交叉或矛盾，请基于你的专业知识整合这些信息，识别真实有效的要求。
        4. 我们使用RequirementID (1-35)作为主键追踪各个风险子类别，确保分析的准确性。

        **当前分析的风险大类**：{cat_name}
        
        **该大类包含的子类别**：
        {subcategory_info}

        **收集到的覆盖情况**：
        {json.dumps(sub_map, ensure_ascii=False)}

        **该大类的详细法规要求**：
        {detailed_info}

        **整体关键发现**：{findings}
        **整体合规建议**：{advice}

        请返回以下格式的JSON（注意字段必须完全匹配）:
        {{
          "Category": "{cat_name}",
          "CategoryLawAnalysis": "针对该大类，综合分析法规的整体要求和规范重点（200-300字）",
          "SubCategoryAnalysis": {{
              "子类名称": {{
                  "Coverage": "覆盖等级（未覆盖/部分覆盖/完全覆盖）",
                  "LawRequirements": "法规对该子类的具体要求说明（如无要求，明确说明'该法规对此子类别无相关要求'）（100-150字）",
                  "KeyProvisions": ["关键条款1", "关键条款2"],
                  "CompliancePoints": ["合规要点1", "合规要点2"]
              }},
              ...（所有子类都需要分析）
          }},
          "CategoryComplianceGuidance": "基于法规要求，企业在该大类下应采取的合规措施建议（150-200字）"
        }}
        
        注意：
        - 对于每个子类别，即使法规没有相关要求，也要在SubCategoryAnalysis中包含该子类别
        - 明确区分"法规要求"（法规规定企业必须做什么）和"合规建议"（为满足法规要求，企业应该如何做）
        """)
        
        raw = _call_anthropic(
            system_msg="你是专业的法律分析专家，必须返回有效的JSON格式，严格按照要求的字段结构。",
            user_msg=prompt,
            model=model,
            max_tokens=2000,
        )
        reports.append(_safe_json_loads(raw))
    return reports


# ───────────────────────── Word 导出 ─────────────────────────
def _export_word(report: Dict, out_file: Path, image_dir: Path | None = None):
    """生成格式化的Word文档，包含适当的中文字体和表格样式"""
    doc = Document()
    
    # 设置文档默认字体
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_ALIGN_VERTICAL
    
    # 设置文档默认中文字体
    doc.styles['Normal'].font.name = 'Times New Roman'
    doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    doc.styles['Normal'].font.size = Pt(12)
    
    # 创建标题样式
    def create_heading_style(level, size):
        style = doc.styles[f'Heading {level}']
        style.font.name = 'Arial'
        style._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        style.font.size = Pt(size)
        style.font.bold = True
        if level == 1:
            style.font.color.rgb = RGBColor(0, 0, 0)
        else:
            style.font.color.rgb = RGBColor(51, 51, 51)
    
    create_heading_style(1, 16)
    create_heading_style(2, 14)
    create_heading_style(3, 12)
    
    # 添加文档标题
    title = doc.add_heading(f"{report['DocumentTitle']} - 法规要求分析报告", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].font.name = 'Arial'
    title.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    title.runs[0].font.size = Pt(20)
    
    # 添加分隔线
    doc.add_paragraph('_' * 80)
    
    # 添加报告说明
    doc.add_heading("报告说明", level=1)
    para = doc.add_paragraph(
        "本报告旨在分析该法规对企业境外投资在8大风险类别和36个子类别下的具体要求。"
        "报告重点说明法规规定了什么、要求企业做什么，以及企业应如何满足这些要求。"
    )
    para.paragraph_format.first_line_indent = Inches(0.5)
    para.paragraph_format.space_after = Pt(12)

    # 法规整体分析与合规实施建议（合并为一章）
    doc.add_heading("法规整体分析与合规实施建议", level=1)

    # 如有热力图和分析报告，插入于正文之前
    if image_dir:
        cat_img = next(Path(image_dir).glob("*分类汇总热力图.png"), None)
        det_img = next(Path(image_dir).glob("*详细热力图.png"), None)
        desc_map = {
            cat_img: "类别汇总热力图：展示各大风险类别在不同LLM的覆盖情况",
            det_img: "详细热力图：展示各风险子类别的综合得分分布",
        }
        for img in [cat_img, det_img]:
            if img and img.exists():
                doc.add_picture(str(img), width=Inches(6))
                p = doc.add_paragraph(desc_map[img])
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.runs[0].italic = True

        txt_file = next(Path(image_dir).glob("*分析报告.txt"), None)
        if txt_file and txt_file.exists():
            llm_rows, cat_rows = _parse_analysis_report(txt_file.read_text(encoding="utf-8"))
            if llm_rows:
                doc.add_heading("得分汇总", level=2)
                _insert_table(doc, ["LLM", "平均得分", "覆盖率", "高分项目数"], llm_rows)
            if cat_rows:
                doc.add_heading("各类别得分概览", level=2)
                _insert_table(doc, ["类别", "LLM", "平均得分", "最高得分", "覆盖率"], cat_rows)

    # 将整体分析内容分段显示
    analysis_text = report["OverallAnalysis"]
    
    # 处理文本中的标记
    sections = analysis_text.split("【")
    for section in sections:
        if section.strip():
            if "】" in section:
                # 这是一个带标题的段落
                title, content = section.split("】", 1)
                # 添加小标题
                heading = doc.add_heading(title, level=2)
                # 添加内容
                paras = content.strip().split("\n")
                for para_text in paras:
                    if para_text.strip():
                        para = doc.add_paragraph(para_text.strip())
                        para.paragraph_format.first_line_indent = Inches(0.5)
                        para.paragraph_format.space_after = Pt(8)
            else:
                # 普通段落
                paras = section.strip().split("\n")
                for para_text in paras:
                    if para_text.strip():
                        para = doc.add_paragraph(para_text.strip())
                        para.paragraph_format.first_line_indent = Inches(0.5)
                        para.paragraph_format.space_after = Pt(8)
    
    # 添加分页符
    doc.add_page_break()

    # 各大类详细分析
    for idx, cat in enumerate(report["CategoryReports"]):
        doc.add_heading(cat["Category"], level=1)
        
        # 大类整体分析
        doc.add_heading("大类法规要求概述", level=2)
        para = doc.add_paragraph(cat["CategoryLawAnalysis"])
        para.paragraph_format.first_line_indent = Inches(0.5)
        para.paragraph_format.space_after = Pt(12)
        
        # 子类别分析表格
        doc.add_heading("子类别法规要求分析", level=2)
        
        # 创建表格
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Light Grid Accent 1'  # 使用内置的专业表格样式
        table.autofit = True
        
        # 设置表头
        hdr_cells = table.rows[0].cells
        headers = ["子类别", "覆盖情况", "法规要求", "关键条款/合规要点"]
        for i, header in enumerate(headers):
            hdr_cells[i].text = header
            # 设置表头格式
            for paragraph in hdr_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.name = 'Arial'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
                    run.font.size = Pt(11)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # 设置表头背景色
            shading_elm = OxmlElement('w:shd')
            shading_elm.set(qn('w:fill'), 'E0E0E0')
            hdr_cells[i]._element.get_or_add_tcPr().append(shading_elm)
        
        # 添加数据行
        for sub, info in cat["SubCategoryAnalysis"].items():
            row_cells = table.add_row().cells
            
            # 子类别名称
            row_cells[0].text = sub
            row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
            
            # 覆盖情况 - 根据覆盖程度设置颜色
            coverage = info["Coverage"]
            row_cells[1].text = coverage
            para = row_cells[1].paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.runs[0]
            run.font.bold = True
            if coverage == "完全覆盖":
                run.font.color.rgb = RGBColor(0, 128, 0)  # 绿色
            elif coverage == "部分覆盖":
                run.font.color.rgb = RGBColor(255, 140, 0)  # 橙色
            else:  # 未覆盖
                run.font.color.rgb = RGBColor(255, 0, 0)  # 红色
            
            # 法规要求
            row_cells[2].text = info["LawRequirements"]
            row_cells[2].paragraphs[0].paragraph_format.space_after = Pt(6)
            
            # 关键条款/合规要点
            key_info = []
            if info.get("KeyProvisions"):
                key_info.append("【关键条款】\n" + "\n".join(f"• {p}" for p in info["KeyProvisions"]))
            if info.get("CompliancePoints"):
                key_info.append("【合规要点】\n" + "\n".join(f"• {p}" for p in info["CompliancePoints"]))
            row_cells[3].text = "\n\n".join(key_info) if key_info else "无"
            
            # 设置所有单元格的字体
            for cell in row_cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Times New Roman'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
                        run.font.size = Pt(10)
                    paragraph.paragraph_format.space_after = Pt(3)
                    paragraph.paragraph_format.space_before = Pt(3)
                cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
        
        # 设置列宽
        for i, width in enumerate([1.5, 1.0, 3.5, 2.5]):
            for cell in table.columns[i].cells:
                cell.width = Inches(width)
        
        # 大类合规指导
        doc.add_heading("合规措施建议", level=2)
        para = doc.add_paragraph(cat["CategoryComplianceGuidance"])
        para.paragraph_format.first_line_indent = Inches(0.5)
        para.paragraph_format.space_after = Pt(12)
        
        # 在每个大类后添加一些空间，但不要分页（除非是最后一个）
        if idx < len(report["CategoryReports"]) - 1:
            doc.add_paragraph()
            doc.add_paragraph()

    # 添加报告信息
    doc.add_paragraph()
    doc.add_paragraph('_' * 80)
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run(f"生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    footer.runs[0].font.size = Pt(9)
    footer.runs[0].font.color.rgb = RGBColor(128, 128, 128)
    
    # 设置所有表格的默认字体
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        if not run.font.name:
                            run.font.name = 'Times New Roman'
                            run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    # 保存文档
    doc.save(out_file)


# ───────────────────────── 对外主函数 ─────────────────────────
def generate_overall_report(json_path: str | Path,
                            model_cat="claude-opus-4-20250514",
                            model_doc="claude-opus-4-20250514") -> tuple[Path, Path]:
    """
    Returns (overall_json_path, overall_docx_path)
    """
    json_path = Path(json_path)
    cov, findings, advice, detailed_data = _gather(json_path)

    # 逐大类分析
    cat_reports = _build_category_reports(cov, findings, advice, detailed_data, model_cat)

    # 全文总体法规分析
    doc_prompt = textwrap.dedent(f"""
    你是一名资深法律分析专家，专注于企业境外投资合规法律分析。
    
    基于以下各大类的法规要求分析，请撰写一份综合分析报告。请直接输出纯文本内容，不要使用JSON格式。
    
    请按以下结构撰写（总计700-900字）：
    
    【法规整体分析】
    - 该法规的核心目的和规范重点
    - 法规对企业境外投资的主要要求领域
    - 法规的管理思路和监管重点
    
    【合规实施建议】
    - 基于法规要求，企业应建立的核心合规体系
    - 重点关注的合规领域和优先级
    - 实施这些合规要求的具体步骤建议
    
    各大类分析结果：
    {json.dumps(cat_reports, ensure_ascii=False)}
    
    请以专业、客观的语言撰写，重点说明法规要求了什么、企业应该做什么。
    直接输出文本内容，不要有任何JSON格式标记。
    """)
    
    overall_analysis = _call_anthropic(
        system_msg="你是专业的法律分析专家，请提供纯文本格式的专业分析，不要使用JSON格式。",
        user_msg=doc_prompt,
        model=model_doc,
        max_tokens=4000,
    )
    
    report = {
        "DocumentTitle": json_path.stem.replace("_综合分析结果", ""),
        "CategoryReports": cat_reports,
        "OverallAnalysis": overall_analysis.strip()
    }

    stem = json_path.stem
    out_json = json_path.parent / f"{stem}_overall.json"
    out_docx = json_path.parent / f"{stem}_overall.docx"

    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _export_word(report, out_docx, json_path.parent)

    return out_json, out_docx


"""
quick_test_anthropic.py
测试 overall_reporter_anthropic.generate_overall_report()
"""

# 你的相对 JSON 路径
json_file = (
    "Result/regulation_20250524_172749/境外投资管理办法/"
    "境外投资管理办法_综合分析结果.json"
)

if __name__ == "__main__":
    rep_json, rep_docx = generate_overall_report(json_file)
    print("\n生成成功:")
    print("  •", rep_json)
    print("  •", rep_docx)
