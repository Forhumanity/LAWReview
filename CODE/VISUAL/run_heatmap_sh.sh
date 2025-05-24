#!/bin/bash
# 热力图生成运行脚本

echo "=================================="
echo "合规分析热力图生成工具"
echo "=================================="
echo

# 检查Python环境
echo "1. 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python"
    exit 1
fi
echo "✓ Python已安装: $(python3 --version)"

# 检查必要的包
echo -e "\n2. 检查必要的Python包..."
packages=("pandas" "numpy" "matplotlib" "seaborn")
missing_packages=()

for package in "${packages[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo "✓ $package 已安装"
    else
        echo "✗ $package 未安装"
        missing_packages+=($package)
    fi
done

# 安装缺失的包
if [ ${#missing_packages[@]} -gt 0 ]; then
    echo -e "\n需要安装以下包: ${missing_packages[*]}"
    read -p "是否现在安装? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install pandas numpy matplotlib seaborn openpyxl
    else
        echo "请手动安装缺失的包后再运行"
        exit 1
    fi
fi

# 检查JSON文件
echo -e "\n3. 检查输入文件..."
if [ $# -eq 0 ]; then
    # 使用默认文件名
    json_file="关于进一步引导和规范境外投资方向指导意见_综合分析结果.json"
else
    json_file="$1"
fi

if [ ! -f "$json_file" ]; then
    echo "❌ 找不到JSON文件: $json_file"
    echo "用法: $0 [json文件路径]"
    exit 1
fi
echo "✓ 找到JSON文件: $json_file"

# 创建输出目录
echo -e "\n4. 创建输出目录..."
output_dir="heatmap_output_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$output_dir"
echo "✓ 输出目录: $output_dir"

# 生成热力图
echo -e "\n5. 生成热力图..."
python3 << EOF
import sys
import os
sys.path.append('.')

# 尝试导入生成器
try:
    from heatmap_generator import ComplianceHeatmapGenerator
    print("使用完整版生成器...")
    
    generator = ComplianceHeatmapGenerator()
    score_matrix = generator.process_json_data("$json_file")
    
    # 生成所有图表
    generator.create_heatmap(score_matrix, "$output_dir/detailed_heatmap.png")
    generator.create_category_summary_heatmap(score_matrix, "$output_dir/category_heatmap.png")
    generator.generate_analysis_report(score_matrix, "$output_dir/analysis_report.txt")
    
except ImportError:
    print("使用简化版生成器...")
    from quick_heatmap import create_simple_heatmap, create_requirement_level_heatmap, generate_summary_stats
    
    create_simple_heatmap("$json_file", "$output_dir/category_heatmap.png")
    create_requirement_level_heatmap("$json_file", "$output_dir/requirement_heatmap.png")
    
    # 生成统计报告
    import sys
    orig_stdout = sys.stdout
    with open("$output_dir/summary_stats.txt", 'w', encoding='utf-8') as f:
        sys.stdout = f
        generate_summary_stats("$json_file")
    sys.stdout = orig_stdout

print("\n✓ 热力图生成完成！")
EOF

# 显示结果
echo -e "\n=================================="
echo "生成完成！"
echo "=================================="
echo "输出文件位于: $output_dir/"
echo
ls -la "$output_dir/"
echo
echo "您可以查看以下文件："
echo "- 热力图: *.png"
echo "- 分析报告: *.txt"
echo "- Excel数据: *.xlsx (如有)"

# 询问是否打开文件夹
if command -v open &> /dev/null; then
    # macOS
    read -p "是否打开输出文件夹? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$output_dir"
    fi
elif command -v xdg-open &> /dev/null; then
    # Linux
    read -p "是否打开输出文件夹? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        xdg-open "$output_dir"
    fi
elif command -v explorer &> /dev/null; then
    # Windows (Git Bash)
    read -p "是否打开输出文件夹? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        explorer "$output_dir"
    fi
fi