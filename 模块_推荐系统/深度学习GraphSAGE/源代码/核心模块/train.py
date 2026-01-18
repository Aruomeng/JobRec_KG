import sys
print("🚀 Script starting...", flush=True)
import torch
import torch.nn.functional as F
from tqdm import tqdm
import os
import numpy as np

# 导入自定义模块
try:
    from data_loader import GraphDataLoader
    from model import RecommenderModel
except ImportError as e:
    print(f"❌ 无法导入模块: {e}", flush=True)
    exit(1)

def train():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"🚀 使用设备: {device}", flush=True)

    # 1. 加载数据
    data_path = 'graph_data.pt'
    if os.path.exists(data_path):
        print(f"📂 加载缓存数据: {data_path}", flush=True)
        data = torch.load(data_path, weights_only=False)
    else:
        print("🔄 构建新数据...", flush=True)
        loader = GraphDataLoader()
        try:
            data = loader.load_data()
            torch.save(data, data_path)
        finally:
            loader.close()
            
    data = data.to(device)
    
    # 2. 初始化模型
    model = RecommenderModel(data.metadata(), hidden_channels=64, out_channels=32).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    if ('student', 'applies', 'job') not in data.edge_index_dict:
        print("❌ 错误: 图数据中缺少 'applies' 边，无法训练。", flush=True)
        return

    edge_index = data['student', 'applies', 'job'].edge_index
    print(f"📈 训练样本数: {edge_index.size(1)}", flush=True)
    
    # 检查数据质量
    for k, v in data.x_dict.items():
        if torch.isnan(v).any():
            print(f"❌ Node feature '{k}' has NaN!", flush=True)
        else:
            print(f"✅ Node feature '{k}' OK.", flush=True)
    
    # 3. 训练循环
    print("\nStarting Training...", flush=True)
    model.train()
    
    for epoch in range(1, 201):
        optimizer.zero_grad()
        
        src, pos_dst = edge_index
        num_nodes = data['job'].num_nodes
        neg_dst = torch.randint(0, num_nodes, (src.size(0),), device=device)
        
        pos_edge_label_index = edge_index
        neg_edge_label_index = torch.stack([src, neg_dst], dim=0)
        edge_label_index = torch.cat([pos_edge_label_index, neg_edge_label_index], dim=1)
        
        pos_label = torch.ones(pos_edge_label_index.size(1), device=device)
        neg_label = torch.zeros(neg_edge_label_index.size(1), device=device)
        target = torch.cat([pos_label, neg_label])
        
        pred = model(data.x_dict, data.edge_index_dict, edge_label_index).squeeze()
        
        loss = F.binary_cross_entropy_with_logits(pred, target)
        loss.backward()
        optimizer.step()
        
        if epoch % 5 == 0:
            with torch.no_grad():
                from sklearn.metrics import roc_auc_score
                prob = pred.sigmoid().cpu().numpy()
                label = target.cpu().numpy()
                try:
                    auc = roc_auc_score(label, prob)
                    print(f"Epoch: {epoch:03d}, Loss: {loss:.4f}, Train AUC: {auc:.4f}", flush=True)
                except:
                    print(f"Epoch: {epoch:03d}, Loss: {loss:.4f}", flush=True)

    os.makedirs('输出/模型权重', exist_ok=True)
    save_path = '输出/模型权重/graphsage_model.pth'
    torch.save(model.state_dict(), save_path)
    print(f"\n✅ 模型已保存到: {save_path}", flush=True)

if __name__ == "__main__":
    train()
