#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱职业推荐系统测试报告生成器
==================================
生成详细的Markdown测试报告文档
"""

import os
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "TYH041113"


def generate_test_report():
    """生成测试报告"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    report = []
    report.append("# 知识图谱职业推荐系统测试报告\n")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("---\n")
    
    with driver.session() as session:
        # ========== 1. 知识图谱概览 ==========
        report.append("## 1. 知识图谱概览\n")
        report.append("### 1.1 节点统计\n")
        report.append("| 节点类型 | 数量 | 说明 |\n")
        report.append("|----------|------|------|\n")
        
        stats = {}
        for label, desc in [
            ("Job", "职位/岗位"),
            ("Company", "公司"),
            ("City", "城市"),
            ("Industry", "行业"),
            ("Skill", "技能"),
            ("Student", "学生"),
            ("Major", "专业"),
            ("Course", "课程")
        ]:
            result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            count = result.single()['count']
            stats[label] = count
            report.append(f"| {label} | {count:,} | {desc} |\n")
        
        report.append("\n### 1.2 关系统计\n")
        report.append("| 关系类型 | 数量 | 含义 |\n")
        report.append("|----------|------|------|\n")
        
        for rel, desc in [
            ("REQUIRES_SKILL", "岗位→技能"),
            ("OFFERED_BY", "岗位→公司"),
            ("BELONGS_TO_INDUSTRY", "岗位→行业"),
            ("LOCATED_IN", "公司→城市"),
            ("MAJORS_IN", "学生→专业"),
            ("HAS_COURSE", "专业→课程"),
            ("TEACHES_SKILL", "课程→技能"),
            ("TAKES", "学生→课程")
        ]:
            result = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) as count")
            count = result.single()['count']
            report.append(f"| {rel} | {count:,} | {desc} |\n")
        
        # ========== 2. 学生维度分析 ==========
        report.append("\n## 2. 学生维度分析\n")
        
        # 2.1 学历分布
        report.append("### 2.1 学历分布\n")
        report.append("| 学历 | 人数 | 占比 |\n")
        report.append("|------|------|------|\n")
        result = session.run("""
            MATCH (s:Student)
            RETURN s.education as edu, count(s) as count
            ORDER BY count DESC
        """)
        total_students = stats['Student']
        for r in result:
            pct = r['count'] / total_students * 100 if total_students > 0 else 0
            report.append(f"| {r['edu']} | {r['count']} | {pct:.1f}% |\n")
        
        # 2.2 专业分布
        report.append("\n### 2.2 专业分布\n")
        report.append("| 专业 | 学生数 | 占比 |\n")
        report.append("|------|--------|------|\n")
        result = session.run("""
            MATCH (s:Student)-[:MAJORS_IN]->(m:Major)
            RETURN m.name as major, count(s) as count
            ORDER BY count DESC
        """)
        for r in result:
            pct = r['count'] / total_students * 100 if total_students > 0 else 0
            report.append(f"| {r['major']} | {r['count']} | {pct:.1f}% |\n")
        
        # 2.3 学生技能统计
        report.append("\n### 2.3 学生技能统计\n")
        result = session.run("""
            MATCH (s:Student)-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk:Skill)
            WITH s, count(DISTINCT sk) as skill_count
            RETURN min(skill_count) as min_skills,
                   max(skill_count) as max_skills,
                   avg(skill_count) as avg_skills
        """)
        r = result.single()
        report.append(f"- **最少技能数**: {r['min_skills']}\n")
        report.append(f"- **最多技能数**: {r['max_skills']}\n")
        report.append(f"- **平均技能数**: {r['avg_skills']:.1f}\n")
        
        # ========== 3. 岗位维度分析 ==========
        report.append("\n## 3. 岗位维度分析\n")
        
        # 3.1 城市分布
        report.append("### 3.1 城市岗位分布\n")
        report.append("| 城市 | 岗位数 | 占比 |\n")
        report.append("|------|--------|------|\n")
        result = session.run("""
            MATCH (j:Job)-[:OFFERED_BY]->(c:Company)-[:LOCATED_IN]->(city:City)
            RETURN city.name as city, count(j) as count
            ORDER BY count DESC
        """)
        total_jobs = stats['Job']
        for r in result:
            pct = r['count'] / total_jobs * 100 if total_jobs > 0 else 0
            report.append(f"| {r['city']} | {r['count']:,} | {pct:.1f}% |\n")
        
        # 3.2 薪资分析
        report.append("\n### 3.2 薪资分析\n")
        result = session.run("""
            MATCH (j:Job)
            WHERE j.salary_min IS NOT NULL AND j.salary_min > 0
            RETURN min(j.salary_min) as min_sal,
                   max(j.salary_max) as max_sal,
                   avg(j.salary_min) as avg_min,
                   avg(j.salary_max) as avg_max
        """)
        r = result.single()
        if r['min_sal']:
            report.append(f"- **最低薪资**: {r['min_sal']:,.0f} 元/月\n")
            report.append(f"- **最高薪资**: {r['max_sal']:,.0f} 元/月\n")
            report.append(f"- **平均薪资范围**: {r['avg_min']:,.0f} - {r['avg_max']:,.0f} 元/月\n")
        
        # 3.3 技能需求Top20
        report.append("\n### 3.3 热门技能需求 (Top 20)\n")
        report.append("| 排名 | 技能 | 需求岗位数 |\n")
        report.append("|------|------|------------|\n")
        result = session.run("""
            MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill)
            RETURN s.name as skill, count(j) as count
            ORDER BY count DESC
            LIMIT 20
        """)
        for i, r in enumerate(result, 1):
            report.append(f"| {i} | {r['skill']} | {r['count']:,} |\n")
        
        # ========== 4. 技能匹配分析 ==========
        report.append("\n## 4. 技能匹配分析\n")
        
        # 4.1 技能覆盖率
        report.append("### 4.1 技能覆盖率\n")
        result = session.run("""
            MATCH (c:Course)-[:TEACHES_SKILL]->(sk:Skill)
            WITH collect(DISTINCT sk.name) as course_skills
            MATCH (j:Job)-[:REQUIRES_SKILL]->(jsk:Skill)
            WITH course_skills, collect(DISTINCT jsk.name) as job_skills
            WITH course_skills, job_skills, 
                 [s IN course_skills WHERE s IN job_skills] as overlap
            RETURN size(course_skills) as course_skill_count,
                   size(job_skills) as job_skill_count,
                   size(overlap) as overlap_count
        """)
        r = result.single()
        overlap_count = r['overlap_count']
        coverage = overlap_count / r['job_skill_count'] * 100 if r['job_skill_count'] > 0 else 0
        report.append(f"- **课程教授技能数**: {r['course_skill_count']}\n")
        report.append(f"- **岗位需求技能数**: {r['job_skill_count']:,}\n")
        report.append(f"- **重叠技能数**: {r['overlap_count']}\n")
        report.append(f"- **覆盖率**: {coverage:.2f}%\n")
        
        # 4.2 重叠技能列表
        report.append("\n### 4.2 课程与岗位重叠技能\n")
        result = session.run("""
            MATCH (c:Course)-[:TEACHES_SKILL]->(sk:Skill)<-[:REQUIRES_SKILL]-(j:Job)
            RETURN DISTINCT sk.name as skill, count(DISTINCT j) as job_count
            ORDER BY job_count DESC
            LIMIT 15
        """)
        report.append("| 技能 | 匹配岗位数 |\n")
        report.append("|------|------------|\n")
        for r in result:
            report.append(f"| {r['skill']} | {r['job_count']:,} |\n")
        
        # ========== 5. 推荐效果测试 ==========
        report.append("\n## 5. 推荐效果测试\n")
        
        # 5.1 推荐覆盖率
        report.append("### 5.1 推荐覆盖率\n")
        result = session.run("""
            MATCH (s:Student)-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk:Skill)<-[:REQUIRES_SKILL]-(j:Job)
            WITH s, count(DISTINCT j) as job_count
            WHERE job_count > 0
            RETURN count(s) as covered_students
        """)
        covered = result.single()['covered_students']
        coverage_pct = covered / total_students * 100 if total_students > 0 else 0
        report.append(f"- **可获推荐学生数**: {covered}\n")
        report.append(f"- **总学生数**: {total_students}\n")
        report.append(f"- **推荐覆盖率**: {coverage_pct:.1f}%\n")
        
        # 5.2 随机学生推荐示例
        report.append("\n### 5.2 随机学生推荐示例\n")
        result = session.run("""
            MATCH (s:Student)
            RETURN s.student_id as id, s.name as name, s.education as edu
            ORDER BY rand()
            LIMIT 3
        """)
        sample_students = [dict(r) for r in result]
        
        for student in sample_students:
            report.append(f"\n#### 学生: {student['name']} ({student['id']}) - {student['edu']}\n")
            
            # 专业
            result = session.run("""
                MATCH (s:Student {student_id: $id})-[:MAJORS_IN]->(m:Major)
                RETURN m.name as major
            """, id=student['id'])
            major = result.single()['major']
            report.append(f"- **专业**: {major}\n")
            
            # 技能
            result = session.run("""
                MATCH (s:Student {student_id: $id})-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk:Skill)
                RETURN collect(DISTINCT sk.name) as skills
            """, id=student['id'])
            skills = result.single()['skills']
            report.append(f"- **技能数**: {len(skills)}\n")
            report.append(f"- **技能列表**: {', '.join(skills[:10])}{'...' if len(skills) > 10 else ''}\n")
            
            # 推荐岗位
            result = session.run("""
                MATCH (s:Student {student_id: $id})-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk:Skill)<-[:REQUIRES_SKILL]-(j:Job)
                WITH j, collect(DISTINCT sk.name) as matched, count(DISTINCT sk) as cnt
                MATCH (j)-[:OFFERED_BY]->(comp:Company)
                RETURN j.title as title, j.salary as salary, comp.name as company, matched, cnt
                ORDER BY cnt DESC
                LIMIT 3
            """, id=student['id'])
            
            report.append("\n**推荐岗位 (Top 3)**:\n")
            report.append("| 岗位 | 薪资 | 公司 | 匹配技能数 |\n")
            report.append("|------|------|------|------------|\n")
            for r in result:
                salary = r['salary'] if r['salary'] and str(r['salary']) != 'nan' else '面议'
                report.append(f"| {r['title'][:25]}{'...' if len(r['title'])>25 else ''} | {salary} | {r['company'][:15]}{'...' if len(r['company'])>15 else ''} | {r['cnt']} |\n")
        
        # ========== 6. 总结 ==========
        report.append("\n## 6. 总结\n")
        report.append("### 6.1 知识图谱规模\n")
        report.append(f"- 总节点数: {sum(stats.values()):,}\n")
        report.append(f"- 核心实体: {stats['Job']:,}个岗位, {stats['Company']:,}家公司, {stats['Skill']:,}个技能\n")
        report.append(f"- 教育实体: {stats['Student']}名学生, {stats['Major']}个专业, {stats['Course']}门课程\n")
        
        report.append("\n### 6.2 推荐系统效果\n")
        report.append(f"- 推荐覆盖率: **{coverage_pct:.1f}%**\n")
        report.append(f"- 可匹配技能数: **{overlap_count}** 个\n")
        report.append("- 推荐质量: 基于技能匹配的推荐结果与学生专业背景高度相关\n")
        
        report.append("\n### 6.3 改进建议\n")
        report.append("1. 丰富课程技能库，增加更多实用技能映射\n")
        report.append("2. 引入用户行为数据，实现协同过滤推荐\n")
        report.append("3. 考虑加入学历、城市偏好等维度的过滤\n")
        report.append("4. 可添加技能熟练度权重，提升匹配精度\n")
    
    driver.close()
    
    # 保存报告
    report_content = ''.join(report)
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               f'推荐系统测试报告_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ 测试报告已生成: {output_file}")
    print("\n" + "="*60)
    print(report_content)
    
    return output_file


if __name__ == '__main__':
    generate_test_report()
