#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复知识图谱中因NaN值导致失败的记录
只处理行业字段为空的职位，补充它们到图谱中
"""

import os
import re
import pandas as pd
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "TYH041113"

# 输入目录
INPUT_BASE_DIR = '第二次清洗_进阶'

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


def is_valid_value(value):
    """检查值是否有效（非空、非NaN）"""
    if value is None:
        return False
    if pd.isna(value):
        return False
    if isinstance(value, str) and value.strip() == '':
        return False
    return True


def fix_failed_records():
    """修复因NaN导致失败的记录"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("="*60)
    print("🔧 修复失败记录")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print("✅ 已连接到Neo4j")
    
    fixed_count = 0
    skipped_count = 0
    
    try:
        for city_dir in CITY_DIRS:
            city_path = os.path.join(base_dir, INPUT_BASE_DIR, city_dir)
            
            if not os.path.exists(city_path):
                continue
            
            city_name = city_dir.replace('data_', '').replace('_advanced', '').upper()
            print(f"\n📁 处理城市: {city_name}")
            csv_files = [f for f in os.listdir(city_path) if f.endswith('.csv')]
            
            for csv_file in csv_files:
                file_path = os.path.join(city_path, csv_file)
                print(f"  📄 {csv_file}", end=' ', flush=True)
                df = pd.read_csv(file_path, encoding='utf-8')
                
                file_fixed = 0
                file_skipped = 0
                
                # 找出行业为空的记录
                for idx, row in df.iterrows():
                    job_data = row.to_dict()
                    industry = job_data.get('行业')
                    
                    # 只处理行业为NaN的记录
                    if not is_valid_value(industry):
                        job_url = job_data.get('职位URL', f"job_{hash(str(job_data))}")
                        
                        with driver.session() as session:
                            # 检查职位是否已存在
                            result = session.run(
                                "MATCH (j:Job {url: $url}) RETURN j",
                                url=job_url
                            )
                            
                            if result.single() is None:
                                # 职位不存在，需要创建
                                city = job_data.get('城市')
                                company = job_data.get('公司')
                                scale = job_data.get('公司规模', '')
                                skills = job_data.get('技能', '')
                                
                                has_city = is_valid_value(city)
                                has_company = is_valid_value(company)
                                
                                # 创建城市节点
                                if has_city:
                                    session.run("MERGE (city:City {name: $name})", name=city)
                                
                                # 创建公司节点
                                if has_company:
                                    session.run(
                                        "MERGE (c:Company {name: $name}) SET c.scale = $scale",
                                        name=company,
                                        scale=scale if is_valid_value(scale) else ''
                                    )
                                    if has_city:
                                        session.run("""
                                            MATCH (c:Company {name: $company})
                                            MATCH (city:City {name: $city})
                                            MERGE (c)-[:LOCATED_IN]->(city)
                                        """, company=company, city=city)
                                
                                # 创建职位节点
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
                                    description=str(job_data.get('工作描述', ''))[:500] if job_data.get('工作描述') else '',
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
                                        MATCH (c:Company {name: $company})
                                        MERGE (j)-[:OFFERED_BY]->(c)
                                    """, url=job_url, company=company)
                                
                                # 创建技能关系
                                if skills and isinstance(skills, str):
                                    skill_list = re.split(r'[,，、;；/\|]', skills)
                                    for skill in skill_list:
                                        skill = skill.strip()
                                        if skill and len(skill) >= 2:
                                            session.run("MERGE (s:Skill {name: $name})", name=skill)
                                            session.run("""
                                                MATCH (j:Job {url: $url})
                                                MATCH (s:Skill {name: $skill})
                                                MERGE (j)-[:REQUIRES_SKILL]->(s)
                                            """, url=job_url, skill=skill)
                                
                                fixed_count += 1
                                file_fixed += 1
                            else:
                                skipped_count += 1
                                file_skipped += 1
                
                print(f"-> 新增: {file_fixed}, 跳过: {file_skipped}")
        
        # 获取最终统计
        with driver.session() as session:
            result = session.run("MATCH (j:Job) RETURN count(j) as total")
            total_jobs = result.single()['total']
        
        print(f"\n✅ 修复完成!")
        print(f"   • 新增职位: {fixed_count}")
        print(f"   • 已存在跳过: {skipped_count}")
        print(f"   • 当前职位总数: {total_jobs}")
        
    finally:
        driver.close()
        print("🔒 Neo4j连接已关闭")


if __name__ == '__main__':
    fix_failed_records()
