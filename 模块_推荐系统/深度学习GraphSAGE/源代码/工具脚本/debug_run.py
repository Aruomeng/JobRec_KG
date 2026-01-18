
import sys
print("Debug start", flush=True)
try:
    import torch
    print("Torch imported", flush=True)
    from data_loader import GraphDataLoader
    print("Loader imported", flush=True)
    loader = GraphDataLoader()
    print("Loader init", flush=True)
    # Don't load data, just connect
    with loader.driver.session() as session:
        print("Session created", flush=True)
        res = session.run("RETURN 1")
        print(f"Neo4j check: {res.single()[0]}", flush=True)
    loader.close()
    print("Debug end", flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
