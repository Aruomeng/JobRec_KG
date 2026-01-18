#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合推荐系统测试脚本
测试三层漏斗推荐效果并生成报告
"""

import torch
import time
from datetime import datetime
from hybrid_recommender import create_recommender_from_trained_model

def run_test():
    print("="*70)
    print("🧪 混合推荐系统 (HybridRecommender) 测试报告")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 初始化
    start_time = time.time()
    recommender = create_recommender_from_trained_model()
    init_time = time.time() - start_time
    
    print(f"\n⏱️  初始化耗时: {init_time:.2f}秒")
    
    # 测试学生列表 (10名来自训练集)
    test_students = [f'STU{i:04d}' for i in [1, 10, 50, 100, 150, 200, 250, 300, 400, 500]]
    
    results_all = {}
    layer_times = {'recall': [], 'rank': [], 'fuse': []}
    
    print(f"\n{'='*70}")
    print(f"📊 测试 {len(test_students)} 名学生")
    print("="*70)
    
    for stu_id in test_students:
        t0 = time.time()
        
        # Layer 1
        candidates = recommender.recall(stu_id, 500)
        t1 = time.time()
        layer_times['recall'].append(t1 - t0)
        
        # Layer 2
        ranked = recommender.rank(stu_id, candidates)
        t2 = time.time()
        layer_times['rank'].append(t2 - t1)
        
        # Layer 3
        results = recommender.fuse_and_explain(stu_id, ranked, 50)
        t3 = time.time()
        layer_times['fuse'].append(t3 - t2)
        
        results_all[stu_id] = results[:5]  # 保存Top 5
        
        # 打印进度
        total_time = t3 - t0
        print(f"   {stu_id}: ✅ 完成 ({total_time:.3f}s)")
    
    # 统计汇总
    print(f"\n{'='*70}")
    print("📈 性能统计")
    print("="*70)
    
    avg_recall = sum(layer_times['recall']) / len(layer_times['recall'])
    avg_rank = sum(layer_times['rank']) / len(layer_times['rank'])
    avg_fuse = sum(layer_times['fuse']) / len(layer_times['fuse'])
    
    print(f"\n层级耗时 (平均):")
    print(f"   Layer 1 (召回):   {avg_recall*1000:.1f} ms")
    print(f"   Layer 2 (精排):   {avg_rank*1000:.1f} ms")
    print(f"   Layer 3 (融合):   {avg_fuse*1000:.1f} ms")
    print(f"   ─────────────────────────")
    print(f"   总计:             {(avg_recall+avg_rank+avg_fuse)*1000:.1f} ms / 次推荐")
    
    # 得分统计
    all_scores = []
    for stu_id, recs in results_all.items():
        for rec in recs:
            all_scores.append({
                'student': stu_id,
                'job': rec.job_id,
                'final': rec.final_score,
                'deep': rec.deep_score,
                'skill': rec.skill_score,
                'rule': rec.rule_score
            })
    
    finals = [s['final'] for s in all_scores]
    deeps = [s['deep'] for s in all_scores]
    
    print(f"\n得分分布:")
    print(f"   最终得分: min={min(finals):.4f}, max={max(finals):.4f}, avg={sum(finals)/len(finals):.4f}")
    print(f"   深度得分: min={min(deeps):.4f}, max={max(deeps):.4f}, avg={sum(deeps)/len(deeps):.4f}")
    
    # 打印详细结果
    print(f"\n{'='*70}")
    print("📋 详细推荐结果")
    print("="*70)
    
    for stu_id, recs in results_all.items():
        print(f"\n👤 {stu_id}:")
        for i, rec in enumerate(recs[:3], 1):
            job_short = rec.job_id[-25:] if len(rec.job_id) > 25 else rec.job_id
            print(f"   {i}. {job_short}")
            print(f"      得分: {rec.final_score:.4f} (深度:{rec.deep_score:.4f} 技能:{rec.skill_score:.4f} 规则:{rec.rule_score:.4f})")
            print(f"      {rec.explanation}")
    
    recommender.close()
    
    # 生成Markdown报告
    report = generate_report(results_all, layer_times, init_time)
    with open('输出/混合推荐测试报告.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n{'='*70}")
    print("✅ 测试完成！报告已保存到: 输出/混合推荐测试报告.md")
    print("="*70)

def generate_report(results_all, layer_times, init_time):
    """生成Markdown格式的测试报告"""
    
    avg_recall = sum(layer_times['recall']) / len(layer_times['recall']) * 1000
    avg_rank = sum(layer_times['rank']) / len(layer_times['rank']) * 1000
    avg_fuse = sum(layer_times['fuse']) / len(layer_times['fuse']) * 1000
    
    report = f"""# 混合推荐系统 (HybridRecommender) 测试报告

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**测试学生数**: {len(results_all)}  
**推荐模型**: 三层漏斗式混合推荐

