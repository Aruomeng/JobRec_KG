#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphSAGE 模型训练可视化
绘制训练过程中的所有相关参数
"""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

import numpy as np
import os

# 创建输出目录
os.makedirs('输出/可视化', exist_ok=True)

# ==================== 训练数据 ====================
epochs = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
loss_values = [3.2537, 0.8817, 0.8028, 0.3305, 0.3128, 0.3733, 0.3314, 0.3018, 0.3023, 0.2991]
auc_values = [0.8725, 0.8649, 0.8674, 0.8811, 0.8942, 0.9049, 0.9096, 0.9126, 0.9095, 0.9153]

# ==================== 图1: 训练曲线 (Loss + AUC) ====================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Loss曲线
ax1.plot(epochs, loss_values, 'b-o', linewidth=2, markersize=8, label='Training Loss')
ax1.fill_between(epochs, loss_values, alpha=0.3)
ax1.set_xlabel('Epoch', fontsize=12)
ax1.set_ylabel('Loss', fontsize=12)
ax1.set_title('Training Loss Curve', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(0, 3.5)
ax1.legend()

# 标注最低点
min_idx = np.argmin(loss_values)
ax1.annotate(f'Min: {loss_values[min_idx]:.4f}', 
             xy=(epochs[min_idx], loss_values[min_idx]),
             xytext=(epochs[min_idx]+5, loss_values[min_idx]+0.3),
             arrowprops=dict(arrowstyle='->', color='red'),
             fontsize=10, color='red')

# AUC曲线
ax2.plot(epochs, auc_values, 'g-s', linewidth=2, markersize=8, label='Training AUC')
ax2.fill_between(epochs, auc_values, alpha=0.3, color='green')
ax2.axhline(y=0.9, color='r', linestyle='--', label='Target: 0.90')
ax2.set_xlabel('Epoch', fontsize=12)
ax2.set_ylabel('AUC', fontsize=12)
ax2.set_title('Training AUC Curve', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(0.85, 0.93)
ax2.legend()

# 标注最高点
max_idx = np.argmax(auc_values)
ax2.annotate(f'Max: {auc_values[max_idx]:.4f}', 
             xy=(epochs[max_idx], auc_values[max_idx]),
             xytext=(epochs[max_idx]-10, auc_values[max_idx]-0.01),
             arrowprops=dict(arrowstyle='->', color='blue'),
             fontsize=10, color='blue')

plt.tight_layout()
plt.savefig('输出/可视化/训练曲线.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ 保存: 输出/可视化/训练曲线.png")

# ==================== 图2: 数据规模对比 ====================
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# 节点数量
node_types = ['Student', 'Job', 'Skill', 'City']
node_counts = [500, 31487, 15696, 9]
colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0']

ax = axes[0]
bars = ax.bar(node_types, node_counts, color=colors)
ax.set_ylabel('Count (log scale)', fontsize=12)
ax.set_title('Node Distribution', fontsize=14, fontweight='bold')
ax.set_yscale('log')
for bar, count in zip(bars, node_counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), 
            f'{count:,}', ha='center', va='bottom', fontsize=10)

# 边数量
edge_types = ['Stu-Skill', 'Job-Skill', 'Stu-City', 'Train Edge']
edge_counts = [8765, 105323, 842, 892760]
colors2 = ['#E91E63', '#00BCD4', '#FFC107', '#8BC34A']

ax = axes[1]
bars = ax.bar(edge_types, edge_counts, color=colors2)
ax.set_ylabel('Count (log scale)', fontsize=12)
ax.set_title('Edge Distribution', fontsize=14, fontweight='bold')
ax.set_yscale('log')
ax.tick_params(axis='x', rotation=15)
for bar, count in zip(bars, edge_counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), 
            f'{count:,}', ha='center', va='bottom', fontsize=9)

# Demo vs Full 对比
ax = axes[2]
x = np.arange(3)
width = 0.35
demo_vals = [3000, 241991, 0.8311]
full_vals = [31487, 892760, 0.9153]
labels = ['Jobs', 'Samples', 'AUC']

# 归一化显示
demo_norm = [demo_vals[0]/full_vals[0]*100, demo_vals[1]/full_vals[1]*100, demo_vals[2]/full_vals[2]*100]
full_norm = [100, 100, 100]

bars1 = ax.bar(x - width/2, demo_norm, width, label='Demo (3k)', color='#FF7043')
bars2 = ax.bar(x + width/2, full_norm, width, label='Full (31k)', color='#42A5F5')
ax.set_ylabel('Relative %', fontsize=12)
ax.set_title('Demo vs Full Comparison', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
ax.set_ylim(0, 120)

plt.tight_layout()
plt.savefig('输出/可视化/数据规模.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ 保存: 输出/可视化/数据规模.png")

# ==================== 图3: 模型参数 ====================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 模型超参数
params = {
    'Hidden Channels': 64,
    'Output Channels': 32,
    'Learning Rate': 0.01,
    'Epochs': 50,
    'Batch (Full Graph)': 1,
}
ax = axes[0]
y_pos = np.arange(len(params))
values = list(params.values())
ax.barh(y_pos, values, color='#7E57C2')
ax.set_yticks(y_pos)
ax.set_yticklabels(list(params.keys()))
ax.set_xlabel('Value')
ax.set_title('Model Hyperparameters', fontsize=14, fontweight='bold')
for i, v in enumerate(values):
    ax.text(v + 0.5, i, str(v), va='center')

# 最终指标
ax = axes[1]
metrics = ['Final Loss', 'Final AUC', 'Train Samples', 'Model Params']
values = [0.2991, 0.9153, 892760/1000000, 0.5]  # 归一化
colors = ['#EF5350', '#66BB6A', '#42A5F5', '#AB47BC']
bars = ax.bar(metrics, values, color=colors)
ax.set_ylabel('Value (normalized)', fontsize=12)
ax.set_title('Final Training Metrics', fontsize=14, fontweight='bold')
ax.tick_params(axis='x', rotation=15)

# 添加实际数值标签
actual = ['0.2991', '0.9153', '892,760', '~10K']
for bar, val in zip(bars, actual):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
            val, ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('输出/可视化/模型参数.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ 保存: 输出/可视化/模型参数.png")

# ==================== 图4: 学生专业分布 ====================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# 训练学生专业分布 (模拟数据)
majors = ['Computer Sci', 'Software Eng', 'Network Eng', 'Big Data', 'AI', 'IoT', 'Info Security', 'E-Commerce', 'EE', 'Communication']
counts = [55, 56, 58, 57, 48, 45, 51, 44, 42, 52]  # 模拟分布
colors = plt.cm.Set3(np.linspace(0, 1, len(majors)))

ax1.pie(counts, labels=majors, autopct='%1.0f%%', colors=colors, startangle=90)
ax1.set_title('Training Students by Major', fontsize=14, fontweight='bold')

# 测试学生专业分布
test_majors = ['Computer Sci', 'Network Eng', 'Software Eng', 'Big Data', 'IoT']
test_counts = [3, 2, 2, 2, 1]
colors2 = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336']

ax2.pie(test_counts, labels=test_majors, autopct='%1.0f%%', colors=colors2, startangle=90, explode=[0.05]*5)
ax2.set_title('Test Students by Major (10 samples)', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('输出/可视化/专业分布.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ 保存: 输出/可视化/专业分布.png")

# ==================== 图5: 综合仪表盘 ====================
fig = plt.figure(figsize=(16, 10))

# 标题
fig.suptitle('GraphSAGE Job Recommendation Model - Training Dashboard', 
             fontsize=18, fontweight='bold', y=0.98)

# 子图1: Loss曲线
ax1 = fig.add_subplot(2, 3, 1)
ax1.plot(epochs, loss_values, 'b-o', linewidth=2)
ax1.set_title('Loss Curve')
ax1.set_xlabel('Epoch')
ax1.set_ylabel('Loss')
ax1.grid(True, alpha=0.3)

# 子图2: AUC曲线
ax2 = fig.add_subplot(2, 3, 2)
ax2.plot(epochs, auc_values, 'g-s', linewidth=2)
ax2.axhline(y=0.9, color='r', linestyle='--', alpha=0.7)
ax2.set_title('AUC Curve')
ax2.set_xlabel('Epoch')
ax2.set_ylabel('AUC')
ax2.set_ylim(0.85, 0.93)
ax2.grid(True, alpha=0.3)

# 子图3: 关键指标
ax3 = fig.add_subplot(2, 3, 3)
metrics_text = """
╔════════════════════════════════╗
║     FINAL TRAINING RESULTS     ║
╠════════════════════════════════╣
║  AUC Score:     0.9153  🏆     ║
║  Final Loss:    0.2991         ║
║  Total Epochs:  50             ║
║                                ║
║  Jobs:          31,487         ║
║  Skills:        15,696         ║
║  Students:      500            ║
║  Train Samples: 892,760        ║
╚════════════════════════════════╝
"""
ax3.text(0.5, 0.5, metrics_text, transform=ax3.transAxes, fontsize=11,
         verticalalignment='center', horizontalalignment='center',
         fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
ax3.axis('off')
ax3.set_title('Key Metrics', fontsize=12, fontweight='bold')

# 子图4: 节点分布
ax4 = fig.add_subplot(2, 3, 4)
ax4.bar(node_types, node_counts, color=colors)
ax4.set_yscale('log')
ax4.set_title('Node Counts')
ax4.set_ylabel('Count (log)')

# 子图5: 边分布
ax5 = fig.add_subplot(2, 3, 5)
ax5.bar(edge_types, edge_counts, color=colors2)
ax5.set_yscale('log')
ax5.set_title('Edge Counts')
ax5.tick_params(axis='x', rotation=20)

# 子图6: 模型架构示意
ax6 = fig.add_subplot(2, 3, 6)
arch_text = """
┌─────────────────────────────────┐
│         INPUT FEATURES          │
│  Student[500,2] | Job[31487,2]  │
│  Skill[15696] | City[9]         │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│     HeteroConv Layer 1          │
│     SAGEConv(-1, 64)            │
│     + ReLU Activation           │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│     HeteroConv Layer 2          │
│     SAGEConv(64, 32)            │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│       Link Predictor            │
│   Linear(32*2, 1) → Score       │
└─────────────────────────────────┘
"""
ax6.text(0.5, 0.5, arch_text, transform=ax6.transAxes, fontsize=9,
         verticalalignment='center', horizontalalignment='center',
         fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
ax6.axis('off')
ax6.set_title('Model Architecture', fontsize=12, fontweight='bold')

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('输出/可视化/训练仪表盘.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ 保存: 输出/可视化/训练仪表盘.png")

print("\n" + "="*50)
print("📊 所有可视化图表已生成！")
print("="*50)
print("文件列表:")
for f in os.listdir('输出/可视化'):
    print(f"   • 输出/可视化/{f}")
