from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "TYH041113"

# 检查用户 18162572004 的数据
query = """
MATCH (s:Student)
WHERE s.name = '18162572004' OR s.username = '18162572004' OR s.student_id = '18162572004'
RETURN s
"""

try:
    with GraphDatabase.driver(URI, auth=(USER, PASSWORD)) as driver:
        with driver.session() as session:
            result = session.run(query).single()
            if result:
                student = result['s']
                print(f"找到用户:")
                for key, value in student.items():
                    print(f"  {key}: {value}")
            else:
                print("未找到用户 18162572004")
except Exception as e:
    print(f"Error: {e}")
