import torch
from torch_geometric.data import HeteroData
from neo4j import GraphDatabase
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import os

# 配置信息
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "TYH041113"

class GraphDataLoader:
    def __init__(self, student_file='/Users/tianyuhang/文稿/data/模块_工具/学生数据生成/students_data_500.json'):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.student_file = student_file
        self.data = HeteroData()
        
        # 编码器
        self.city_encoder = LabelEncoder()
        self.skill_encoder = LabelEncoder()
        self.major_encoder = LabelEncoder()
        self.edu_encoder = LabelEncoder()
        self.industry_encoder = LabelEncoder()
        
    def close(self):
        self.driver.close()

    def load_data(self):
        print("🔄 开始加载并构建图数据...")
        
        # 1. 加载学生数据
        with open(self.student_file, 'r', encoding='utf-8') as f:
            student_json = json.load(f)
        students = student_json['students']
        print(f"   已加载 {len(students)} 名学生")

        # 2. 从Neo4j加载职位数据
        jobs = self._fetch_jobs()
        print(f"   已加载 {len(jobs)} 个职位")
        
        # 3. 构建节点映射和特征
        self._build_nodes(students, jobs)
        
        # 4. 构建边连接
        self._build_edges(students, jobs)
        
        print("✅ 图数据构建完成")
        print(self.data)
        return self.data

    def _fetch_jobs(self):
        query = """
        MATCH (j:Job)-[:OFFERED_BY]->(c:Company)
        OPTIONAL MATCH (j)-[:LOCATED_IN]->(city:City)
        OPTIONAL MATCH (j)-[:BELONGS_TO_INDUSTRY]->(ind:Industry)
        OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(s:Skill)
        RETURN j.url as id, j.title as title, j.salary_min as salary_min, 
               j.salary_max as salary_max, j.education as education,
               city.name as city, ind.name as industry,
               collect(s.name) as skills
        """
        with self.driver.session() as session:
            result = session.run(query)
            data = [record.data() for record in result]
            print(f"   [Debug] 前5个职位城市: {[d['city'] for d in data[:5]]}")
            return data

    def _build_nodes(self, students, jobs):
        # --- 准备原始列表 ---
        all_skills = set()
        all_cities = set()
        all_majors = set()
        all_industries = set()
        
        # 收集学生端信息
        student_ids = []
        student_edus = []
        
        for s in students:
            student_ids.append(s['student_id'])
            student_edus.append(s['education'])
            all_majors.add(s['major'])
            for city in s['preferred_cities']:
                all_cities.add(city)
            for skill in s['skills']:
                all_skills.add(skill)
                
        # 收集职位端信息
        job_ids = []
        job_salaries = []
        job_edus = []
        
        for j in jobs:
            job_ids.append(j['id'])
            # 薪资归一化处理
            s_min = j['salary_min'] 
            if s_min is None or pd.isna(s_min): s_min = 0
            
            s_max = j['salary_max']
            if s_max is None or pd.isna(s_max): s_max = 0
            
            job_salaries.append([(s_min + s_max) / 2])
            
            job_edus.append(j['education'] if j['education'] else '不限')
            if j['city']: all_cities.add(j['city'])
            if j['industry']: all_industries.add(j['industry'])
            for skill in j['skills']:
                all_skills.add(skill)

        # --- 编码器拟合 ---
        self.skill_encoder.fit(list(all_skills))
        self.city_encoder.fit(list(all_cities))
        self.major_encoder.fit(list(all_majors))
        all_edus = list(set(student_edus + job_edus + ['不限', '大专', '本科', '硕士', '博士']))
        self.edu_encoder.fit(all_edus)
        self.industry_encoder.fit(list(all_industries))
        
        # --- 设置节点特征 (X) ---
        
        # 1. Student 节点 [Educaton(1), Major(1)]
        s_edu_vec = self.edu_encoder.transform(student_edus)
        student_features = []
        for i, s in enumerate(students):
            major_idx = self.major_encoder.transform([s['major']])[0]
            student_features.append([s_edu_vec[i], major_idx])
            
        self.data['student'].x = torch.tensor(student_features, dtype=torch.float)
        self.data['student'].num_nodes = len(students)
        self.data['student'].node_map = {sid: i for i, sid in enumerate(student_ids)}
        
        # 2. Job 节点 [Salary(1), Education(1)]
        scaler = MinMaxScaler()
        salary_norm = scaler.fit_transform(job_salaries)
        j_edu_vec = self.edu_encoder.transform(job_edus)
        
        job_features = []
        for i in range(len(jobs)):
            job_features.append([salary_norm[i][0], j_edu_vec[i]])
            
        self.data['job'].x = torch.tensor(job_features, dtype=torch.float)
        self.data['job'].num_nodes = len(jobs)
        self.data['job'].node_map = {jid: i for i, jid in enumerate(job_ids)}
        
        # 3. Skill, City, Major 节点 (使用Embedding作为Feature，这里初始化为One-hot或随机)
        self.data['skill'].num_nodes = len(self.skill_encoder.classes_)
        self.data['skill'].x = torch.eye(len(self.skill_encoder.classes_)) # 简单one-hot
        
        self.data['city'].num_nodes = len(self.city_encoder.classes_)
        self.data['city'].x = torch.eye(len(self.city_encoder.classes_))
        
        print(f"   节点统计: Student({self.data['student'].num_nodes}), Job({self.data['job'].num_nodes}), Skill({self.data['skill'].num_nodes})")

    def _build_edges(self, students, jobs):
        # 辅助函数：添加边
        def add_edge(src_type, dst_type, src_indices, dst_indices):
            edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
            self.data[src_type, 'to', dst_type].edge_index = edge_index
            # 添加反向边 (无向图效果，利于信息传递)
            # self.data[dst_type, 'rev_to', src_type].edge_index = torch.flip(edge_index, [0])

        s_map = self.data['student'].node_map
        j_map = self.data['job'].node_map
        
        # 优化：构建技能集合以便快速查找
        valid_skills = set(self.skill_encoder.classes_)
        
        # 1. Student-Skill (掌握)
        src_s, dst_k = [], []
        for s in students:
            if s['student_id'] not in s_map: continue
            s_idx = s_map[s['student_id']]
            
            # 过滤有效技能
            s_skills = [sk for sk in s['skills'] if sk in valid_skills]
            if not s_skills: continue
            
            try:
                skill_indices = self.skill_encoder.transform(s_skills)
                for k_idx in skill_indices:
                    src_s.append(s_idx)
                    dst_k.append(k_idx)
            except: pass
        add_edge('student', 'skill', src_s, dst_k)
        add_edge('skill', 'student', dst_k, src_s) # 反向
        
        # 2. Job-Skill (需求)
        src_j, dst_k = [], []
        for j in jobs:
            if j['id'] not in j_map: continue
            j_idx = j_map[j['id']]
            
            # 过滤有效技能
            j_skills = [sk for sk in j['skills'] if sk in valid_skills]
            if not j_skills: continue
            
            try:
                skill_indices = self.skill_encoder.transform(j_skills)
                for k_idx in skill_indices:
                    src_j.append(j_idx)
                    dst_k.append(k_idx)
            except: pass
        add_edge('job', 'skill', src_j, dst_k)
        add_edge('skill', 'job', dst_k, src_j) # 反向
        
        # 3. Job-City (位于)
        src_j, dst_c = [], []
        valid_cities = set(self.city_encoder.classes_)
        for j in jobs:
            if j['id'] not in j_map or not j['city']: continue
            if j['city'] in valid_cities:
                j_idx = j_map[j['id']]
                c_idx = self.city_encoder.transform([j['city']])[0]
                src_j.append(j_idx)
                dst_c.append(c_idx)
        add_edge('job', 'city', src_j, dst_c)
        add_edge('city', 'job', dst_c, src_j)
        
        # 4. Student-City (期望)
        src_s, dst_c = [], []
        for s in students:
            if s['student_id'] not in s_map: continue
            s_idx = s_map[s['student_id']]
            for city in s['preferred_cities']:
                if city in valid_cities:
                    c_idx = self.city_encoder.transform([city])[0]
                    src_s.append(s_idx)
                    dst_c.append(c_idx)
        add_edge('student', 'city', src_s, dst_c)
        add_edge('city', 'student', dst_c, src_s)

        # 5. 生成训练用的正样本 (Student-Job)
        # 规则：技能重合度 > 0.3 且 城市匹配
        print("   正在生成训练标签(基于规则的弱监督 - 优化版)...")
        train_src, train_dst = [], []
        
        # 优化1: 构建 Skill -> Jobs 反向索引
        skill_to_jobs = {}
        for j in jobs:
            if j['id'] not in j_map: continue
            j_idx = j_map[j['id']]
            # 过滤有效技能
            valid_j_skills = [sk for sk in j['skills'] if sk in valid_skills]
            for sk in valid_j_skills:
                if sk not in skill_to_jobs: skill_to_jobs[sk] = set()
                skill_to_jobs[sk].add(j_idx)
        
        import random
        
        for s in students:
            if s['student_id'] not in s_map: continue
            s_idx = s_map[s['student_id']]
            s_skills = [sk for sk in s['skills'] if sk in valid_skills]
            
            if not s_skills: continue
            
            # 找到所有有相关技能的职位
            candidate_indices = set()
            for sk in s_skills:
                if sk in skill_to_jobs:
                    candidate_indices.update(skill_to_jobs[sk])
            
            # 采样限制 (避免边过多爆内存)
            candidates = list(candidate_indices)
            if len(candidates) > 50:
                candidates = random.sample(candidates, 50)
                
            for j_idx in candidates:
                train_src.append(s_idx)
                train_dst.append(j_idx)
                    
        print(f"   生成正样本连接数: {len(train_src)}")
        edge_index = torch.tensor([train_src, train_dst], dtype=torch.long)
        self.data['student', 'applies', 'job'].edge_index = edge_index

if __name__ == "__main__":
    loader = GraphDataLoader()
    try:
        data = loader.load_data()
        torch.save(data, 'graph_data.pt')
        print("💾 数据已保存到 graph_data.pt")
    finally:
        loader.close()
