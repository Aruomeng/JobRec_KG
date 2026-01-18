#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
就业推荐知识图谱构建脚本
========================
使用Neo4j构建就业推荐知识图谱

实体节点:
- Job (岗位): 职位名称、经验要求、工作描述、薪资
- Company (公司): 公司名称、规模
- City (城市): 城市名称
- Skill (技能): 技能名称
- Industry (行业): 行业名称

关系:
- (Job)-[:REQUIRES_SKILL]->(Skill) 岗位需要技能
- (Job)-[:BELONGS_TO_INDUSTRY]->(Industry) 岗位属于行业
- (Job)-[:OFFERED_BY]->(Company) 岗位属于公司
- (Company)-[:LOCATED_IN]->(City) 公司在城市

作者：AI Assistant
日期：2026-01-12
"""

import os
import re
import pandas as pd
from neo4j import GraphDatabase
from datetime import datetime

# ==================== Neo4j配置 ====================
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "TYH041113"

# 输入目录
INPUT_BASE_DIR = '第二次清洗_进阶'

# 城市目录列表
CITY_DIRS = [
    'data_beijing_advanced',
    'data_chengdu_advanced',
    'data_chongqing_advanced',
    'data_hangzhou_advanced',
    'data_nanjin_advanced',
    'data_shenzhen_advanced',
    'data_wuhan_advanced',
    'data_xiamen_advanced',
    'data_zhengzhou_advanced'
]


class JobKnowledgeGraph:
    def __init__(self, uri, user, password):
        """初始化Neo4j连接"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✅ 已连接到Neo4j: {uri}")
    
    def close(self):
        """关闭连接"""
        self.driver.close()
        print("🔒 Neo4j连接已关闭")
    
    def clear_database(self):
        """清空数据库（可选）"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("🗑️  数据库已清空")
    
    def create_constraints(self):
        """创建约束和索引，提高查询效率"""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.url IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (city:City) REQUIRE city.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Industry) REQUIRE i.name IS UNIQUE",
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"⚠️ 约束创建警告: {e}")
            print("📋 索引和约束已创建")
    
    def _is_valid_value(self, value):
        """检查值是否有效（非空、非NaN）"""
        if value is None:
            return False
        if pd.isna(value):
            return False
        if isinstance(value, str) and value.strip() == '':
            return False
        return True
    
    def create_job_graph(self, job_data):
        """
        创建单条职位记录的图谱
        
        参数:
            job_data: 包含职位信息的字典
        """
        with self.driver.session() as session:
            city = job_data.get('城市')
            company = job_data.get('公司')
            industry = job_data.get('行业')
            scale = job_data.get('公司规模', '')
            
            # 检查值是否有效
            has_city = self._is_valid_value(city)
            has_company = self._is_valid_value(company)
            has_industry = self._is_valid_value(industry)
            
            # 创建城市节点
            if has_city:
                session.run(
                    "MERGE (city:City {name: $city_name})",
                    city_name=city
                )
            
            # 创建公司节点
            if has_company:
                session.run("""
                    MERGE (c:Company {name: $company_name})
                    SET c.scale = $scale
                """, 
                    company_name=company,
                    scale=scale if self._is_valid_value(scale) else ''
                )
                
                # 创建公司-城市关系
                if has_city:
                    session.run("""
                        MATCH (c:Company {name: $company_name})
                        MATCH (city:City {name: $city_name})
                        MERGE (c)-[:LOCATED_IN]->(city)
                    """,
                        company_name=company,
                        city_name=city
                    )
            
            # 创建行业节点
            if has_industry:
                session.run(
                    "MERGE (i:Industry {name: $industry_name})",
                    industry_name=industry
                )
            
            # 创建职位节点
            job_url = job_data.get('职位URL', f"job_{hash(str(job_data))}")
            session.run("""
                MERGE (j:Job {url: $url})
                SET j.title = $title,
                    j.experience = $experience,
                    j.education = $education,
                    j.description = $description,
                    j.salary = $salary,
                    j.salary_min = $salary_min,
                    j.salary_max = $salary_max,
                    j.annual_months = $annual_months,
                    j.publish_time = $publish_time
            """,
                url=job_url,
                title=job_data.get('职位', ''),
                experience=job_data.get('经验', ''),
                education=job_data.get('学历', ''),
                description=job_data.get('工作描述', '')[:500] if job_data.get('工作描述') else '',
                salary=job_data.get('薪资', ''),
                salary_min=job_data.get('薪资_最小值'),
                salary_max=job_data.get('薪资_最大值'),
                annual_months=job_data.get('年薪月数'),
                publish_time=job_data.get('发布时间', '')
            )
            
            # 创建职位-公司关系
            if has_company:
                session.run("""
                    MATCH (j:Job {url: $url})
                    MATCH (c:Company {name: $company_name})
                    MERGE (j)-[:OFFERED_BY]->(c)
                """,
                    url=job_url,
                    company_name=company
                )
            
            # 创建职位-行业关系
            if has_industry:
                session.run("""
                    MATCH (j:Job {url: $url})
                    MATCH (i:Industry {name: $industry_name})
                    MERGE (j)-[:BELONGS_TO_INDUSTRY]->(i)
                """,
                    url=job_url,
                    industry_name=industry
                )
            
            # 创建技能节点和关系
            skills = job_data.get('技能', '')
            if skills and isinstance(skills, str):
                # 分割技能
                skill_list = re.split(r'[,，、;；/\|]', skills)
                for skill in skill_list:
                    skill = skill.strip()
                    if skill and len(skill) >= 2:
                        # 创建技能节点
                        session.run(
                            "MERGE (s:Skill {name: $skill_name})",
                            skill_name=skill
                        )
                        # 创建职位-技能关系
                        session.run("""
                            MATCH (j:Job {url: $url})
                            MATCH (s:Skill {name: $skill_name})
                            MERGE (j)-[:REQUIRES_SKILL]->(s)
                        """,
                            url=job_url,
                            skill_name=skill
                        )
    
    def batch_create_jobs(self, jobs_df, batch_size=100):
        """
        批量创建职位图谱
        
        参数:
            jobs_df: 包含职位数据的DataFrame
            batch_size: 批处理大小
        """
        total = len(jobs_df)
        created = 0
        
        for idx, row in jobs_df.iterrows():
            try:
                job_data = row.to_dict()
                self.create_job_graph(job_data)
                created += 1
                
                if created % batch_size == 0:
                    print(f"  📊 进度: {created}/{total} ({created/total*100:.1f}%)")
            except Exception as e:
                print(f"  ⚠️ 创建失败 [{row.get('职位', 'Unknown')}]: {e}")
        
        return created
    
    def get_statistics(self):
        """获取图谱统计信息"""
        with self.driver.session() as session:
            stats = {}
            
            # 节点数量
            result = session.run("MATCH (j:Job) RETURN count(j) as count")
            stats['jobs'] = result.single()['count']
            
            result = session.run("MATCH (c:Company) RETURN count(c) as count")
            stats['companies'] = result.single()['count']
            
            result = session.run("MATCH (city:City) RETURN count(city) as count")
            stats['cities'] = result.single()['count']
            
            result = session.run("MATCH (s:Skill) RETURN count(s) as count")
            stats['skills'] = result.single()['count']
            
            result = session.run("MATCH (i:Industry) RETURN count(i) as count")
            stats['industries'] = result.single()['count']
            
            # 关系数量
            result = session.run("MATCH ()-[r:REQUIRES_SKILL]->() RETURN count(r) as count")
            stats['skill_relations'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:OFFERED_BY]->() RETURN count(r) as count")
            stats['company_relations'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:BELONGS_TO_INDUSTRY]->() RETURN count(r) as count")
            stats['industry_relations'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:LOCATED_IN]->() RETURN count(r) as count")
            stats['location_relations'] = result.single()['count']
            
            return stats


def main():
    """主函数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("="*60)
    print("🏗️  就业推荐知识图谱构建程序")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 连接Neo4j
    try:
        kg = JobKnowledgeGraph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    except Exception as e:
        print(f"❌ 连接Neo4j失败: {e}")
        print("请确保Neo4j服务已启动，并检查连接参数")
        return
    
    try:
        # 清空数据库（可选，谨慎使用）
        user_input = input("\n是否清空现有数据库？(y/n): ").strip().lower()
        if user_input == 'y':
            kg.clear_database()
        
        # 创建约束和索引
        kg.create_constraints()
        
        # 处理所有城市数据
        total_jobs = 0
        
        for city_dir in CITY_DIRS:
            city_path = os.path.join(base_dir, INPUT_BASE_DIR, city_dir)
            
            if not os.path.exists(city_path):
                print(f"⚠️ 目录不存在: {city_dir}")
                continue
            
            city_name = city_dir.replace('data_', '').replace('_advanced', '').upper()
            print(f"\n📁 处理城市: {city_name}")
            
            # 获取所有CSV文件
            csv_files = [f for f in os.listdir(city_path) if f.endswith('.csv')]
            
            for csv_file in csv_files:
                file_path = os.path.join(city_path, csv_file)
                print(f"  📄 {csv_file}")
                
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                    created = kg.batch_create_jobs(df)
                    total_jobs += created
                    print(f"  ✅ 创建 {created} 条记录")
                except Exception as e:
                    print(f"  ❌ 处理失败: {e}")
        
        # 获取统计信息
        print("\n" + "="*60)
        print("📊 知识图谱构建完成 - 统计信息")
        print("="*60)
        
        stats = kg.get_statistics()
        
        print("\n🔵 节点统计:")
        print(f"   • 职位 (Job): {stats['jobs']}")
        print(f"   • 公司 (Company): {stats['companies']}")
        print(f"   • 城市 (City): {stats['cities']}")
        print(f"   • 技能 (Skill): {stats['skills']}")
        print(f"   • 行业 (Industry): {stats['industries']}")
        
        print("\n🔗 关系统计:")
        print(f"   • 职位-技能 (REQUIRES_SKILL): {stats['skill_relations']}")
        print(f"   • 职位-公司 (OFFERED_BY): {stats['company_relations']}")
        print(f"   • 职位-行业 (BELONGS_TO_INDUSTRY): {stats['industry_relations']}")
        print(f"   • 公司-城市 (LOCATED_IN): {stats['location_relations']}")
        
        print("\n" + "="*60)
        print("✅ 知识图谱构建完成！")
        print("💡 访问 http://localhost:7474 在Neo4j Browser中查看图谱")
        print("="*60)
        
    finally:
        kg.close()


if __name__ == '__main__':
    main()
