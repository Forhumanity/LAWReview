"""
快速生成合规热力图的简化版本
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib

# 配置matplotlib以支持中文
matplotlib.rcParams['font.family'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# 如果系统安装了中文字体，取消下面的注释
# plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows
# plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # macOS
# plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']  # Linux


def load_json_data(json_path):
    """加载JSON数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_score(item):
    """计算单个项目的得分"""
    score = 0
    
    # 覆盖情况得分
    coverage_scores = {
        "完全覆盖": 40,
        "部分覆盖": 25,
        "未覆盖": 0,
        "未提及": 0,
        "不适用": 5
    }
    coverage = item.get("法规覆盖情况", "未覆盖")
    score += coverage_scores.get(coverage, 0)
    
    # 提及次数得分
    mentions = len(item.get("法规要求内容", []))
    score += min(mentions * 10, 30)
    
    # 强制等级得分
    enforcement_scores = {
        "强制": 20,
        "推荐": 10,
        "指导": 5
    }
    
    for content in item.get("法规要求内容", []):
        enforcement = content.get("强制等级", "")
        score += enforcement_scores.get(enforcement, 0) / max(1, mentions)
    
    # 处罚措施得分
    penalty = item.get("处罚措施", "")
    if penalty and penalty not in ["未明确", "未明确规定", "不适用", "无", ""]:
        score += 10
    
    return min(score, 100)


def create_simple_heatmap(json_path, save_path="heatmap.png"):
    """创建简化版热力图"""
    # 加载数据
    data = load_json_data(json_path)
    llm_results = data.get("LLM分析结果", {})
    
    # 收集所有类别
    all_categories = set()
    for llm_name, llm_data in llm_results.items():
        if "详细分析" in llm_data:
            all_categories.update(llm_data["详细分析"].keys())
    
    all_categories = sorted(list(all_categories))
    
    # 创建得分矩阵
    score_data = []
    category_labels = []
    
    for category in all_categories:
        category_scores = []
        
        for llm in ['deepseek', 'openai', 'anthropic']:
            if llm not in llm_results:
                category_scores.append(0)
                continue
            
            llm_data = llm_results[llm]
            if "错误" in llm_data:
                category_scores.append(0)
                continue
            
            detailed = llm_data.get("详细分析", {})
            if category in detailed:
                items = detailed[category]
                if isinstance(items, list) and items:
                    # 计算该类别的平均得分
                    scores = [calculate_score(item) for item in items]
                    avg_score = np.mean(scores) if scores else 0
                    category_scores.append(avg_score)
                else:
                    category_scores.append(0)
            else:
                category_scores.append(0)
        
        score_data.append(category_scores)
        # 简化类别名称以便显示
        simple_name = category.replace("、", ".")
        category_labels.append(simple_name)
    
    # 创建DataFrame
    df = pd.DataFrame(
        score_data,
        columns=['DeepSeek', 'OpenAI', 'Anthropic'],
        index=category_labels
    )
    
    # 创建热力图
    plt.figure(figsize=(8, 10))
    
    # 使用自定义颜色映射
    colors = ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', 
              '#4292c6', '#2171b5', '#08519c', '#08306b']
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("custom", colors)
    
    # 绘制热力图
    ax = sns.heatmap(
        df,
        annot=True,
        fmt='.0f',
        cmap=cmap,
        cbar_kws={'label': 'Score (0-100)'},
        vmin=0,
        vmax=100,
        linewidths=1,
        linecolor='white',
        square=True
    )
    
    # 设置标题和标签
    plt.title('Compliance Coverage Analysis\n合规覆盖分析', fontsize=14, pad=20)
    plt.xlabel('LLM Models', fontsize=12)
    plt.ylabel('Categories', fontsize=12)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图片
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"热力图已保存到: {save_path}")
    
    # 显示图片
    plt.show()
    
    return df


