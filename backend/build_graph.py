#!/usr/bin/env python3
"""
使用流水线中的Neo4jUploader构建职位知识图谱
"""

import os
import sys
import importlib.util
import pandas as pd
from neo4j import GraphDatabase

# 配置Neo4j连接信息
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "TYH041113"

# 清洗后的数据路径
CLEAN_DATA_PATH = "../模块_数据处理/清洗输出/第二次清洗/"

class Neo4jUploader:
    """Neo4j知识图谱上传器"""

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✅ 已连接到Neo4j: {uri}")
        
        # 显示当前数据库状态
        try:
            total_nodes, total_rels = self.get_neo4j_stats()
            print(f"📊 当前数据库: {total_nodes:,} 个节点, {total_rels:,} 条关系")
        except Exception as e:
            print(f"⚠️  无法获取数据库统计: {e}")

    def close(self):
        self.driver.close()

    def get_neo4j_stats(self):
        """获取Neo4j数据库统计信息"""
        with self.driver.session() as session:
            result = session.run("CALL db.stats.retrieve('GRAPH COUNTS')")
            stats = result.single()[0]
            total_nodes = stats['nodes']['total'] if 'nodes' in stats else 0
            total_rels = stats['relationships']['total'] if 'relationships' in stats else 0
            return total_nodes, total_rels

    def _is_valid_value(self, value):
        """检查值是否有效"""
        if value is None:
            return False
        if pd.isna(value):
            return False
        if isinstance(value, str) and value.strip() == '':
            return False
        return True

    def clear_database(self):
        """清空数据库中的所有数据（已禁用）"""
        print("⚠️  清空数据库功能已禁用，保护现有数据安全")
        return False

    def create_job_graph(self, job_data):
        """创建职位图谱"""
        import re
        
        with self.driver.session() as session:
            city = job_data.get('城市')
            company = job_data.get('公司')
            industry = job_data.get('行业')
            scale = job_data.get('公司规模', '')
            
            has_city = self._is_valid_value(city)
            has_company = self._is_valid_value(company)
            has_industry = self._is_valid_value(industry)
            
            # 创建城市
            if has_city:
                session.run("MERGE (city:City {name: $name})", name=city)
            
            # 创建公司
            if has_company:
                session.run("""
                    MERGE (c:Company {name: $name})
                    SET c.scale = $scale
                """, name=company, scale=scale if self._is_valid_value(scale) else '')
                
                if has_city:
                    session.run("""
                        MATCH (c:Company {name: $company})
                        MATCH (city:City {name: $city})
                        MERGE (c)-[:LOCATED_IN]->(city)
                    """, company=company, city=city)
            
            # 创建行业
            if has_industry:
                session.run("MERGE (i:Industry {name: $name})", name=industry)
            
            # 创建职位
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
                description=str(job_data.get('工作描述', ''))[:500],
                salary=job_data.get('薪资', ''),
                salary_min=job_data.get('薪资_最小值'),
                salary_max=job_data.get('薪资_最大值'),
                annual_months=job_data.get('年薪月数'),
                publish_time=job_data.get('发布时间', '')
            )
            
            # 创建关系
            if has_company:
                session.run("""
                    MATCH (j:Job {url: $url})
                    MATCH (c:Company {name: $company})
                    MERGE (j)-[:OFFERED_BY]->(c)
                """, url=job_url, company=company)
            
            if has_industry:
                session.run("""
                    MATCH (j:Job {url: $url})
                    MATCH (i:Industry {name: $industry})
                    MERGE (j)-[:BELONGS_TO_INDUSTRY]->(i)
                """, url=job_url, industry=industry)
            
            # 创建技能关系
            skills = job_data.get('技能', '')
            if skills and isinstance(skills, str):
                skill_list = re.split(r'[,，、;；/\\|]', skills)
                for skill in skill_list:
                    skill = skill.strip()
                    if skill and len(skill) >= 2:
                        session.run("MERGE (s:Skill {name: $name})", name=skill)
                        session.run("""
                            MATCH (j:Job {url: $url})
                            MATCH (s:Skill {name: $skill})
                            MERGE (j)-[:REQUIRES_SKILL]->(s)
                        """, url=job_url, skill=skill)

    def upload_cleaned_jobs(self, input_dir):
        """上传清洗后的职位数据"""
        print(f"📁 开始上传数据: {input_dir}")
        
        # 遍历所有子目录
        total_count = 0
        for subdir in os.listdir(input_dir):
            subdir_path = os.path.join(input_dir, subdir)
            if os.path.isdir(subdir_path):
                print(f"🔍 处理目录: {subdir}")
                
                # 找到所有CSV文件
                csv_files = [f for f in os.listdir(subdir_path) if f.endswith('_advanced.csv')]
                
                for csv_file in csv_files:
                    file_path = os.path.join(subdir_path, csv_file)
                    print(f"📄 处理文件: {csv_file}")
                    
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8')
                        file_count = 0
                        
                        for _, row in df.iterrows():
                            job_data = row.to_dict()
                            self.create_job_graph(job_data)
                            file_count += 1
                            total_count += 1
                            
                            if total_count % 100 == 0:
                                print(f"  📊 总进度: {total_count}")
                        
                        print(f"  ✅ 完成文件: {csv_file}, 处理了 {file_count} 条记录")
                    
                    except Exception as e:
                        print(f"  ❌ 处理文件 {csv_file} 时出错: {e}")
                        continue
        
        print(f"✅ 所有数据上传完成: {total_count} 条记录")
        return total_count

def main():
    print("="*60)
    print("🏗️  构建职位知识图谱")
    print("="*60)
    
    try:
        # 初始化上传器
        uploader = Neo4jUploader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        
        try:
            # 清空数据库
            if not uploader.clear_database():
                print("❌ 清空数据库失败")
                return
            
            # 上传数据
            if os.path.exists(CLEAN_DATA_PATH):
                uploader.upload_cleaned_jobs(CLEAN_DATA_PATH)
            else:
                print(f"❌ 数据路径不存在: {CLEAN_DATA_PATH}")
                return
            
            # 显示最终状态
            total_nodes, total_rels = uploader.get_neo4j_stats()
            print(f"\n📊 最终数据库状态: {total_nodes:,} 个节点, {total_rels:,} 条关系")
            print("✅ 知识图谱构建完成！")
            
        finally:
            uploader.close()
            
    except Exception as e:
        print(f"❌ 构建图谱时出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
