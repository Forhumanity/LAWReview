# Matplotlib 中文字体配置
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 可选字体列表
# available_fonts = ['STHeiti', 'Arial Unicode MS', 'STHeiti', 'Hiragino Sans GB', 'Arial Unicode MS']
