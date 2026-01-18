#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
职业数据处理流水线
==================
统一处理职业数据从原始CSV到Neo4j知识图谱的完整流程

功能:
1. 第一次数据清洗 - 去除缺失必填字段的记录
2. 第二次数据清洗 - URL去重、薪资标准化、数据增强
3. 上传Neo4j - 构建知识图谱

作者: AI Assistant
日期: 2026-01-12
"""

import os
import re
import json
import argparse
import pandas as pd
from datetime import datetime
from neo4j import GraphDatabase

# ==================== 配置加载 ====================
def load_config():
    """加载配置文件"""
    config_file = os.path.join(os.path.dirname(__file__), 'pipeline_config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()

# ==================== 安全检查函数 ====================
def confirm_neo4j_operation():
    """确认Neo4j写入操作"""
    safety_config = CONFIG.get('safety', {})
    
    if not safety_config.get('require_confirmation', True):
        return True
    
    if safety_config.get('backup_reminder', True):
        print("\n" + "="*60)
        print("⚠️  安全提醒")
        print("="*60)
        print("即将向Neo4j数据库写入数据！")
        print("\n建议操作:")
        print("  1. 确认已备份Neo4j数据库")
        print("  2. 检查数据文件是否正确")
        print("  3. 建议先用小量数据测试")
        print("\n数据库连接信息:")
        print(f"  URI: {CONFIG['neo4j']['uri']}")
        print(f"  用户: {CONFIG['neo4j']['user']}")
        print("="*60)
    
    while True:
        response = input("\n是否继续上传到Neo4j? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            print("❌ 用户取消操作")
            return False
        else:
            print("⚠️  请输入 yes 或 no")

def get_neo4j_stats(driver):
    """获取Neo4j数据库统计信息"""
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as total_nodes")
        total_nodes = result.single()['total_nodes']
        
        result = session.run("MATCH ()-[r]->() RETURN count(r) as total_rels")
        total_rels = result.single()['total_rels']
        
    return total_nodes, total_rels

# ==================== 第一次清洗 ====================
class FirstCleaner:
    """第一次数据清洗器"""
    
    def __init__(self, required_fields):
        self.required_fields = required_fields
    
    def check_required_fields(self, row):
        """检查必填字段"""
        missing_fields = []
        for field in self.required_fields:
            value = row.get(field, None)
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ''):
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"缺少必填字段: {', '.join(missing_fields)}"
        return True, ""
    
    def clean_city(self, input_dir, output_dir):
        """清洗指定城市的数据"""
        os.makedirs(output_dir, exist_ok=True)
        
        csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
        total_stats = {'original': 0, 'cleaned': 0, 'removed': 0}
        
        print(f"📁 第一次清洗: {input_dir}")
        
        for csv_file in csv_files:
            input_path = os.path.join(input_dir, csv_file)
            output_path = os.path.join(output_dir, csv_file)
            
            df = pd.read_csv(input_path, encoding='utf-8')
            total_stats['original'] += len(df)
            
            valid_rows = []
            for _, row in df.iterrows():
                is_valid, _ = self.check_required_fields(row)
                if is_valid:
                    valid_rows.append(row)
            
            if valid_rows:
                cleaned_df = pd.DataFrame(valid_rows)
                cleaned_df.to_csv(output_path, index=False, encoding='utf-8')
                total_stats['cleaned'] += len(cleaned_df)
                total_stats['removed'] += len(df) - len(cleaned_df)
        
        print(f"  ✅ 原始: {total_stats['original']}, 清洗后: {total_stats['cleaned']}, 删除: {total_stats['removed']}")
        return total_stats

# ==================== 第二次清洗 ====================
class SecondCleaner:
    """第二次数据清洗器（进阶）"""
    
    @staticmethod
    def standardize_salary(salary_str):
        """标准化薪资"""
        if pd.isna(salary_str):
            return None
        
        salary_str = str(salary_str).strip()
        if salary_str in ['面议', '', 'nan']:
            return None
        
        # 匹配 "4-7万" 格式
        match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*万', salary_str)
        if match:
            min_sal = float(match.group(1)) * 10000
            max_sal = float(match.group(2)) * 10000
            return f"{int(min_sal)}-{int(max_sal)}"
        
        # 匹配 "4-7千" 格式
        match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*千', salary_str)
        if match:
            min_sal = float(match.group(1)) * 1000
            max_sal = float(match.group(2)) * 1000
            return f"{int(min_sal)}-{int(max_sal)}"
        
        return None
    
    @staticmethod
    def extract_salary_details(salary_str):
        """提取薪资详情"""
        if pd.isna(salary_str):
            return None, None, None
        
        salary_str = str(salary_str).strip()
        
        # 提取薪资范围
        match = re.search(r'(\d+)-(\d+)', salary_str)
        if match:
            min_sal = int(match.group(1))
            max_sal = int(match.group(2))
        else:
            return None, None, None
        
        # 提取年薪月数
        months_match = re.search(r'(\d+)薪', salary_str)
        annual_months = int(months_match.group(1)) if months_match else 12
        
        return min_sal, max_sal, annual_months
    
    def clean_city(self, input_dir, output_dir):
        """清洗指定城市的数据"""
        os.makedirs(output_dir, exist_ok=True)
        
        csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
        total_stats = {'original': 0, 'cleaned': 0, 'duplicates': 0}
        
        print(f"📁 第二次清洗: {input_dir}")
        
        for csv_file in csv_files:
            input_path = os.path.join(input_dir, csv_file)
            output_file = csv_file.replace('.csv', '_advanced.csv')
            output_path = os.path.join(output_dir, output_file)
            
            df = pd.read_csv(input_path, encoding='utf-8')
            total_stats['original'] += len(df)
            
            # URL去重
            df_cleaned = df.drop_duplicates(subset=['职位URL'], keep='first')
            total_stats['duplicates'] += len(df) - len(df_cleaned)
            
            # 薪资处理
            df_cleaned['薪资_最小值'] = None
            df_cleaned['薪资_最大值'] = None
            df_cleaned['年薪月数'] = None
            
            for idx, row in df_cleaned.iterrows():
                min_sal, max_sal, months = self.extract_salary_details(row.get('薪资'))
                df_cleaned.at[idx, '薪资_最小值'] = min_sal
                df_cleaned.at[idx, '薪资_最大值'] = max_sal
                df_cleaned.at[idx, '年薪月数'] = months
                
                standardized = self.standardize_salary(row.get('薪资'))
                if standardized:
                    df_cleaned.at[idx, '薪资'] = standardized
            
            df_cleaned.to_csv(output_path, index=False, encoding='utf-8')
            total_stats['cleaned'] += len(df_cleaned)
        
        print(f"  ✅ 原始: {total_stats['original']}, 清洗后: {total_stats['cleaned']}, 去重: {total_stats['duplicates']}")
        return total_stats

# ==================== Neo4j上传器 ====================
class Neo4jUploader:
    """Neo4j知识图谱上传器"""
    
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✅ 已连接到Neo4j: {uri}")
        
        # 显示当前数据库状态
        try:
            total_nodes, total_rels = get_neo4j_stats(self.driver)
            print(f"📊 当前数据库: {total_nodes:,} 个节点, {total_rels:,} 条关系")
        except Exception as e:
            print(f"⚠️  无法获取数据库统计: {e}")
    
    def close(self):
        self.driver.close()
    
    def _is_valid_value(self, value):
        """检查值是否有效"""
        if value is None:
            return False
        if pd.isna(value):
            return False
        if isinstance(value, str) and value.strip() == '':
            return False
        return True
    
    def create_job_graph(self, job_data):
        """创建职位图谱"""
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
    
    def upload_city(self, input_dir):
        """上传指定城市的数据"""
        csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
        total_count = 0
        
        print(f"📁 上传到Neo4j: {input_dir}")
        
        for csv_file in csv_files:
            file_path = os.path.join(input_dir, csv_file)
            df = pd.read_csv(file_path, encoding='utf-8')
            
            for _, row in df.iterrows():
                job_data = row.to_dict()
                self.create_job_graph(job_data)
                total_count += 1
                
                if total_count % 100 == 0:
                    print(f"  📊 进度: {total_count}")
        
        print(f"  ✅ 上传完成: {total_count} 条记录")
        return total_count

# ==================== 流水线主程序 ====================
class JobDataPipeline:
    """数据处理流水线"""
    
    def __init__(self):
        self.config = CONFIG
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_data_dir = self.config.get('base_data_dir', '.')
        self.base_dir = os.path.normpath(os.path.join(script_dir, base_data_dir))
        self.first_cleaner = FirstCleaner(self.config['required_fields'])
        self.second_cleaner = SecondCleaner()
    
    def find_cities(self):
        """查找所有城市目录"""
        cities = []
        for item in os.listdir(self.base_dir):
            if os.path.isdir(os.path.join(self.base_dir, item)) and item.startswith('data_'):
                city_name = item.replace('data_', '')
                cities.append(city_name)
        return cities
    
    def process_city(self, city_name, clean1=True, clean2=True, upload=True):
        """处理单个城市数据"""
        print(f"\n{'='*60}")
        print(f"🏙️  处理城市: {city_name.upper()}")
        print(f"{'='*60}")
        
        # 目录路径
        raw_dir = os.path.join(self.base_dir, f'data_{city_name}')
        clean1_dir = os.path.join(self.base_dir, f'第一次清洗_{city_name}')
        clean2_dir = os.path.join(self.base_dir, '第二次清洗_进阶', f'data_{city_name}_advanced')
        
        if not os.path.exists(raw_dir):
            print(f"❌ 原始数据目录不存在: {raw_dir}")
            return
        
        # 第一次清洗
        if clean1:
            stats1 = self.first_cleaner.clean_city(raw_dir, clean1_dir)
        else:
            print(f"⏭️  跳过第一次清洗")
        
        # 第二次清洗
        if clean2:
            source_dir = clean1_dir if clean1 else raw_dir
            stats2 = self.second_cleaner.clean_city(source_dir, clean2_dir)
        else:
            print(f"⏭️  跳过第二次清洗")
        
        # 上传Neo4j
        if upload:
            # 安全确认
            if not confirm_neo4j_operation():
                print(f"⏭️  跳过上传Neo4j（用户取消）")
                return
            
            uploader = Neo4jUploader(
                self.config['neo4j']['uri'],
                self.config['neo4j']['user'],
                self.config['neo4j']['password']
            )
            try:
                uploader.upload_city(clean2_dir)
            finally:
                uploader.close()
        else:
            print(f"⏭️  跳过上传Neo4j")
        
        print(f"✅ 城市 {city_name} 处理完成")

def main():
    parser = argparse.ArgumentParser(description='职业数据处理流水线')
    parser.add_argument('--city', type=str, help='指定处理的城市（如shanghai）')
    parser.add_argument('--all-new', action='store_true', help='处理所有新城市')
    parser.add_argument('--clean1', action='store_true', help='执行第一次清洗')
    parser.add_argument('--clean2', action='store_true', help='执行第二次清洗')
    parser.add_argument('--upload', action='store_true', help='上传到Neo4j')
    parser.add_argument('--all', action='store_true', help='执行完整流程')
    
    args = parser.parse_args()
    
    pipeline = JobDataPipeline()
    
    # 确定处理阶段
    if args.all:
        clean1, clean2, upload = True, True, True
    else:
        clean1 = args.clean1
        clean2 = args.clean2
        upload = args.upload
        if not (clean1 or clean2 or upload):
            clean1, clean2, upload = True, True, True
    
    print("="*60)
    print("🏗️  职业数据处理流水线")  
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 处理城市
    if args.city:
        pipeline.process_city(args.city, clean1, clean2, upload)
    elif args.all_new:
        cities = pipeline.find_cities()
        processed = pipeline.config.get('processed_cities', [])
        new_cities = [c for c in cities if c not in processed]
        
        if new_cities:
            print(f"\n发现 {len(new_cities)} 个新城市: {', '.join(new_cities)}")
            for city in new_cities:
                pipeline.process_city(city, clean1, clean2, upload)
        else:
            print("\n没有发现新城市")
    else:
        print("\n❌ 请指定 --city 或 --all-new 参数")
        print("示例: python job_data_pipeline.py --city shanghai --all")
    
    print("\n" + "="*60)
    print("✅ 流水线执行完成")
    print("="*60)

if __name__ == '__main__':
    main()