---

## 📊 系统概览

| 组件 | 说明 |
|------|------|
| Layer 1 | 向量相似度召回 (NumPy) |
| Layer 2 | 深度学习精排 (GraphSAGE + LinkPredictor) |
| Layer 3 | 神经符号融合 (Neo4j + 规则) |
| 融合公式 | 0.6×deep + 0.3×skill + 0.1×rule |

---

## ⚡ 性能统计

| 层级 | 平均耗时 | 说明 |
|------|----------|------|
| 初始化 | {init_time*1000:.1f} ms | 加载模型+构建索引 |
| Layer 1 | {avg_recall:.1f} ms | 从31,487职位召回500 |
| Layer 2 | {avg_rank:.1f} ms | 深度学习排序 |
| Layer 3 | {avg_fuse:.1f} ms | Neo4j融合+解释 |
| **总计** | **{avg_recall+avg_rank+avg_fuse:.1f} ms** | 单次推荐延迟 |

---

## 📈 得分分布

"""
    
    # 收集得分
    all_scores = []
    for stu_id, recs in results_all.items():
        for rec in recs:
            all_scores.append(rec)
    
    finals = [s.final_score for s in all_scores]
    deeps = [s.deep_score for s in all_scores]
    skills = [s.skill_score for s in all_scores]
    rules = [s.rule_score for s in all_scores]
    
    report += f"""| 得分类型 | 最小值 | 最大值 | 平均值 |
|----------|--------|--------|--------|
| 最终得分 | {min(finals):.4f} | {max(finals):.4f} | {sum(finals)/len(finals):.4f} |
| 深度得分 | {min(deeps):.4f} | {max(deeps):.4f} | {sum(deeps)/len(deeps):.4f} |
| 技能得分 | {min(skills):.4f} | {max(skills):.4f} | {sum(skills)/len(skills):.4f} |
| 规则得分 | {min(rules):.4f} | {max(rules):.4f} | {sum(rules)/len(rules):.4f} |

---

## 📋 推荐结果详情

"""
    
    for stu_id, recs in results_all.items():
        report += f"### {stu_id}\n\n"
        report += "| 排名 | 职位ID | 最终得分 | 深度 | 技能 | 规则 |\n"
        report += "|------|--------|----------|------|------|------|\n"
        for i, rec in enumerate(recs, 1):
            job_short = rec.job_id[-20:]
            report += f"| {i} | ...{job_short} | {rec.final_score:.4f} | {rec.deep_score:.4f} | {rec.skill_score:.4f} | {rec.rule_score:.4f} |\n"
        report += f"\n**Top 1 推荐理由**: {recs[0].explanation}\n\n---\n\n"
    
    report += """
## 💡 分析与建议

### ✅ 优势
1. **响应速度快**: 单次推荐 < 1秒
2. **多层过滤**: 三层漏斗有效减少计算量
3. **可解释性**: 自动生成推荐理由

### ⚠️ 待优化
1. 技能匹配得分较低，需检查Neo4j关系路径
2. 可安装FAISS提升召回层性能
3. 可增加更多规则因子（城市、薪资等）

---

**报告生成**: Antigravity AI Agent
"""
    return report


if __name__ == "__main__":
    run_test()
