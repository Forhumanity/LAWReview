# 合规热力图使用和解释指南

## 概述

本工具根据JSON分析结果生成合规覆盖热力图，可视化展示35个监管要求在不同LLM分析中的覆盖情况。

## 评分机制

### 总分计算 (0-100分)

1. **法规覆盖情况** (40分)
   - 完全覆盖: 40分
   - 部分覆盖: 25分
   - 未覆盖/未提及: 0分
   - 不适用: 5分

2. **提及次数** (30分)
   - 每个具体条款提及: 10分
   - 最高30分

3. **强制等级** (20分)
   - 强制: 20分
   - 推荐: 10分
   - 指导: 5分

4. **处罚措施** (10分)
   - 有明确处罚: 10分
   - 无明确处罚: 0分

## 使用方法

### 1. 基本使用

```python
# 最简单的使用方式
from quick_heatmap import create_simple_heatmap

create_simple_heatmap("your_analysis_result.json")
```

### 2. 完整分析

```python
from heatmap_generator import ComplianceHeatmapGenerator

# 创建生成器
generator = ComplianceHeatmapGenerator()

# 处理数据
score_matrix = generator.process_json_data("your_file.json")
reg_name = generator.get_regulation_name("your_file.json")

# 生成详细热力图
generator.create_heatmap(score_matrix, "详细热力图.png", regulation_name=reg_name)

# 生成类别汇总
generator.create_category_summary_heatmap(score_matrix, "分类汇总热力图.png", regulation_name=reg_name)

# 生成报告
generator.generate_analysis_report(score_matrix, "report.txt", regulation_name=reg_name)
```

## 热力图解读

### 颜色含义
- **深绿色** (80-100分): 高度覆盖，法规对此要求有明确、强制的规定
- **浅绿色** (60-80分): 良好覆盖，有相关规定但可能不够详细
- **黄色** (40-60分): 部分覆盖，仅有间接或推荐性规定
- **橙色** (20-40分): 低度覆盖，提及很少
- **红色** (0-20分): 基本未覆盖

### 分析维度

#### X轴 - LLM提供商
- DeepSeek
- OpenAI  
- Anthropic

#### Y轴 - 合规要求
- 35个具体的合规管理要求
- 分为8大类别

## 输出文件说明

1. **<法规名称>_详细热力图.png**
   - 35个要求的详细热力图
   - 显示每个要求在各LLM中的具体得分

2. **<法规名称>_分类汇总热力图.png**
   - 8个大类的汇总热力图
   - 显示每个类别的平均得分

3. **<法规名称>_分析报告.txt**
   - 文字版分析报告
   - 包含统计数据和重点发现

4. **compliance_analysis.xlsx**
   - Excel格式的数据表
   - 方便进一步分析

## 自定义配置

### 修改评分权重

```python
generator.weights = {
    'coverage': 0.5,      # 提高覆盖情况权重
    'mentions': 0.2,      
    'enforcement': 0.2,   
    'penalty': 0.1       
}
```

### 修改颜色方案

```python
# 使用不同的颜色映射
sns.heatmap(data, cmap='YlOrRd')  # 黄-橙-红
sns.heatmap(data, cmap='Blues')    # 蓝色系
sns.heatmap(data, cmap='viridis')  # 紫-绿色系
```

### 添加中文字体支持

```python
# Windows
plt.rcParams['font.sans-serif'] = ['SimHei']

# macOS  
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']

# Linux
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
```

## 常见问题

### Q1: 中文显示为方块
**解决方案**: 安装中文字体并配置matplotlib
```bash
# Ubuntu/Debian
sudo apt-get install fonts-wqy-zenhei

# 然后在代码中设置
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
```

### Q2: 图片太大/太小
**解决方案**: 调整图形大小
```python
plt.figure(figsize=(12, 20))  # 宽12英寸，高20英寸
```

### Q3: 想要不同的评分标准
**解决方案**: 修改 `calculate_score` 函数
```python
def calculate_score(item):
    # 自定义您的评分逻辑
    score = 0
    # ...
    return score
```

## 数据要求

输入的JSON文件必须包含以下结构：
```json
{
  "LLM分析结果": {
    "deepseek": {
      "详细分析": {
        "类别名称": [
          {
            "框架要求编号": 1,
            "法规覆盖情况": "完全覆盖",
            "法规要求内容": [...],
            "强制等级": "强制",
            "处罚措施": "..."
          }
        ]
      }
    }
  }
}
```

## 扩展功能

### 1. 对比多个文档
```python
# 处理多个JSON文件
files = ["doc1.json", "doc2.json", "doc3.json"]
all_scores = []

for file in files:
    score_matrix = generator.process_json_data(file)
    all_scores.append(score_matrix)

# 创建对比图
comparison_df = pd.concat(all_scores, keys=files)
```

### 2. 时间序列分析
```python
# 如果有多个时间点的分析结果
# 可以创建时间序列热力图显示合规改进情况
```

### 3. 导出为其他格式
```python
# 导出为CSV
score_matrix.to_csv("scores.csv", encoding='utf-8-sig')

# 导出为JSON
score_matrix.to_json("scores.json", force_ascii=False)
```

## 最佳实践

1. **数据准备**: 确保JSON文件格式正确，编码为UTF-8
2. **批量处理**: 对多个文档使用循环处理
3. **结果解释**: 结合具体法规内容解读得分
4. **持续改进**: 定期运行分析，跟踪合规改进情况

## 技术支持

如遇到问题，请检查：
1. Python环境是否安装所需库
2. JSON文件格式是否正确
3. 文件路径是否正确
4. 是否有足够的内存处理大文件