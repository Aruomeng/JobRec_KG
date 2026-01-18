from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "TYH041113"

# 用户账号
STUDENT_ID = "STU0501"

def test_user_data():
    with GraphDatabase.driver(URI, auth=(USER, PASSWORD)) as driver:
        with driver.session() as session:
            # 1. 检查用户基本信息
            print("=" * 60)
            print("1. 用户基本信息")
            result = session.run("""
                MATCH (s:Student {student_id: $stu_id})
                RETURN s
            """, stu_id=STUDENT_ID).single()
            
            if result:
                for key, value in result['s'].items():
                    print(f"   {key}: {value}")
            else:
                print("   用户不存在!")
                return
            
            # 2. 检查用户直接技能 (HAS_SKILL)
            print("\n" + "=" * 60)
            print("2. 用户直接技能 (HAS_SKILL)")
            skills = session.run("""
                MATCH (s:Student {student_id: $stu_id})-[:HAS_SKILL]->(sk:Skill)
                RETURN sk.name as skill
            """, stu_id=STUDENT_ID).data()
            
            if skills:
                for s in skills:
                    print(f"   - {s['skill']}")
            else:
                print("   无直接技能")
            
            # 3. 检查用户选择的课程 (TAKES)
            print("\n" + "=" * 60)
            print("3. 用户选择的课程 (TAKES)")
            courses = session.run("""
                MATCH (s:Student {student_id: $stu_id})-[:TAKES]->(c:Course)
                RETURN c.name as course
            """, stu_id=STUDENT_ID).data()
            
            if courses:
                for c in courses:
                    print(f"   - {c['course']}")
            else:
                print("   无已选课程 - 这就是为什么没有课程赋能!")
            
            # 4. 检查课程关联的技能 (TEACHES_SKILL)
            print("\n" + "=" * 60)
            print("4. 课程->技能 关系示例")
            course_skills = session.run("""
                MATCH (c:Course)-[:TEACHES_SKILL]->(sk:Skill)
                RETURN c.name as course, collect(sk.name) as skills
                LIMIT 5
            """).data()
            
            for cs in course_skills:
                print(f"   {cs['course']}: {cs['skills']}")
            
            # 5. 检查一个职位的技能要求
            print("\n" + "=" * 60)
            print("5. 示例职位的技能要求")
            job_skills = session.run("""
                MATCH (j:Job)-[:REQUIRES_SKILL]->(sk:Skill)
                WHERE j.title CONTAINS 'Java' OR j.title CONTAINS 'Python'
                RETURN j.title as title, j.url as url, collect(sk.name) as skills
                LIMIT 3
            """).data()
            
            for js in job_skills:
                print(f"   {js['title'][:40]}...")
                print(f"      技能: {js['skills']}")
                print(f"      URL: {js['url']}")

if __name__ == "__main__":
    test_user_data()
