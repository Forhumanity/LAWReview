# 合规分析热力图生成工具 - 总结

## 快速开始

最简单的方式 - 直接运行：
```bash
python instant_heatmap.py
```

## 完整功能列表

### 1. **instant_heatmap.py** - 即时生成器
- 最简单，一行命令
- 生成35×3的热力图
- 自动计算得分

### 2. **quick_heatmap.py** - 快速生成器
- 两种热力图：类别级和详细级
- Excel数据导出
- 基础统计信息

### 3. **heatmap_generator.py** - 完整生成器
- 详细的35项要求热力图
- 8大类别汇总热力图
- 完整的文字分析报告
- 可自定义评分权重

### 4. **chinese_font_setup.py** - 中文字体助手
- 自动检测和设置中文字体
- 解决中文显示问题

## 生成的文件

| 文件名 | 内容 | 用途 |
|--------|------|------|
| instant_heatmap.png | 35×3基础热力图 | 快速查看 |
| compliance_heatmap_detailed.png | 详细热力图 | 深入分析 |
| compliance_heatmap_category.png | 类别汇总图 | 管理层汇报 |
| compliance_analysis_report.txt | 文字报告 | 详细说明 |
| compliance_analysis.xlsx | Excel数据 | 进一步分析 |

## 评分机制说明

总分100分，包括：
- **法规覆盖情况** (40分)
  - 完全覆盖: 40分
  - 部分覆盖: 25分
  - 未覆盖: 0分
  
- **提及次数** (30分)
  - 每个条款10分，最高30分
  
- **强制等级** (20分)
  - 强制: 20分
  - 推荐: 10分
  - 指导: 5分
  
- **处罚措施** (10分)
  - 有明确处罚: 10分

## 使用场景

### 场景1: 快速预览
```bash
python instant_heatmap.py your_analysis.json
```

### 场景2: 完整分析
```bash
python heatmap_generator.py
```

### 场景3: 批量处理
```bash
./run_heatmap.sh *.json
```

### 场景4: 中文字体问题
```bash
python chinese_font_setup.py
```

## 颜色含义

🟢 **绿色** (80-100): 高度覆盖
🟡 **黄色** (40-80): 中度覆盖  
🔴 **红色** (0-40): 低度覆盖

## 常见问题解决

### Q: 中文显示为方块？
```bash
python chinese_font_setup.py
```

### Q: 没有安装必要的包？
```bash
pip install -r heatmap_requirements.txt
```

### Q: 想要不同的颜色？
在代码中修改 `cmap` 参数：
- `cmap='RdYlGn'` - 红黄绿（默认）
- `cmap='Blues'` - 蓝色系
- `cmap='viridis'` - 紫绿色系

## 数据要求

输入JSON必须包含以下结构：
```json
{
  "LLM分析结果": {
    "deepseek": {
      "详细分析": {...}
    },
    "openai": {
      "详细分析": {...}
    },
    "anthropic": {
      "详细分析": {...}
    }
  }
}
```

## 联系与支持

如有问题，请检查：
1. JSON文件格式是否正确
2. Python包是否安装完整
3. 文件路径是否正确

祝您使用愉快！