#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱职业推荐测试脚本
========================
基于学生技能匹配岗位，测试推荐效果

推荐逻辑:
Student -> TAKES -> Course -> TEACHES_SKILL -> Skill <- REQUIRES_SKILL <- Job
"""

import random
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "TYH041113"


def test_job_recommendation():
    """测试职业推荐效果"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("="*80)
    print("🎯 知识图谱职业推荐测试")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    with driver.session() as session:
        # 随机选取5名学生
        result = session.run("""
            MATCH (s:Student)
            RETURN s.student_id as id, s.name as name, s.education as education
            ORDER BY rand()
            LIMIT 5
        """)
        students = [dict(r) for r in result]
        
        for i, student in enumerate(students, 1):
            print(f"\n{'='*80}")
            print(f"👤 测试学生 #{i}: {student['name']} ({student['id']}) - {student['education']}")
            print("="*80)
            
            # 获取学生专业
            result = session.run("""
                MATCH (s:Student {student_id: $id})-[:MAJORS_IN]->(m:Major)
                RETURN m.name as major
            """, id=student['id'])
            record = result.single()
            major = record['major'] if record else '未知'
            print(f"📚 专业: {major}")
            
            # 获取学生选修课程
            result = session.run("""
                MATCH (s:Student {student_id: $id})-[:TAKES]->(c:Course)
                RETURN collect(c.name) as courses
            """, id=student['id'])
            courses = result.single()['courses']
            print(f"📖 选修课程 ({len(courses)}门): {', '.join(courses[:5])}{'...' if len(courses) > 5 else ''}")
            
            # 获取学生可能掌握的技能
            result = session.run("""
                MATCH (s:Student {student_id: $id})-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk:Skill)
                RETURN collect(DISTINCT sk.name) as skills
            """, id=student['id'])
            skills = result.single()['skills']
            print(f"🔧 可能技能 ({len(skills)}个): {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}")
            
            # 推荐岗位 - 基于技能匹配
            result = session.run("""
                MATCH (s:Student {student_id: $id})-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk:Skill)<-[:REQUIRES_SKILL]-(j:Job)
                WITH j, collect(DISTINCT sk.name) as matched_skills, count(DISTINCT sk) as match_count
                MATCH (j)-[:OFFERED_BY]->(comp:Company)
                OPTIONAL MATCH (comp)-[:LOCATED_IN]->(city:City)
                RETURN j.title as title, 
                       j.salary as salary,
                       comp.name as company,
                       city.name as city,
                       matched_skills,
                       match_count
                ORDER BY match_count DESC
                LIMIT 5
            """, id=student['id'])
            
            recommendations = [dict(r) for r in result]
            
            if recommendations:
                print(f"\n🎯 推荐岗位 (Top 5):")
                print("-"*80)
                for j, rec in enumerate(recommendations, 1):
                    skills_str = ', '.join(rec['matched_skills'][:3])
                    if len(rec['matched_skills']) > 3:
                        skills_str += f"...共{len(rec['matched_skills'])}个"
                    print(f"  {j}. {rec['title']}")
                    print(f"     💰 薪资: {rec['salary'] or '面议'}")
                    print(f"     🏢 公司: {rec['company']} ({rec['city'] or '未知'})")
                    print(f"     🔗 匹配技能({rec['match_count']}): {skills_str}")
                    print()
            else:
                print(f"\n⚠️ 未找到匹配岗位")
        
        # 总体统计
        print("\n" + "="*80)
        print("📊 推荐系统统计")
        print("="*80)
        
        # 技能覆盖率
        result = session.run("""
            MATCH (c:Course)-[:TEACHES_SKILL]->(sk:Skill)
            WITH collect(DISTINCT sk.name) as course_skills
            MATCH (j:Job)-[:REQUIRES_SKILL]->(jsk:Skill)
            WITH course_skills, collect(DISTINCT jsk.name) as job_skills
            WITH course_skills, job_skills, 
                 [s IN course_skills WHERE s IN job_skills] as overlap
            RETURN size(course_skills) as 课程技能数,
                   size(job_skills) as 岗位技能数,
                   size(overlap) as 重叠技能数
        """)
        stats = result.single()
        print(f"\n🔗 技能覆盖分析:")
        print(f"   • 课程教授技能: {stats['课程技能数']} 个")
        print(f"   • 岗位需要技能: {stats['岗位技能数']} 个")
        print(f"   • 重叠技能: {stats['重叠技能数']} 个")
        if stats['岗位技能数'] > 0:
            coverage = stats['重叠技能数'] / stats['岗位技能数'] * 100
            print(f"   • 覆盖率: {coverage:.1f}%")
        
        # 可推荐学生比例
        result = session.run("""
            MATCH (s:Student)-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk:Skill)<-[:REQUIRES_SKILL]-(j:Job)
            WITH s, count(DISTINCT j) as job_count
            WHERE job_count > 0
            RETURN count(s) as 可推荐学生数
        """)
        rec_students = result.single()['可推荐学生数']
        
        result = session.run("MATCH (s:Student) RETURN count(s) as total")
        total_students = result.single()['total']
        
        print(f"\n👥 学生推荐覆盖:")
        print(f"   • 总学生数: {total_students}")
        print(f"   • 可获得推荐: {rec_students}")
        print(f"   • 推荐覆盖率: {rec_students/total_students*100:.1f}%")
        
        print("\n" + "="*80)
        print("✅ 测试完成!")
        print("="*80)
    
    driver.close()


if __name__ == '__main__':
    test_job_recommendation()