def create_requirement_level_heatmap(json_path, save_path="requirement_heatmap.png"):
    """创建基于35个具体要求的热力图"""
    # 定义所有35个要求
    all_requirements = [
        "1. 海外业务治理与决策管理办法",
        "2. 董事会海外风险监督细则",
        "3. 海外子公司管理授权与责任制度",
        "4. 战略规划与投资决策流程规范",
        "5. 海外全面风险管理基本制度",
        "6. 风险偏好与容忍度政策",
        "7. 风险识别评估与分级管理办法",
        "8. 风险监测预警与报告制度",
        "9. 风险应对与缓释措施管理办法",
        "10. 风险事件管理与调查制度",
        "11. 风险管理成熟度与绩效评估制度",
        "12. 全球合规管理体系文件",
        "13. 反腐败与反贿赂政策",
        "14. 贸易制裁与出口管制合规指引",
        "15. 数据保护与隐私合规制度",
        "16. 竞争法与反垄断合规指引",
        "17. 第三方尽职调查和诚信审查程序",
        "18. 外汇风险管理政策",
        "19. 商品价格对冲管理办法",
        "20. 信用风险管理制度",
        "21. 资金集中与流动性管理办法",
        "22. 海外 HSE 管理体系标准",
        "23. 环境与气候变化管理办法",
        "24. 生产安全事故预防与应急制度",
        "25. 供应链风险与可持续采购政策",
        "26. 设备资产完整性管理制度",
        "27. 海外安全防护与人员安保管理办法",
        "28. 危机管理与业务连续性计划制度",
        "29. 政治风险保险与风险转移指引",
        "30. 网络安全与信息系统管理制度",
        "31. 工控系统安全规范",
        "32. 信息分类分级与保密管理办法",
        "33. 社区关系与社会责任政策",
        "34. 人权与劳工标准政策",
        "35. 海外员工健康与福利管理制度"
    ]
    
    # 加载数据
    data = load_json_data(json_path)
    llm_results = data.get("LLM分析结果", {})
    
    # 创建得分矩阵
    score_matrix = np.zeros((35, 3))
    
    llm_names = ['deepseek', 'openai', 'anthropic']
    
    for llm_idx, llm in enumerate(llm_names):
        if llm not in llm_results:
            continue
            
        llm_data = llm_results[llm]
        if "错误" in llm_data:
            continue
            
        detailed = llm_data.get("详细分析", {})
        
        for category_items in detailed.values():
            if not isinstance(category_items, list):
                continue
                
            for item in category_items:
                req_num = item.get("框架要求编号", item.get("要求编号", 0))
                if 1 <= req_num <= 35:
                    score = calculate_score(item)
                    score_matrix[req_num - 1, llm_idx] = score
    
    # 创建DataFrame
    df = pd.DataFrame(
        score_matrix,
        columns=['DeepSeek', 'OpenAI', 'Anthropic'],
        index=[f"{i+1}" for i in range(35)]
    )
    
    # 创建热力图
    plt.figure(figsize=(6, 14))
    
    # 绘制热力图
    ax = sns.heatmap(
        df,
        annot=True,
        fmt='.0f',
        cmap='RdYlGn',
        cbar_kws={'label': 'Score'},
        vmin=0,
        vmax=100,
        linewidths=0.5,
        linecolor='gray',
        cbar_pos=(1.02, 0.2, 0.03, 0.6)
    )
    
    # 设置标题
    plt.title('35 Requirements Coverage Scores\n35项要求覆盖得分', fontsize=14, pad=20)
    plt.xlabel('LLM Models', fontsize=12)
    plt.ylabel('Requirement Number', fontsize=12)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图片
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"要求级别热力图已保存到: {save_path}")
    
    # 显示图片
    plt.show()
    
    return df


def generate_summary_stats(json_path):
    """生成汇总统计信息"""
    data = load_json_data(json_path)
    llm_results = data.get("LLM分析结果", {})
    
    print("=" * 60)
    print("合规分析汇总统计")
    print("=" * 60)
    
    for llm in ['deepseek', 'openai', 'anthropic']:
        print(f"\n{llm.upper()}:")
        
        if llm not in llm_results:
            print("  - 无数据")
            continue
            
        llm_data = llm_results[llm]
        
        if "错误" in llm_data:
            print(f"  - 错误: {llm_data['错误']}")
            continue
        
        detailed = llm_data.get("详细分析", {})
        
        total_items = 0
        covered_items = 0
        scores = []
        
        for category, items in detailed.items():
            if isinstance(items, list):
                for item in items:
                    total_items += 1
                    coverage = item.get("法规覆盖情况", "")
                    if coverage not in ["未覆盖", "未提及", ""]:
                        covered_items += 1
                    score = calculate_score(item)
                    scores.append(score)
        
        if scores:
            print(f"  - 分析项目数: {total_items}")
            print(f"  - 覆盖项目数: {covered_items}")
            print(f"  - 覆盖率: {covered_items/35*100:.1f}%")
            print(f"  - 平均得分: {np.mean(scores):.1f}")
            print(f"  - 最高得分: {np.max(scores):.0f}")
            print(f"  - 最低得分: {np.min(scores):.0f}")


# 使用示例
if __name__ == "__main__":
    json_file = "关于进一步引导和规范境外投资方向指导意见_综合分析结果.json"
    
    # 生成类别级别的热力图
    print("生成类别级别热力图...")
    category_df = create_simple_heatmap(json_file, "category_heatmap.png")
    
    # 生成35个要求的详细热力图
    print("\n生成详细要求热力图...")
    requirement_df = create_requirement_level_heatmap(json_file, "requirement_heatmap.png")
    
    # 生成统计信息
    print("\n生成统计信息...")
    generate_summary_stats(json_file)
    
    # 保存数据到Excel（可选）
    with pd.ExcelWriter('compliance_analysis.xlsx') as writer:
        category_df.to_excel(writer, sheet_name='Category Scores')
        requirement_df.to_excel(writer, sheet_name='Requirement Scores')
    print("\n数据已保存到 compliance_analysis.xlsx")