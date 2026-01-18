#!/usr/bin/env python3
"""
验证职位知识图谱结构
"""

from neo4j import GraphDatabase

# Neo4j连接信息
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "TYH041113"

class GraphVerifier:
    """知识图谱验证器"""

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✅ 已连接到Neo4j: {uri}")

    def close(self):
        self.driver.close()

    def get_node_counts(self):
        """获取各类型节点的数量"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n) AS labels, COUNT(n) AS count
                ORDER BY count DESC
            """)
            return [
                {"labels": record["labels"], "count": record["count"]}
                for record in result
            ]

    def get_relationship_counts(self):
        """获取各类型关系的数量"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS type, COUNT(r) AS count
                ORDER BY count DESC
            """)
            return [
                {"type": record["type"], "count": record["count"]}
                for record in result
            ]

    def get_sample_nodes(self, label, limit=5):
        """获取指定类型的样本节点"""
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (n:{label})
                RETURN n
                LIMIT {limit}
            """)
            return [record["n"] for record in result]

    def verify_graph_structure(self):
        """验证图谱结构是否正确"""
        print("="*60)
        print("🔍 验证知识图谱结构")
        print("="*60)

        # 检查节点类型
        print("\n📊 节点类型统计:")
        node_counts = self.get_node_counts()
        if not node_counts:
            print("❌ 数据库中没有节点")
            return False

        for item in node_counts:
            labels = ", ".join(item["labels"])
            print(f"  {labels}: {item['count']:,} 个")

        # 检查关系类型
        print("\n🔗 关系类型统计:")
        rel_counts = self.get_relationship_counts()
        if not rel_counts:
            print("❌ 数据库中没有关系")
            return False

        for item in rel_counts:
            print(f"  {item['type']}: {item['count']:,} 条")

        # 检查核心节点是否存在
        required_nodes = ["Job", "Company", "Skill", "Industry", "City"]
        all_nodes_exist = True

        print("\n🔍 核心节点验证:")
        for node_type in required_nodes:
            count = next((item["count"] for item in node_counts 
                         if node_type in item["labels"]), 0)
            if count > 0:
                print(f"  ✅ {node_type}: {count:,} 个")
            else:
                print(f"  ❌ {node_type}: 不存在")
                all_nodes_exist = False

        # 检查核心关系是否存在
        required_relationships = ["OFFERED_BY", "REQUIRES_SKILL", 
                                 "BELONGS_TO_INDUSTRY", "LOCATED_IN"]
        all_relationships_exist = True

        print("\n🔗 核心关系验证:")
        for rel_type in required_relationships:
            count = next((item["count"] for item in rel_counts 
                         if item["type"] == rel_type), 0)
            if count > 0:
                print(f"  ✅ {rel_type}: {count:,} 条")
            else:
                print(f"  ❌ {rel_type}: 不存在")
                all_relationships_exist = False

        # 显示样本数据
        print("\n📋 样本数据:")
        for node_type in required_nodes[:3]:  # 只显示前3种节点的样本
            samples = self.get_sample_nodes(node_type, limit=2)
            if samples:
                print(f"\n  {node_type} 样本:")
                for i, sample in enumerate(samples):
                    print(f"    {i+1}. {sample}")

        # 验证结果
        print("\n" + "="*60)
        if all_nodes_exist and all_relationships_exist:
            print("✅ 知识图谱结构验证成功！")
            return True
        else:
            print("❌ 知识图谱结构验证失败！")
            return False

def main():
    verifier = GraphVerifier(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        verifier.verify_graph_structure()
    finally:
        verifier.close()

if __name__ == "__main__":
    main()
