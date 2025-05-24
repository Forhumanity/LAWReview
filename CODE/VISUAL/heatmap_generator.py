"""
合规分析热力图生成器
基于JSON分析结果生成热力图，展示35个类别在不同LLM中的覆盖情况
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import matplotlib.font_manager as fm

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # 如果系统有中文字体，可以改为 ['SimHei'] 或 ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class ComplianceHeatmapGenerator:
    """合规分析热力图生成器"""
    
    def __init__(self):
        """初始化生成器"""
        # 定义所有35个类别
        self.categories = self._get_all_categories()
        
        # 定义评分权重
        self.weights = {
            'coverage': 0.4,      # 法规覆盖情况权重
            'mentions': 0.2,      # 提及次数权重
            'enforcement': 0.25,  # 强制等级权重
            'penalty': 0.15       # 处罚措施权重
        }
        
    def _get_all_categories(self) -> List[Tuple[str, List[str]]]:
        """获取所有35个类别的定义"""
        return [
            ("一、治理与战略", [
                "1. 海外业务治理与决策管理办法",
                "2. 董事会海外风险监督细则",
                "3. 海外子公司管理授权与责任制度",
                "4. 战略规划与投资决策流程规范"
            ]),
            ("二、全面风险管理", [
                "5. 海外全面风险管理基本制度",
                "6. 风险偏好与容忍度政策",
                "7. 风险识别评估与分级管理办法",
                "8. 风险监测预警与报告制度",
                "9. 风险应对与缓释措施管理办法",
                "10. 风险事件管理与调查制度",
                "11. 风险管理成熟度与绩效评估制度"
            ]),
            ("三、合规与法律", [
                "12. 全球合规管理体系文件（ISO 37301 对标）",
                "13. 反腐败与反贿赂政策",
                "14. 贸易制裁与出口管制合规指引",
                "15. 数据保护与隐私合规制度",
                "16. 竞争法与反垄断合规指引",
                "17. 第三方尽职调查和诚信审查程序"
            ]),
            ("四、财务与市场风险", [
                "18. 外汇风险管理政策",
                "19. 商品价格对冲管理办法",
                "20. 信用风险管理制度",
                "21. 资金集中与流动性管理办法"
            ]),
            ("五、运营与 HSE", [
                "22. 海外 HSE 管理体系标准",
                "23. 环境与气候变化管理办法（ESG）",
                "24. 生产安全事故预防与应急制度",
                "25. 供应链风险与可持续采购政策",
                "26. 设备资产完整性管理制度"
            ]),
            ("六、安全与危机", [
                "27. 海外安全防护与人员安保管理办法",
                "28. 危机管理与业务连续性计划(BCP)制度",
                "29. 政治风险保险与风险转移指引"
            ]),
            ("七、信息与网络安全", [
                "30. 网络安全与信息系统管理制度",
                "31. 工控系统安全规范",
                "32. 信息分类分级与保密管理办法"
            ]),
            ("八、社会责任与人力", [
                "33. 社区关系与社会责任(CSR)政策",
                "34. 人权与劳工标准政策",
                "35. 海外员工健康与福利管理制度"
            ])
        ]
    
    def calculate_relevance_score(self, item_data: Dict) -> float:
        """
        计算单个项目的相关性得分
        
        Args:
            item_data: 包含法规覆盖情况、要求内容、强制等级、处罚措施的字典
            
        Returns:
            相关性得分 (0-100)
        """
        score = 0
        
        # 1. 法规覆盖情况得分 (0-40分)
        coverage_map = {
            "完全覆盖": 40,
            "部分覆盖": 25,
            "未覆盖": 0,
            "未提及": 0,
            "不适用": 5
        }
        coverage = item_data.get("法规覆盖情况", "未覆盖")
        score += coverage_map.get(coverage, 0)
        
        # 2. 提及次数得分 (0-20分)
        mentions = len(item_data.get("法规要求内容", []))
        mention_score = min(mentions * 10, 20)  # 每个提及10分，最高20分
        score += mention_score
        
        # 3. 强制等级得分 (0-25分)
        enforcement_scores = []
        for content in item_data.get("法规要求内容", []):
            enforcement_map = {
                "强制": 25,
                "推荐": 15,
                "指导": 10
            }
            enforcement = content.get("强制等级", "")
            enforcement_scores.append(enforcement_map.get(enforcement, 0))
        
        if enforcement_scores:
            score += max(enforcement_scores)  # 取最高的强制等级得分
        
        # 4. 处罚措施得分 (0-15分)
        penalty = item_data.get("处罚措施", "")
        if penalty and penalty not in ["未明确", "未明确规定", "不适用", "无", ""]:
            score += 15
        elif penalty in ["未明确", "未明确规定"]:
            score += 5
        
        return min(score, 100)  # 确保总分不超过100
    
    def process_json_data(self, json_path: str) -> pd.DataFrame:
        """
        处理JSON数据并生成得分矩阵
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            包含得分的DataFrame
        """
        # 读取JSON数据
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 初始化得分矩阵
        llm_providers = ['deepseek', 'openai', 'anthropic']
        all_requirements = []
        for category, requirements in self.categories:
            all_requirements.extend(requirements)
        
        score_matrix = pd.DataFrame(
            index=all_requirements,
            columns=llm_providers,
            dtype=float
        )
        score_matrix.fillna(0, inplace=True)
        
        # 处理每个LLM的结果
        llm_results = data.get("LLM分析结果", {})
        
        for llm in llm_providers:
            if llm not in llm_results:
                continue
                
            llm_data = llm_results[llm]
            if "错误" in llm_data:
                continue
                
            detailed_analysis = llm_data.get("详细分析", {})
            
            # 处理每个类别
            for category_name, items in detailed_analysis.items():
                if not isinstance(items, list):
                    continue
                    
                for item in items:
                    # 获取要求编号和名称
                    req_number = item.get("框架要求编号", item.get("要求编号", 0))
                    req_name = item.get("框架要求名称", item.get("要求名称", ""))
                    
                    # 构建完整的要求标识
                    full_req_name = f"{req_number}. {req_name}"
                    
                    # 查找匹配的要求
                    for req in all_requirements:
                        if str(req_number) in req or req_name in req:
                            # 计算得分
                            score = self.calculate_relevance_score(item)
                            score_matrix.loc[req, llm] = score
                            break
        
        return score_matrix

    def get_regulation_name(self, json_path: str) -> str:
        """根据文件路径推断法规名称"""
        name = Path(json_path).stem
        name = name.replace("综合分析结果", "").replace("分析结果", "").rstrip("_")
        return name
    
    def create_heatmap(self, score_matrix: pd.DataFrame, output_path: str = None, regulation_name: Optional[str] = None):
        """
        创建热力图
        
        Args:
            score_matrix: 得分矩阵DataFrame
            output_path: 输出文件路径
        """
        # 创建图形
        fig, ax = plt.subplots(figsize=(10, 16))

        vmin = score_matrix.to_numpy().min()
        vmax = score_matrix.to_numpy().max()
        
        # 创建热力图
        sns.heatmap(
            score_matrix,
            annot=True,
            fmt='.0f',
            cmap='RdYlGn_r',
            cbar_kws={'label': 'Relevance Score (0-100)'},
            ax=ax,
            vmin=vmin,
            vmax=vmax,
            linewidths=0.5,
            linecolor='gray'
        )
        
        # 设置标题
        title = '\n法规合规覆盖热力图'
        if regulation_name:
            title = f"{regulation_name}\n法规合规覆盖热力图"
        ax.set_title(title, fontsize=16, pad=20)
        ax.set_xlabel('制度评审专家', fontsize=12)
        ax.set_ylabel('风险梳理框架', fontsize=12)
        
        # 旋转x轴标签
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, ha='center')
        
        # 调整y轴标签
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=8)
        
        # 添加类别分隔线
        category_positions = []
        current_pos = 0
        for category, requirements in self.categories:
            current_pos += len(requirements)
            category_positions.append(current_pos)
        
        # 绘制分隔线
        for pos in category_positions[:-1]:
            ax.axhline(y=pos, color='black', linewidth=2)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存或显示
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"热力图已保存到: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def create_category_summary_heatmap(self, score_matrix: pd.DataFrame, output_path: str = None, regulation_name: Optional[str] = None):
        """
        创建按类别汇总的热力图
        
        Args:
            score_matrix: 得分矩阵DataFrame
            output_path: 输出文件路径
        """
        # 按类别汇总得分
        category_scores = pd.DataFrame(
            columns=score_matrix.columns,
            dtype=float
        )
        
        for category_name, requirements in self.categories:
            # 计算该类别下所有要求的平均得分
            category_req_scores = []
            for req in requirements:
                if req in score_matrix.index:
                    category_req_scores.append(score_matrix.loc[req])
            
            if category_req_scores:
                avg_scores = pd.concat(category_req_scores, axis=1).mean(axis=1)
                category_scores.loc[category_name] = avg_scores
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(8, 10))
        vmin = score_matrix.to_numpy().min()
        vmax = score_matrix.to_numpy().max()
        # 创建热力图
        sns.heatmap(
            category_scores,
            annot=True,
            fmt='.1f',
            cmap='RdYlGn_r',
            cbar_kws={'label': 'Average Relevance Score (0-100)'},
            ax=ax,
            vmin=vmin,
            vmax=vmax,
            linewidths=1,
            linecolor='white'
        )
        
        title = 'Regulatory Compliance Coverage by Category\n法规合规覆盖分类汇总'
        if regulation_name:
            title = f"{regulation_name}\n" + title
        ax.set_title(title, fontsize=16, pad=20)
        ax.set_xlabel('LLM Providers', fontsize=12)
        ax.set_ylabel('Compliance Categories', fontsize=12)
        
        # 旋转标签
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, ha='center')
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存或显示
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"类别汇总热力图已保存到: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_analysis_report(self, score_matrix: pd.DataFrame, output_path: str = None, regulation_name: Optional[str] = None):
        """
        生成分析报告
        
        Args:
            score_matrix: 得分矩阵DataFrame
            output_path: 输出文件路径
        """
        report = []
        report.append("=" * 80)
        header = "法规合规覆盖分析报告"
        if regulation_name:
            header = f"{regulation_name} {header}"
        report.append(header)
        report.append("=" * 80)
        report.append("")
        
        # 总体统计
        report.append("一、总体统计")
        report.append("-" * 40)
        
        for llm in score_matrix.columns:
            avg_score = score_matrix[llm].mean()
            coverage_rate = (score_matrix[llm] > 0).sum() / len(score_matrix) * 100
            high_score_count = (score_matrix[llm] >= 60).sum()
            
            report.append(f"\n{llm.upper()}:")
            report.append(f"  - 平均得分: {avg_score:.1f}")
            report.append(f"  - 覆盖率: {coverage_rate:.1f}%")
            report.append(f"  - 高分项目数 (≥60): {high_score_count}")
        
        # 类别分析
        report.append("\n\n二、类别分析")
        report.append("-" * 40)
        
        for category_name, requirements in self.categories:
            report.append(f"\n{category_name}:")
            
            # 计算该类别的统计信息
            category_scores = {}
            for llm in score_matrix.columns:
                scores = []
                for req in requirements:
                    if req in score_matrix.index:
                        scores.append(score_matrix.loc[req, llm])
                
                if scores:
                    category_scores[llm] = {
                        'avg': np.mean(scores),
                        'max': np.max(scores),
                        'coverage': sum(s > 0 for s in scores) / len(scores) * 100
                    }
            
            for llm, stats in category_scores.items():
                report.append(f"  {llm}: 平均{stats['avg']:.1f}分, "
                            f"最高{stats['max']:.0f}分, "
                            f"覆盖{stats['coverage']:.0f}%")
        
        # 重点发现
        report.append("\n\n三、重点发现")
        report.append("-" * 40)
        
        # 找出得分最高和最低的项目
        all_scores = []
        for req in score_matrix.index:
            for llm in score_matrix.columns:
                score = score_matrix.loc[req, llm]
                if score > 0:
                    all_scores.append((req, llm, score))
        
        all_scores.sort(key=lambda x: x[2], reverse=True)
        
        report.append("\n最高覆盖的要求 (Top 5):")
        for req, llm, score in all_scores[:5]:
            report.append(f"  - {req} ({llm}): {score:.0f}分")
        
        report.append("\n未覆盖或低覆盖的要求:")
        uncovered = []
        for req in score_matrix.index:
            max_score = score_matrix.loc[req].max()
            if max_score < 10:
                uncovered.append(req)
        
        for req in uncovered[:10]:  # 只显示前10个
            report.append(f"  - {req}")
        
        if len(uncovered) > 10:
            report.append(f"  ... 以及其他 {len(uncovered) - 10} 项")
        
        # 保存报告
        report_text = '\n'.join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"分析报告已保存到: {output_path}")
        else:
            print(report_text)
        
        return report_text


def main():
    """主函数"""
    # 创建生成器
    generator = ComplianceHeatmapGenerator()
    
    # 处理JSON数据
    json_path = "Result/regulation_20250524_112352/关于进一步引导和规范境外投资方向指导意见_综合分析结果.json"
    regulation_name = generator.get_regulation_name(json_path)
    
    try:
        # 生成得分矩阵
        print("正在处理JSON数据...")
        score_matrix = generator.process_json_data(json_path)
        
        # 生成详细热力图
        print("正在生成详细热力图...")
        safe_name = regulation_name.replace('/', '_')
        generator.create_heatmap(
            score_matrix,
            output_path=f"{safe_name}_详细热力图.png",
            regulation_name=regulation_name
        )
        
        # 生成类别汇总热力图
        print("正在生成类别汇总热力图...")
        generator.create_category_summary_heatmap(
            score_matrix,
            output_path=f"{safe_name}_分类汇总热力图.png",
            regulation_name=regulation_name
        )
        
        # 生成分析报告
        print("正在生成分析报告...")
        generator.generate_analysis_report(
            score_matrix,
            output_path=f"{safe_name}_分析报告.txt",
            regulation_name=regulation_name
        )
        
        print("\n所有文件已生成完成！")
        
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
