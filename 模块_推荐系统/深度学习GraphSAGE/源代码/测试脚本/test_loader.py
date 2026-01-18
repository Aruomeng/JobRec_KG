from data_loader import GraphDataLoader
print("Testing DataLoader...")
loader = GraphDataLoader()
try:
    data = loader.load_data()
    print("Data loaded successfully!")
    print(data)
except Exception as e:
    print(f"Error: {e}")
finally:
    loader.close()
