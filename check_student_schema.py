from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "TYH041113"

# 检查 Student 节点结构
query = """
MATCH (s:Student)
RETURN s, keys(s) as props
LIMIT 5
"""

try:
    with GraphDatabase.driver(URI, auth=(USER, PASSWORD)) as driver:
        with driver.session() as session:
            results = session.run(query).data()
            print(f"Student 节点示例 (前5个):")
            for r in results:
                print(f"\n属性列表: {r['props']}")
                for key, value in r['s'].items():
                    print(f"  {key}: {value}")
except Exception as e:
    print(f"Error: {e}")
