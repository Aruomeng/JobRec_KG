#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能提取脚本
============
从所有清洗后的职位数据中提取技能，生成去重的技能列表

作者：AI Assistant
日期：2026-01-12
"""

import os
import pandas as pd
from datetime import datetime

# 输入目录（进阶清洗后的数据）
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

def clean_skill(skill):
    """清洗单个技能"""
    import re
    
    if not skill or not isinstance(skill, str):
        return None
    
    skill = skill.strip()
    
    # 过滤空值
    if not skill:
        return None
    
    # 过滤太短的（2个字符以下）
    if len(skill) <= 1:
        return None
    
    # 过滤纯数字或数字开头的无意义项（如"0-1"、"1-10"）
    if re.match(r'^[\d\-~～]+$', skill):
        return None
    
    # 过滤以数字开头且长度短的（如"00 后"、"10W+阅读"）
    if re.match(r'^\d', skill) and len(skill) < 6:
        return None
    
    # 过滤以特殊字符开头
    if skill[0] in './%#@!*':
        return None
    
    # 过滤URL编码的内容
    if '%' in skill:
        return None
    
    # 过滤包含"年"的（可能是经验要求）
    if '年以上' in skill or '年经验' in skill or '届' in skill or '毕业' in skill:
        return None
    
    # 过滤包含薪资信息
    if '薪' in skill:
        return None
    
    # 过滤太长的描述（可能是完整句子而非技能）
    if len(skill) > 30:
        return None
    
    # 过滤包含人数描述
    if '人以下' in skill or '人以上' in skill or '人团队' in skill:
        return None
    
    # 过滤包含"经验"字样的长短语
    if '经验' in skill and len(skill) > 8:
        return None
    
    # 过滤包含"优先"的
    if '优先' in skill:
        return None
    
    # 统一大小写（英文技能转大写）
    if skill.isascii():
        skill = skill.upper()
    
    return skill


def extract_skills_from_file(file_path):
    """从单个CSV文件提取技能"""
    skills = set()
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        
        if '技能' not in df.columns:
            return skills
        
        for skill_str in df['技能']:
            if pd.isna(skill_str) or not isinstance(skill_str, str):
                continue
            
            skill_str = skill_str.strip()
            if not skill_str:
                continue
            
            # 支持多种分隔符：逗号、中文逗号、斜杠、分号、顿号
            import re
            skill_list = re.split(r'[,，、;；/\|]', skill_str)
            
            for skill in skill_list:
                cleaned = clean_skill(skill)
                if cleaned:
                    skills.add(cleaned)
    
    except Exception as e:
        print(f"处理文件失败 {file_path}: {e}")
    
    return skills


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("="*60)
    print("🔍 技能提取程序启动")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    all_skills = set()
    file_count = 0
    
    for city_dir in CITY_DIRS:
        city_path = os.path.join(base_dir, INPUT_BASE_DIR, city_dir)
        
        if not os.path.exists(city_path):
            print(f"⚠️ 目录不存在: {city_dir}")
            continue
        
        city_name = city_dir.replace('data_', '').replace('_advanced', '').upper()
        
        # 获取所有CSV文件
        csv_files = [f for f in os.listdir(city_path) if f.endswith('.csv')]
        
        city_skills = set()
        for csv_file in csv_files:
            file_path = os.path.join(city_path, csv_file)
            skills = extract_skills_from_file(file_path)
            city_skills.update(skills)
            file_count += 1
        
        print(f"📁 {city_name}: {len(city_skills)} 个技能")
        all_skills.update(city_skills)
    
    # 排序技能列表
    sorted_skills = sorted(all_skills)
    
    # 输出到文件
    output_file = os.path.join(base_dir, f'技能列表_{timestamp}.txt')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for skill in sorted_skills:
            f.write(skill + '\n')
    
    print("\n" + "="*60)
    print("📊 提取完成")
    print("="*60)
    print(f"📁 处理文件数: {file_count}")
    print(f"🏷️  技能总数（去重后）: {len(sorted_skills)}")
    print(f"📄 输出文件: {output_file}")
    print("="*60)
    
    # 打印前20个技能示例
    print("\n📋 技能示例（前20个）:")
    for i, skill in enumerate(sorted_skills[:20], 1):
        print(f"   {i}. {skill}")
    if len(sorted_skills) > 20:
        print(f"   ... 还有 {len(sorted_skills) - 20} 个技能")


if __name__ == '__main__':
    main()
