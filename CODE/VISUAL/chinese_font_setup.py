"""
中文字体设置助手
帮助解决matplotlib中文显示问题
"""
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import os


def find_chinese_fonts():
    """查找系统中的中文字体"""
    chinese_fonts = []
    
    # 获取所有可用字体
    font_list = fm.findSystemFonts()
    
    # 常见的中文字体名称
    chinese_font_names = [
        'SimHei', 'SimSun', 'Microsoft YaHei', 'Microsoft JhengHei',
        'STHeiti', 'STSong', 'Arial Unicode MS', 'PingFang SC',
        'Hiragino Sans GB', 'WenQuanYi', 'Noto Sans CJK',
        'Source Han Sans', 'Droid Sans Fallback'
    ]
    
    for font_path in font_list:
        try:
            font_prop = fm.FontProperties(fname=font_path)
            font_name = font_prop.get_name()
            
            # 检查是否是中文字体
            for cn_name in chinese_font_names:
                if cn_name.lower() in font_name.lower():
                    chinese_fonts.append({
                        'name': font_name,
                        'path': font_path,
                        'family': font_prop.get_family()
                    })
                    break
        except:
            continue
    
    return chinese_fonts


def test_chinese_font(font_name=None):
    """测试中文字体显示"""
    # 创建测试图
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # 如果指定了字体
    if font_name:
        plt.rcParams['font.sans-serif'] = [font_name]
    
    # 测试文本
    test_text = [
        "中文字体测试 - Chinese Font Test",
        "合规分析热力图",
        "一、治理与战略",
        "二、全面风险管理",
        "三、合规与法律",
        "完全覆盖 | 部分覆盖 | 未覆盖"
    ]
    
    # 显示测试文本
    for i, text in enumerate(test_text):
        ax.text(0.5, 0.8 - i*0.15, text, 
                ha='center', va='center',
                fontsize=14 + (4-i)*2,
                transform=ax.transAxes)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    # 添加当前字体信息
    current_font = plt.rcParams['font.sans-serif'][0] if plt.rcParams['font.sans-serif'] else 'default'
    ax.text(0.5, 0.05, f'当前字体: {current_font}', 
            ha='center', va='center',
            fontsize=10, style='italic',
            transform=ax.transAxes)
    
    plt.title('Matplotlib 中文显示测试', fontsize=16)
    plt.tight_layout()
    
    # 保存测试图
    plt.savefig('chinese_font_test.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    return current_font


def setup_chinese_font():
    """自动设置中文字体"""
    print("=" * 60)
    print("Matplotlib 中文字体设置助手")
    print("=" * 60)
    
    # 检测操作系统
    system = platform.system()
    print(f"\n检测到操作系统: {system}")
    
    # 查找中文字体
    print("\n正在查找系统中的中文字体...")
    chinese_fonts = find_chinese_fonts()
    
    if not chinese_fonts:
        print("\n❌ 未找到中文字体！")
        print("\n请安装中文字体:")
        
        if system == "Windows":
            print("Windows 通常已包含中文字体，请检查系统设置")
        elif system == "Darwin":  # macOS
            print("macOS: 系统应该已包含中文字体")
        else:  # Linux
            print("Linux: sudo apt-get install fonts-wqy-zenhei fonts-noto-cjk")
        
        return None
    
    # 显示找到的字体
    print(f"\n找到 {len(chinese_fonts)} 个中文字体:")
    for i, font in enumerate(chinese_fonts[:10]):  # 只显示前10个
        print(f"{i+1}. {font['name']}")
    
    if len(chinese_fonts) > 10:
        print(f"... 以及其他 {len(chinese_fonts)-10} 个字体")
    
    # 自动选择推荐字体
    recommended_fonts = {
        "Windows": ["Microsoft YaHei", "SimHei"],
        "Darwin": ["PingFang SC", "Arial Unicode MS", "STHeiti"],
        "Linux": ["WenQuanYi Zen Hei", "Noto Sans CJK SC", "Droid Sans Fallback"]
    }
    
    selected_font = None
    system_recommendations = recommended_fonts.get(system, [])
    
    for rec_font in system_recommendations:
        for font in chinese_fonts:
            if rec_font.lower() in font['name'].lower():
                selected_font = font['name']
                break
        if selected_font:
            break
    
    # 如果没有找到推荐字体，使用第一个
    if not selected_font and chinese_fonts:
        selected_font = chinese_fonts[0]['name']
    
    if selected_font:
        print(f"\n推荐使用字体: {selected_font}")
        
        # 设置字体
        plt.rcParams['font.sans-serif'] = [selected_font]
        plt.rcParams['axes.unicode_minus'] = False
        
        # 测试字体
        print("\n正在测试字体显示...")
        test_chinese_font(selected_font)
        
        # 生成配置代码
        print("\n✅ 字体设置成功！")
        print("\n在您的代码中添加以下设置:")
        print("-" * 40)
        print(f"import matplotlib.pyplot as plt")
        print(f"plt.rcParams['font.sans-serif'] = ['{selected_font}']")
        print(f"plt.rcParams['axes.unicode_minus'] = False")
        print("-" * 40)
        
        # 保存配置
        config_file = "matplotlib_chinese_config.py"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(f"# Matplotlib 中文字体配置\n")
            f.write(f"import matplotlib.pyplot as plt\n\n")
            f.write(f"# 设置中文字体\n")
            f.write(f"plt.rcParams['font.sans-serif'] = ['{selected_font}']\n")
            f.write(f"plt.rcParams['axes.unicode_minus'] = False\n")
            f.write(f"\n# 可选字体列表\n")
            f.write(f"# available_fonts = {[font['name'] for font in chinese_fonts[:5]]}\n")
        
        print(f"\n配置已保存到: {config_file}")
        
        return selected_font
    
    return None


def list_all_fonts():
    """列出所有可用字体"""
    print("\n所有可用字体:")
    print("-" * 60)
    
    fonts = sorted(set([f.name for f in fm.fontManager.ttflist]))
    
    for i, font in enumerate(fonts):
        print(f"{i+1:3d}. {font}")
        
    print(f"\n共 {len(fonts)} 个字体")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        # 列出所有字体
        list_all_fonts()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 测试特定字体
        font_name = sys.argv[2] if len(sys.argv) > 2 else None
        test_chinese_font(font_name)
    else:
        # 自动设置
        setup_chinese_font()
        
        print("\n其他选项:")
        print("- 列出所有字体: python chinese_font_setup.py --list")
        print("- 测试特定字体: python chinese_font_setup.py --test 'Font Name'")
        print("- 查看测试图片: chinese_font_test.png")