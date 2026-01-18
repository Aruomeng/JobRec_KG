import torch
import os
import json
import numpy as np

try:
    from data_loader import GraphDataLoader
    from model import RecommenderModel
except ImportError:
    exit(1)

def recommend(student_id_str, top_k=5):
    # 1. 加载数据
    data_path = 'graph_data.pt'
    if not os.path.exists(data_path):
        print("未找到数据文件，请先运行 train.py")
        return
        
    data = torch.load(data_path, weights_only=False)
    model_path = '输出/模型权重/graphsage_model.pth'
    
    # 2. 加载模型
    model = RecommenderModel(data.metadata(), hidden_channels=64, out_channels=32)
    model.load_state_dict(torch.load(model_path))
    model.eval()
    
    # 3. 查找学生ID
    if student_id_str not in data['student'].node_map:
        print(f"❌ 找不到学生: {student_id_str}")
        return
        
    s_idx = data['student'].node_map[student_id_str]
    num_jobs = data['job'].num_nodes
    
    # 4. 预测所有职位的分数
    # 构造 (Student, All_Jobs) 边
    print(f"🔍 正在为 {student_id_str} 计算 {num_jobs} 个职位的推荐分数...")
    
    with torch.no_grad():
        # 获取所有节点的 Embedding
        # 注意：这里我们传入整个图结构进行编码
        x_dict = model.encoder(data.x_dict, data.edge_index_dict)
        student_emb = x_dict['student'][s_idx] # [32]
        job_embs = x_dict['job']                # [num_jobs, 32]
        
        # 计算相似度 (点积)
        # (1, 32) * (32, num_jobs) -> (1, num_jobs)
        # 但model是拼接的，所以我们手动构建batch预测
        # 为简单起见，我们直接用点积模拟 LinkPredictor 的行为 (若 LinkPredictor 是简单线性层)
        # 这里为了准确，我们还是调用 predictor
        
        # 批量预测 (分批处理防止内存溢出)
        batch_size = 1000
        scores = []
        for i in range(0, num_jobs, batch_size):
            end = min(i + batch_size, num_jobs)
            batch_job_indices = torch.arange(i, end)
            batch_src = torch.full((len(batch_job_indices),), s_idx, dtype=torch.long)
            
            batch_edge_index = torch.stack([batch_src, batch_job_indices], dim=0)
            
            # 使用编码后的特征进行预测
            batch_pred = model.predictor(x_dict['student'], x_dict['job'], batch_edge_index)
            scores.append(batch_pred.squeeze())
            
        all_scores = torch.cat(scores)
        
    # 5. 获取 Top-K
    top_scores, top_indices = torch.topk(all_scores, top_k)
    
    # 6. 解析结果 (反向查Job信息)
    # 反转 job map
    job_id_map = {v: k for k, v in data['job'].node_map.items()}
    
    # 加载原始职位信息（这一步在实际系统中是从DB查）
    # 这里我们只打印ID和分数
    print(f"\n✅ 推荐结果 (Top {top_k}):")
    print("-" * 50)
    for score, idx in zip(top_scores, top_indices):
        job_url = job_id_map[idx.item()]
        print(f"🔗 职位ID: {job_url[-20:]} | 得分: {score.item():.4f}")
    print("-" * 50)

if __name__ == "__main__":
    # 测试生成的第一个学生
    recommend("STU0001")
    # 测试生成的第二个学生
    recommend("STU0002")
