import torch
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, HeteroConv

class JobRecGraphSAGE(torch.nn.Module):
    def __init__(self, hidden_channels, out_channels, metadata):
        super().__init__()
        
        # 使用 HeteroConv 显式定义异构图卷积
        # 对每种边类型应用 SAGEConv
        # (-1, -1) 表示源节点和目标节点的特征维度自适应
        self.conv1 = HeteroConv({
            edge_type: SAGEConv((-1, -1), hidden_channels)
            for edge_type in metadata[1]
        }, aggr='sum')
        
        self.conv2 = HeteroConv({
            edge_type: SAGEConv((-1, -1), out_channels)
            for edge_type in metadata[1]
        }, aggr='sum')

    def forward(self, x_dict, edge_index_dict):
        # 第一层卷积
        x_dict = self.conv1(x_dict, edge_index_dict)
        x_dict = {key: F.relu(x) for key, x in x_dict.items()}
        
        # 第二层卷积
        x_dict = self.conv2(x_dict, edge_index_dict)
        
        return x_dict

class LinkPredictor(torch.nn.Module):
    def __init__(self, in_channels):
        super().__init__()
        # 简单的线性预测器
        self.lin = torch.nn.Linear(in_channels * 2, 1)

    def forward(self, x_student, x_job, edge_label_index):
        # 获取源节点(Student)和目标节点(Job)的Embedding
        row, col = edge_label_index
        edge_feat_student = x_student[row]
        edge_feat_job = x_job[col]
        
        # 拼接特征并预测
        x = torch.cat([edge_feat_student, edge_feat_job], dim=-1)
        return self.lin(x)

class RecommenderModel(torch.nn.Module):
    def __init__(self, metadata, hidden_channels=64, out_channels=32):
        super().__init__()
        self.encoder = JobRecGraphSAGE(hidden_channels, out_channels, metadata)
        self.predictor = LinkPredictor(out_channels)
        
    def forward(self, x_dict, edge_index_dict, edge_label_index):
        # 1. 编码：获取所有节点的Embedding
        x_dict = self.encoder(x_dict, edge_index_dict)
        
        # 2. 预测：计算指定边的分数
        pred = self.predictor(
            x_dict['student'], 
            x_dict['job'], 
            edge_label_index
        )
        return pred
