from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "TYH041113"

# 检查 Course 节点结构和专业关系
query = """
MATCH (c:Course)
RETURN c, keys(c) as props
LIMIT 3
"""

query2 = """
MATCH (c:Course)-[r]-()
RETURN type(r) as rel_type, count(*) as count
"""

try:
    with GraphDatabase.driver(URI, auth=(USER, PASSWORD)) as driver:
        with driver.session() as session:
            results = session.run(query).data()
            print(f"Course 节点示例:")
            for r in results:
                print(f"  属性: {r['props']}")
                for key, value in r['c'].items():
                    print(f"    {key}: {value}")
            
            results2 = session.run(query2).data()
            print(f"\nCourse 关系类型:")
            for r in results2:
                print(f"  {r['rel_type']}: {r['count']}")
except Exception as e:
    print(f"Error: {e}")
