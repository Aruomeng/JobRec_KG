#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将学生数据导入Neo4j知识图谱
============================
导入Student、Major、Course节点，并建立关系

节点:
- Student: student_id, name, education
- Major: name
- Course: name
- Skill: name (复用已有节点)

关系:
- (Student)-[:MAJORS_IN]->(Major)
- (Major)-[:HAS_COURSE]->(Course)
- (Course)-[:TEACHES_SKILL]->(Skill)
- (Student)-[:TAKES]->(Course)
"""

import json
import os
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "TYH041113"


class StudentGraphImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✅ 已连接到Neo4j: {uri}")
        
        # 显示当前数据库状态
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as total")
                total_nodes = result.single()['total']
                result = session.run("MATCH (s:Student) RETURN count(s) as count")
                student_count = result.single()['count']
                print(f"📊 当前数据库: {total_nodes:,} 个节点, {student_count} 名学生")
                if student_count > 0:
                    print(f"⚠️  注意: 数据库中已有学生数据!")
        except Exception as e:
            print(f"⚠️  无法获取数据库统计: {e}")
    
    def close(self):
        self.driver.close()
        print("🔒 Neo4j连接已关闭")
    
    def create_constraints(self):
        """创建约束"""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Student) REQUIRE s.student_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Major) REQUIRE m.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Course) REQUIRE c.name IS UNIQUE",
        ]
        with self.driver.session() as session:
            for c in constraints:
                try:
                    session.run(c)
                except Exception as e:
                    print(f"⚠️ 约束警告: {e}")
        print("📋 约束已创建")
    
    def import_domain_data(self, domain_data):
        """导入专业、课程、技能数据"""
        with self.driver.session() as session:
            for major_name, courses in domain_data.items():
                # 创建专业节点
                session.run("MERGE (m:Major {name: $name})", name=major_name)
                
                for course_name, skills in courses.items():
                    # 创建课程节点
                    session.run("MERGE (c:Course {name: $name})", name=course_name)
                    
                    # 专业-课程关系
                    session.run("""
                        MATCH (m:Major {name: $major})
                        MATCH (c:Course {name: $course})
                        MERGE (m)-[:HAS_COURSE]->(c)
                    """, major=major_name, course=course_name)
                    
                    # 课程-技能关系
                    for skill_name in skills:
                        # 复用或创建技能节点
                        session.run("MERGE (s:Skill {name: $name})", name=skill_name)
                        session.run("""
                            MATCH (c:Course {name: $course})
                            MATCH (s:Skill {name: $skill})
                            MERGE (c)-[:TEACHES_SKILL]->(s)
                        """, course=course_name, skill=skill_name)
        
        print("📚 专业-课程-技能数据已导入")
    
    def import_students(self, students):
        """导入学生数据"""
        count = 0
        with self.driver.session() as session:
            for student in students:
                # 创建学生节点
                session.run("""
                    MERGE (s:Student {student_id: $id})
                    SET s.name = $name,
                        s.education = $education
                """,
                    id=student['student_id'],
                    name=student['name'],
                    education=student['education']
                )
                
                # 学生-专业关系
                session.run("""
                    MATCH (s:Student {student_id: $id})
                    MATCH (m:Major {name: $major})
                    MERGE (s)-[:MAJORS_IN]->(m)
                """, id=student['student_id'], major=student['major'])
                
                # 学生-课程关系
                for course in student['courses']:
                    course_name = course['name'] if isinstance(course, dict) else course
                    session.run("""
                        MATCH (s:Student {student_id: $id})
                        MATCH (c:Course {name: $course})
                        MERGE (s)-[:TAKES]->(c)
                    """, id=student['student_id'], course=course_name)
                
                count += 1
                if count % 20 == 0:
                    print(f"  📊 进度: {count}/{len(students)}")
        
        print(f"👥 已导入 {count} 名学生")
        return count
    
    def get_statistics(self):
        """获取统计信息"""
        stats = {}
        with self.driver.session() as session:
            result = session.run("MATCH (s:Student) RETURN count(s) as count")
            stats['students'] = result.single()['count']
            
            result = session.run("MATCH (m:Major) RETURN count(m) as count")
            stats['majors'] = result.single()['count']
            
            result = session.run("MATCH (c:Course) RETURN count(c) as count")
            stats['courses'] = result.single()['count']
            
            result = session.run("MATCH (s:Skill) RETURN count(s) as count")
            stats['skills'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:MAJORS_IN]->() RETURN count(r) as count")
            stats['majors_in'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:HAS_COURSE]->() RETURN count(r) as count")
            stats['has_course'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:TEACHES_SKILL]->() RETURN count(r) as count")
            stats['teaches_skill'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:TAKES]->() RETURN count(r) as count")
            stats['takes'] = result.single()['count']
        
        return stats


import argparse

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='导入学生数据到Neo4j')
    parser.add_argument('--yes', '-y', action='store_true', 
                       help='自动确认导入操作')
    parser.add_argument('--file', '-f', default='students_data.json',
                       help='学生数据文件名')
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(base_dir, args.file)
    
    print("="*60)
    print("🎓 学生数据导入Neo4j")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 读取数据
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    students = data['students']
    domain_data = data['domain_data']
    
    print(f"📥 读取 {len(students)} 名学生, {len(domain_data)} 个专业")
    
    # 安全确认
    print("\n" + "="*60)
    print("⚠️  安全提醒")
    print("="*60)
    print("即将向Neo4j数据库写入学生数据！")
    print(f"\n将导入: {len(students)} 名学生, {len(domain_data)} 个专业")
    print("\n建议操作:")
    print("  1. 确认已备份Neo4j数据库")
    print(f"  2. 检查数据文件: {args.file}")
    print("  3. 确认数据库中已有Job数据")
    print("="*60)
    
    if not args.yes:
        response = input("\n是否继续导入? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ 用户取消操作")
            return
    else:
        print("✅ 使用自动确认模式")
    
    # 连接Neo4j
    importer = StudentGraphImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # 创建约束
        importer.create_constraints()
        
        # 导入专业-课程-技能
        importer.import_domain_data(domain_data)
        
        # 导入学生
        importer.import_students(students)
        
        # 统计
        print("\n" + "="*60)
        print("📊 导入完成 - 统计信息")
        print("="*60)
        
        stats = importer.get_statistics()
        
        print("\n🔵 节点统计:")
        print(f"   • 学生 (Student): {stats['students']}")
        print(f"   • 专业 (Major): {stats['majors']}")
        print(f"   • 课程 (Course): {stats['courses']}")
        print(f"   • 技能 (Skill): {stats['skills']}")
        
        print("\n🔗 新增关系:")
        print(f"   • 学生-专业 (MAJORS_IN): {stats['majors_in']}")
        print(f"   • 专业-课程 (HAS_COURSE): {stats['has_course']}")
        print(f"   • 课程-技能 (TEACHES_SKILL): {stats['teaches_skill']}")
        print(f"   • 学生-课程 (TAKES): {stats['takes']}")
        
        print("\n" + "="*60)
        print("✅ 学生数据导入完成！")
        print("💡 访问 http://localhost:7474 查看图谱")
        print("="*60)
        
    finally:
        importer.close()


if __name__ == '__main__':
    main()
