"""
即时热力图生成器 - 最简单的使用方式
直接运行即可生成热力图，无需复杂配置
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sys

# 尝试设置中文字体
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
except:
    print("Warning: Chinese font may not display correctly")


def quick_heatmap(json_file="关于进一步引导和规范境外投资方向指导意见_综合分析结果.json"):
    """快速生成热力图"""
    
    print(f"Loading {json_file}...")
    
    # 读取JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Cannot find {json_file}")
        print("Please make sure the JSON file is in the same directory")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {json_file}")
        return
    
    # 提取数据
    llm_results = data.get("LLM分析结果", {})
    
    # 简单的评分函数
    def get_score(coverage):
        scores = {
            "完全覆盖": 90,
            "部分覆盖": 60,
            "未覆盖": 10,
            "未提及": 10,
            "不适用": 20
        }
        return scores.get(coverage, 0)
    
    # 收集所有35个要求的得分
    requirements = []
    scores_matrix = []
    
    # 35个要求的标准列表
    for i in range(1, 36):
        requirements.append(f"Req #{i}")
        
    # 为每个LLM收集得分
    llm_names = ['deepseek', 'openai', 'anthropic']
    
    for i in range(35):
        row_scores = []
        for llm in llm_names:
            score = 0  # 默认得分
            
            if llm in llm_results and "详细分析" in llm_results[llm]:
                # 搜索对应的要求
                for category_items in llm_results[llm]["详细分析"].values():
                    if isinstance(category_items, list):
                        for item in category_items:
                            req_num = item.get("框架要求编号", item.get("要求编号", 0))
                            if req_num == i + 1:
                                coverage = item.get("法规覆盖情况", "未覆盖")
                                score = get_score(coverage)
                                # 如果有强制要求，加分
                                for content in item.get("法规要求内容", []):
                                    if content.get("强制等级") == "强制":
                                        score = min(score + 10, 100)
                                break
            
            row_scores.append(score)
        scores_matrix.append(row_scores)
    
    # 创建热力图
    plt.figure(figsize=(8, 12))
    
    # 转换为numpy数组
    scores_array = np.array(scores_matrix)
    
    # 绘制
    ax = sns.heatmap(
        scores_array,
        xticklabels=['DeepSeek', 'OpenAI', 'Anthropic'],
        yticklabels=[f"{i+1}" for i in range(35)],
        annot=True,
        fmt='d',
        cmap='RdYlGn',
        vmin=0,
        vmax=100,
        cbar_kws={'label': 'Coverage Score'},
        linewidths=0.5
    )
    
    # 设置标题
    plt.title('Compliance Requirements Coverage Analysis\n(35 Requirements × 3 LLMs)', 
              fontsize=14, pad=20)
    plt.xlabel('LLM Models', fontsize=12)
    plt.ylabel('Requirement Number (1-35)', fontsize=12)
    
    # 添加分类线（每个主要类别的分隔）
    category_breaks = [4, 11, 17, 21, 26, 29, 32, 35]
    for pos in category_breaks[:-1]:
        ax.axhline(y=pos, color='blue', linewidth=2)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存
    output_file = 'instant_heatmap.png'
    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    print(f"\n✅ Heatmap saved as: {output_file}")
    
    # 显示
    plt.show()
    
    # 打印简单统计
    print("\n" + "="*50)
    print("Quick Statistics:")
    print("="*50)
    
    for j, llm in enumerate(['DeepSeek', 'OpenAI', 'Anthropic']):
        llm_scores = scores_array[:, j]
        avg_score = np.mean(llm_scores)
        coverage = np.sum(llm_scores > 20) / 35 * 100
        
        print(f"\n{llm}:")
        print(f"  Average Score: {avg_score:.1f}")
        print(f"  Coverage Rate: {coverage:.1f}%")
        print(f"  High Coverage (>60): {np.sum(llm_scores > 60)} items")


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = "关于进一步引导和规范境外投资方向指导意见_综合分析结果.json"
    
    # 生成热力图
    quick_heatmap(json_file)
    
    print("\nUsage: python instant_heatmap.py [your_json_file.json]")