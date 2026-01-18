#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能智能清洗脚本
================
使用规则 + 特征分类来识别真正的技能，过滤非技能项

作者：AI Assistant
日期：2026-01-12
"""

import re
from collections import Counter

# ==================== 技能识别规则 ====================

# 技术技能关键词（高置信度）
TECH_KEYWORDS = {
    # 编程语言
    'PYTHON', 'JAVA', 'C++', 'C#', 'JAVASCRIPT', 'JS', 'GO', 'GOLANG', 'RUST',
    'PHP', 'RUBY', 'SWIFT', 'KOTLIN', 'SCALA', 'R', 'MATLAB', 'SQL', 'SHELL',
    'PERL', 'LUA', 'TYPESCRIPT', 'DART', 'C语言', 'COBOL', 'FORTRAN',
    
    # 前端
    'HTML', 'CSS', 'VUE', 'REACT', 'ANGULAR', 'JQUERY', 'WEBPACK', 'NODE',
    'NPM', 'SASS', 'LESS', 'BOOTSTRAP', 'ANTD', 'ELEMENT', 'UNI-APP',
    
    # 后端/框架
    'SPRING', 'SPRINGBOOT', 'DJANGO', 'FLASK', 'EXPRESS', 'FASTAPI',
    'MYBATIS', 'HIBERNATE', 'NETTY', 'DUBBO', 'GRPC',
    
    # 数据库
    'MYSQL', 'POSTGRESQL', 'ORACLE', 'MONGODB', 'REDIS', 'ELASTICSEARCH',
    'HBASE', 'CASSANDRA', 'SQLITE', 'MEMCACHED', 'KAFKA',
    
    # 云/DevOps
    'DOCKER', 'KUBERNETES', 'K8S', 'AWS', 'AZURE', 'GCP', 'LINUX', 'UNIX',
    'NGINX', 'APACHE', 'JENKINS', 'GIT', 'CI', 'CD', 'CICD', 'ANSIBLE',
    
    # AI/ML
    'TENSORFLOW', 'PYTORCH', 'KERAS', 'SKLEARN', 'OPENCV', 'NLP', 'CNN',
    'RNN', 'LSTM', 'BERT', 'GPT', 'TRANSFORMER', 'YOLO', 'GAN', 'LLM',
    
    # 大数据
    'HADOOP', 'SPARK', 'FLINK', 'HIVE', 'PRESTO', 'AIRFLOW', 'ETL',
    
    # 工具/软件
    'EXCEL', 'PPT', 'WORD', 'PS', 'AI', 'CAD', 'AUTOCAD', 'SOLIDWORKS',
    'CATIA', 'MATLAB', 'SIMULINK', 'LABVIEW', 'PROE', 'UG', 'CREO',
    
    # 测试
    'SELENIUM', 'JMETER', 'POSTMAN', 'JUNIT', 'PYTEST', 'APPIUM',
    
    # 协议/标准
    'TCP', 'IP', 'HTTP', 'HTTPS', 'REST', 'API', 'JSON', 'XML', 'MQTT',
    'WEBSOCKET', 'GRPC', 'CAN', 'LIN', 'SPI', 'I2C', 'UART',
}

# 行业技能关键词
INDUSTRY_KEYWORDS = {
    '运营', '营销', '销售', '管理', '设计', '开发', '测试', '架构',
    '算法', '工程师', '分析', '策划', '产品', '项目', '研发', '技术',
    '财务', '会计', '审计', '法务', '人力', '采购', '供应链', '质量',
    '安全', '运维', '数据', '客服', '编辑', '写作', '翻译', '培训',
}

# 非技能模式（正则）
NON_SKILL_PATTERNS = [
    r'^[0-9\-~～\.\s]+$',           # 纯数字/符号
    r'^\d+[KWkw万千]+',             # 薪资相关
    r'经验$',                        # 以"经验"结尾
    r'以上$',                        # 以"以上"结尾
    r'以下$',                        # 以"以下"结尾
    r'优先$',                        # 以"优先"结尾
    r'毕业',                         # 包含毕业
    r'应届',                         # 包含应届
    r'年限',                         # 年限相关
    r'人团队',                       # 团队规模
    r'人（含）',                     # 人数
    r'^\d+人',                       # 以数字人开头
    r'全日制',                       # 学历相关
    r'本科|硕士|博士|大专|学历',     # 学历
    r'^\d+届',                       # 届
    r'熟练|精通|了解|掌握',          # 程度描述
    r'必须|需要|要求',               # 要求类
    r'^可',                          # 以"可"开头
    r'^有.+经验',                    # 有XX经验
    r'工作经验',                     # 工作经验
    r'从业经验',                     # 从业经验
    r'项目经验$',                    # 以项目经验结尾
    r'相关专业',                     # 相关专业
    r'等相关',                       # 等相关
    r'^\（',                         # 以括号开头
    r'^（',                          # 以中文括号开头
    r'^\d+年',                       # 以数字年开头
    r'年及',                         # 年及
    r'薪$',                          # 以薪结尾
    r'双休|单休',                    # 休假
    r'五险一金',                     # 福利
    r'接受|接收',                    # 接受接收
    r'无经验',                       # 无经验
    r'实习生',                       # 实习生
    r'\\+$',                         # 以+结尾
    r'元$',                          # 以元结尾（薪资）
]

# 技能后缀模式（增加置信度）
SKILL_SUFFIXES = [
    '开发', '测试', '设计', '分析', '管理', '运营', '工程师', '架构',
    '系统', '平台', '框架', '工具', '技术', '算法', '编程', '语言',
    '协议', '接口', '驱动', '模块', '组件', '服务', '应用',
]

# 技能前缀模式
SKILL_PREFIXES = [
    'AI', 'ML', 'DL', 'NLP', '大数据', '云计算', '区块链', '物联网',
    '嵌入式', '前端', '后端', '全栈', '移动端', 'WEB', 'APP', '桌面',
    '数据', '图像', '视觉', '语音', '自动化', '智能', '机器学习',
]


def is_valid_skill(skill):
    """判断是否是有效技能"""
    if not skill or not isinstance(skill, str):
        return False, "空值"
    
    skill = skill.strip()
    
    # 长度检查
    if len(skill) < 2:
        return False, "太短"
    if len(skill) > 25:
        return False, "太长（可能是描述）"
    
    # 非技能模式检查
    for pattern in NON_SKILL_PATTERNS:
        if re.search(pattern, skill):
            return False, f"匹配非技能模式: {pattern}"
    
    # 计算技能得分
    score = 0
    reasons = []
    
    # 检查是否是已知技术关键词
    skill_upper = skill.upper().replace(' ', '')
    for keyword in TECH_KEYWORDS:
        if keyword in skill_upper or skill_upper in keyword:
            score += 3
            reasons.append(f"技术关键词: {keyword}")
            break
    
    # 检查行业关键词
    for keyword in INDUSTRY_KEYWORDS:
        if keyword in skill:
            score += 2
            reasons.append(f"行业关键词: {keyword}")
            break
    
    # 检查技能后缀
    for suffix in SKILL_SUFFIXES:
        if skill.endswith(suffix):
            score += 1
            reasons.append(f"技能后缀: {suffix}")
            break
    
    # 检查技能前缀
    for prefix in SKILL_PREFIXES:
        if skill.startswith(prefix):
            score += 1
            reasons.append(f"技能前缀: {prefix}")
            break
    
    # 全英文/英文+数字（很可能是技术名词）
    if re.match(r'^[A-Za-z0-9\.\-\+\#\s]+$', skill):
        if len(skill) >= 2:
            score += 2
            reasons.append("英文技术词")
    
    # 包含英文和中文混合（如"Python开发"）
    has_english = bool(re.search(r'[A-Za-z]', skill))
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', skill))
    if has_english and has_chinese:
        score += 1
        reasons.append("中英混合")
    
    # 特殊技能格式（如"C++"、".NET"）
    if re.match(r'^[A-Za-z\.\#\+]+$', skill):
        score += 1
        reasons.append("标准技术名")
    
    # 判定
    if score >= 2:
        return True, f"得分{score}: {'; '.join(reasons)}"
    elif score == 1:
        # 边界情况，进一步检查
        if len(skill) <= 10 and (has_english or '工' in skill or '师' in skill):
            return True, f"边界通过: {'; '.join(reasons)}"
    
    return False, f"得分不足({score})"


def clean_skills_file(input_file, output_file):
    """清洗技能文件"""
    print("="*60)
    print("🤖 技能智能清洗程序")
    print("="*60)
    
    # 读取技能
    with open(input_file, 'r', encoding='utf-8') as f:
        skills = [line.strip() for line in f if line.strip()]
    
    print(f"📥 读取技能数: {len(skills)}")
    
    valid_skills = []
    invalid_skills = []
    
    for skill in skills:
        is_valid, reason = is_valid_skill(skill)
        if is_valid:
            valid_skills.append(skill)
        else:
            invalid_skills.append((skill, reason))
    
    # 去重
    valid_skills = sorted(set(valid_skills))
    
    # 保存有效技能
    with open(output_file, 'w', encoding='utf-8') as f:
        for skill in valid_skills:
            f.write(skill + '\n')
    
    # 保存被过滤的技能（用于检查）
    filtered_file = output_file.replace('.txt', '_过滤.txt')
    with open(filtered_file, 'w', encoding='utf-8') as f:
        for skill, reason in invalid_skills:
            f.write(f"{skill}\t|\t{reason}\n")
    
    print(f"\n📊 清洗结果:")
    print(f"   ✅ 有效技能: {len(valid_skills)}")
    print(f"   ❌ 过滤项目: {len(invalid_skills)}")
    print(f"   📁 有效技能保存: {output_file}")
    print(f"   📁 过滤记录保存: {filtered_file}")
    
    # 显示部分过滤掉的项目
    print(f"\n🔍 过滤示例（前20个）:")
    for skill, reason in invalid_skills[:20]:
        print(f"   {skill[:20]:<20} | {reason}")
    
    print("\n" + "="*60)
    
    return valid_skills, invalid_skills


if __name__ == '__main__':
    import os
    import glob
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 查找最新的技能列表文件
    skill_files = glob.glob(os.path.join(base_dir, '技能列表_*.txt'))
    skill_files = [f for f in skill_files if '过滤' not in f and '清洗' not in f]
    
    if not skill_files:
        print("❌ 未找到技能列表文件")
        exit(1)
    
    # 使用最新的文件
    input_file = max(skill_files, key=os.path.getmtime)
    output_file = os.path.join(base_dir, '技能列表_清洗后.txt')
    
    print(f"📄 输入文件: {os.path.basename(input_file)}")
    
    clean_skills_file(input_file, output_file)
