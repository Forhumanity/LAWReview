"""
批量处理器
处理文件夹中的所有文档
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 为导入热力图生成器添加路径
import sys
VISUAL_DIR = Path(__file__).resolve().parents[1] / "VISUAL"
if str(VISUAL_DIR) not in sys.path:
    sys.path.append(str(VISUAL_DIR))

from config import GlobalConfig, ReviewMode
from regulation_analyzer import RegulationAnalyzer
from documentation_analyzer import DocumentationAnalyzer


class BatchProcessor:
    """批量文档处理器"""
    
    def __init__(self, config: GlobalConfig):
        self.config = config

        # 加载热力图生成器
        visual_dir = Path(__file__).resolve().parents[1] / "VISUAL"
        if str(visual_dir) not in sys.path:
            sys.path.append(str(visual_dir))
        from VISUAL.heatmap_generator import ComplianceHeatmapGenerator
        self.heatmap_generator = ComplianceHeatmapGenerator()
        
        # 根据模式选择分析器
        if config.review_mode == ReviewMode.REGULATION:
            self.analyzer = RegulationAnalyzer(config)
        else:
            self.analyzer = DocumentationAnalyzer(config)
        
        # 确保输出目录存在
        self.output_dir = Path(config.output_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建本次运行的输出子目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_output_dir = self.output_dir / f"{config.review_mode.value}_{timestamp}"
        self.run_output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化热力图生成器
        self.heatmap_generator = ComplianceHeatmapGenerator()
    
    def get_files_to_process(self) -> List[Path]:
        """获取需要处理的文件列表"""
        input_path = Path(self.config.input_path)
        
        if not input_path.exists():
            raise ValueError(f"输入路径不存在: {input_path}")
        
        files = set()
        if input_path.is_file():
            # 单个文件
            if input_path.suffix.lower() in self.config.supported_extensions:
                files.add(input_path)
        else:
            # 目录，使用rglob递归搜索并去重
            for ext in self.config.supported_extensions:
                for file in input_path.rglob(f"*{ext}"):
                    if file.is_file():
                        files.add(file)

        return sorted(files)
    
    def save_results(self, file_path: Path, results: Dict[str, Any]):
        """保存分析结果"""
        base_name = file_path.stem
        doc_dir = self.run_output_dir / base_name
        doc_dir.mkdir(parents=True, exist_ok=True)

        if self.config.save_consolidated_results:
            output_file = doc_dir / f"{base_name}_综合分析结果.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"  - 保存综合结果: {output_file}")
            # 根据综合结果生成热力图
            try:
                score_matrix = self.heatmap_generator.process_json_data(str(output_file))
                reg_name = self.heatmap_generator.get_regulation_name(str(output_file))
                safe_name = reg_name.replace('/', '_')
                self.heatmap_generator.create_heatmap(
                    score_matrix,
                    doc_dir / f"{safe_name}_详细热力图.png",
                    regulation_name=reg_name,
                )
                self.heatmap_generator.create_category_summary_heatmap(
                    score_matrix,
                    doc_dir / f"{safe_name}_分类汇总热力图.png",
                    regulation_name=reg_name,
                )
            except Exception as e:
                print(f"  - 生成热力图失败: {e}")

        # 保存各LLM的单独结果
        if self.config.save_individual_results:
            for provider, llm_result in results.get("LLM分析结果", {}).items():
                if isinstance(llm_result, dict) and "错误" not in llm_result:
                    individual_file = doc_dir / f"{base_name}_{provider}_分析结果.json"
                    with open(individual_file, 'w', encoding='utf-8') as f:
                        json.dump(llm_result, f, ensure_ascii=False, indent=2)
                    print(f"  - 保存{provider}结果: {individual_file}")

        # 根据综合结果生成热力图
        if output_file and output_file.exists():
            try:
                score_matrix = self.heatmap_generator.process_json_data(str(output_file))
                reg_name = self.heatmap_generator.get_regulation_name(str(output_file))
                safe_name = reg_name.replace('/', '_')

                self.heatmap_generator.create_heatmap(
                    score_matrix,
                    output_path=str(doc_dir / f"{safe_name}_详细热力图.png"),
                    regulation_name=reg_name,
                )
                self.heatmap_generator.create_category_summary_heatmap(
                    score_matrix,
                    output_path=str(doc_dir / f"{safe_name}_分类汇总热力图.png"),
                    regulation_name=reg_name,
                )
            except Exception as e:
                print(f"  - 生成热力图失败: {e}")
    
    def generate_summary_report(self, all_results: List[Dict[str, Any]]):
        """生成汇总报告"""
        summary = {
            "报告生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "审查模式": self.config.review_mode.value,
            "处理文件数": len(all_results),
            "文件列表": [],
            "LLM使用情况": {},
            "整体统计": {}
        }
        
        # 统计LLM使用情况
        llm_stats = {provider: {"成功": 0, "失败": 0} for provider in self.config.llm_configs.keys()}
        
        for result in all_results:
            file_info = {
                "文件名": result["文档名称"],
                "处理状态": "成功" if result.get("LLM分析结果") else "失败"
            }
            
            # 统计各LLM的结果
            for provider, llm_result in result.get("LLM分析结果", {}).items():
                if isinstance(llm_result, dict):
                    if "错误" in llm_result:
                        llm_stats[provider]["失败"] += 1
                    else:
                        llm_stats[provider]["成功"] += 1
                        
            summary["文件列表"].append(file_info)
        
        summary["LLM使用情况"] = llm_stats
        
        # 保存汇总报告
        summary_file = self.run_output_dir / "批处理汇总报告.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # 生成可读的文本报告
        self.generate_readable_report(summary)
        
        return summary
    
    def generate_readable_report(self, summary: Dict[str, Any]):
        """生成可读的文本报告"""
        report_lines = [
            "=" * 80,
            f"批处理分析报告",
            "=" * 80,
            f"生成时间: {summary['报告生成时间']}",
            f"审查模式: {'法规审查' if summary['审查模式'] == 'regulation' else '文档审查'}",
            f"处理文件数: {summary['处理文件数']}",
            "",
            "LLM使用情况:",
            "-" * 40
        ]
        
        for provider, stats in summary['LLM使用情况'].items():
            report_lines.append(
                f"{provider}: 成功 {stats['成功']} 个, 失败 {stats['失败']} 个"
            )
        
        report_lines.extend([
            "",
            "文件处理详情:",
            "-" * 40
        ])
        
        for file_info in summary['文件列表']:
            report_lines.append(
                f"- {file_info['文件名']}: {file_info['处理状态']}"
            )
        
        report_lines.append("=" * 80)
        
        # 保存文本报告
        report_file = self.run_output_dir / "批处理报告.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        # 打印到控制台
        print('\n'.join(report_lines))
    
    def process_all_files(self) -> List[Dict[str, Any]]:
        """处理所有文件"""
        files = self.get_files_to_process()
        
        if not files:
            print(f"在 {self.config.input_path} 中未找到支持的文件")
            return []
        
        print(f"找到 {len(files)} 个文件待处理")
        print(f"审查模式: {'法规审查' if self.config.review_mode == ReviewMode.REGULATION else '文档审查'}")
        print(f"输出目录: {self.run_output_dir}")
        print("-" * 80)
        
        all_results = []
        
        for i, file_path in enumerate(files, 1):
            print(f"\n处理文件 {i}/{len(files)}: {file_path.name}")
            
            try:
                # 使用所有LLM分析
                results = self.analyzer.analyze_with_all_llms(str(file_path))
                
                # 保存结果
                self.save_results(file_path, results)
                
                all_results.append(results)
                
            except Exception as e:
                print(f"处理文件时出错: {str(e)}")
                error_result = {
                    "文档名称": file_path.name,
                    "文档路径": str(file_path),
                    "错误": str(e),
                    "状态": "处理失败"
                }
                all_results.append(error_result)
        
        # 生成汇总报告
        print("\n" + "=" * 80)
        print("生成汇总报告...")
        self.generate_summary_report(all_results)
        
        return all_results