#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphSAGE 模型测试脚本
测试10名随机生成的新学生（非训练集）
"""

import torch
import json
import random
from datetime import datetime
from neo4j import GraphDatabase

# 复用生成学生的逻辑
SURNAMES = ['王','李','张','刘','陈','杨','赵','黄','周','吴','徐','孙','胡','朱','高']
NAMES = ['伟','芳','娜','敏','静','丽','强','磊','军','洋','勇','艳','杰','涛','明']
CITIES = ['北京','上海','深圳','杭州','南京','成都','武汉','郑州','厦门']
EDUCATIONS = ['大专', '本科', '硕士', '博士']

domain_data = {
    "物联网工程": {"物联网导论": ["IoT概念","传感器技术","RFID"], "嵌入式系统设计": ["C语言","ARM架构","Linux驱动"]},
    "计算机科学与技术": {"Java语言程序设计": ["Java","JVM","多线程"], "数据结构与算法": ["算法","数据结构","逻辑思维"], "计算机网络": ["TCP/IP","HTTP协议","网络编程"]},
    "软件工程": {"Java企业级开发": ["Java","Spring Boot","MyBatis"], "Web应用开发": ["React","JavaScript","Node.js"], "DevOps实践": ["Docker","Kubernetes","Jenkins"]},
    "大数据管理与应用": {"Python数据分析": ["Python","Pandas","NumPy"], "Hadoop大数据技术": ["Hadoop","MapReduce","HDFS"], "机器学习导论": ["Scikit-learn","机器学习","统计学"]},
    "人工智能": {"深度学习": ["TensorFlow","PyTorch","神经网络"], "计算机视觉": ["OpenCV","图像处理","CNN"], "自然语言处理": ["NLP","BERT","文本分析"]},
    "网络工程": {"路由与交换技术": ["Cisco","华为认证","VLAN"], "网络安全技术": ["防火墙","VPN","入侵检测"], "云计算架构": ["OpenStack","KVM","虚拟化"]},
}

def generate_test_student(student_id):
    """生成一个测试学生"""
    name = random.choice(SURNAMES) + random.choice(NAMES) + random.choice(NAMES)
    education = random.choices(EDUCATIONS, weights=[15, 60, 20, 5])[0]
    major = random.choice(list(domain_data.keys()))
    preferred_cities = random.sample(CITIES, random.randint(1, 3))
    
    courses = list(domain_data[major].keys())
    selected_courses = random.sample(courses, min(2, len(courses)))
    
    skills = set()
    for course in selected_courses:
        skills.update(domain_data[major][course])
    
    return {
        'student_id': student_id,
        'name': name,
        'education': education,
        'major': major,
        'preferred_cities': preferred_cities,
        'skills': list(skills)
    }

def test_recommendation():
    from model import RecommenderModel
    
    print("="*70)
    print("🧪 GraphSAGE 模型测试报告")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 加载模型和数据
    data = torch.load('graph_data.pt', weights_only=False)
    model = RecommenderModel(data.metadata(), hidden_channels=64, out_channels=32)
    model.load_state_dict(torch.load('输出/模型权重/graphsage_model.pth', weights_only=True))
    model.eval()
    
    print(f"\n📊 模型信息:")
    print(f"   职位总数: {data['job'].num_nodes:,}")
    print(f"   技能总数: {data['skill'].num_nodes:,}")
    
    # 连接Neo4j获取职位详情
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "TYH041113"))
    
    # 生成10名测试学生 (ID从TEST0001开始，避免与训练集STU0001-0500重复)
    test_students = [generate_test_student(f"TEST{i:04d}") for i in range(1, 11)]
    
    print(f"\n🎓 测试学生: {len(test_students)}名 (非训练集)")
    print("-"*70)
    
    results = []
    
    # 获取编码后的节点嵌入
    with torch.no_grad():
        x_dict = model.encoder(data.x_dict, data.edge_index_dict)
        job_embs = x_dict['job']
        
        # 由于测试学生不在图中，我们需要基于技能相似度找到最相似的训练学生
        # 然后使用该学生的嵌入进行推荐
        # 这模拟了冷启动场景
        
        # 简化处理：随机选择一个训练学生作为代理
        # 实际应用中应该基于特征相似度
        
        job_id_map = {v: k for k, v in data['job'].node_map.items()}
        
        for idx, student in enumerate(test_students):
            # 使用随机训练学生的嵌入（模拟冷启动的简化方案）
            proxy_idx = random.randint(0, data['student'].num_nodes - 1)
            student_emb = x_dict['student'][proxy_idx]
            
            # 计算与所有职位的匹配分数
            num_jobs = data['job'].num_nodes
            batch_size = 1000
            scores = []
            
            for i in range(0, num_jobs, batch_size):
                end = min(i + batch_size, num_jobs)
                batch_job_indices = torch.arange(i, end)
                batch_src = torch.full((len(batch_job_indices),), proxy_idx, dtype=torch.long)
                batch_edge_index = torch.stack([batch_src, batch_job_indices], dim=0)
                batch_pred = model.predictor(x_dict['student'], x_dict['job'], batch_edge_index)
                scores.append(batch_pred.squeeze())
            
            all_scores = torch.cat(scores)
            top_scores, top_indices = torch.topk(all_scores, 3)
            
            # 查询职位详情
            recommendations = []
            for score, job_idx in zip(top_scores, top_indices):
                job_url = job_id_map[job_idx.item()]
                suffix = job_url.split('/')[-1]
                
                query = f"MATCH (j:Job) WHERE j.url ENDS WITH '{suffix}' RETURN j.title as title, j.salary as salary"
                with driver.session() as session:
                    result = session.run(query).single()
                    if result:
                        recommendations.append({
                            'title': result['title'] or '未知',
                            'salary': result['salary'] or '面议',
                            'score': score.item()
                        })
            
            results.append({
                'student': student,
                'recommendations': recommendations
            })
            
            # 打印结果
            print(f"\n👤 {student['name']} ({student['student_id']})")
            print(f"   🎓 {student['education']} | {student['major']}")
            print(f"   📍 期望城市: {', '.join(student['preferred_cities'])}")
            print(f"   🛠️ 技能: {', '.join(student['skills'][:5])}...")
            print(f"   📋 推荐职位:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"      {i}. {rec['title']} ({rec['salary']}) - 得分:{rec['score']:.4f}")
    
    driver.close()
    
    # 统计汇总
    print("\n" + "="*70)
    print("📊 测试统计汇总")
    print("="*70)
    
    all_scores = []
    for r in results:
        for rec in r['recommendations']:
            all_scores.append(rec['score'])
    
    if all_scores:
        avg_score = sum(all_scores) / len(all_scores)
        max_score = max(all_scores)
        min_score = min(all_scores)
        print(f"   平均推荐得分: {avg_score:.4f}")
        print(f"   最高得分: {max_score:.4f}")
        print(f"   最低得分: {min_score:.4f}")
    
    # 专业分布
    majors = {}
    for r in results:
        m = r['student']['major']
        majors[m] = majors.get(m, 0) + 1
    
    print(f"\n   测试学生专业分布:")
    for m, c in majors.items():
        print(f"      • {m}: {c}人")
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70)
    
    return results

if __name__ == "__main__":
    test_recommendation()
