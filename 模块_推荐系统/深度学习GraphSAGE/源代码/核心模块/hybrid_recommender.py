#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HybridRecommender: 三层漏斗式混合推荐系统
==========================================
Layer 1: 快速召回 (Recall) - 基于向量相似度
Layer 2: 精排序 (Ranking) - 基于深度学习模型  
Layer 3: 重排序 (Fusion) - 神经符号融合 + 可解释性

Author: Antigravity AI Agent
Date: 2026-01-13
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from neo4j import GraphDatabase
import warnings

# 尝试导入faiss，如果不可用则使用numpy替代
try:
    import faiss
    USE_FAISS = False  # 禁用 FAISS 以避免 ARM64 Mac 上的崩溃
except ImportError:
    USE_FAISS = False
    warnings.warn("faiss not installed, using numpy for similarity search (slower)")


@dataclass
class RecommendationResult:
    """单个推荐结果"""
    job_id: str
    final_score: float
    deep_score: float  # 深度学习得分
    skill_score: float  # 技能匹配得分
    rule_score: float  # 规则得分
    matched_skills: List[str]  # 匹配的技能
    explanation: str  # 推荐理由


class HybridRecommender:
    """
    三层漏斗式混合推荐器
    
    Attributes:
        node_embeddings: 节点嵌入字典 {id: tensor}
        link_predictor: 预训练的链路预测模型
        neo4j_driver: Neo4j数据库驱动
        job_mapping: Job索引到ID的映射
    """
    
    def __init__(
        self,
        node_embeddings: Dict[str, torch.Tensor],
        link_predictor: torch.nn.Module,
        neo4j_driver: Any,
        job_mapping: Dict[int, str],
        embedding_dim: int = 32
    ):
        """
        初始化混合推荐器
        
        Args:
            node_embeddings: 所有节点的嵌入向量
            link_predictor: 预训练的链路预测模型
            neo4j_driver: Neo4j驱动实例
            job_mapping: 索引到Job ID的映射
            embedding_dim: 嵌入向量维度
        """
        self.embeddings = node_embeddings
        self.predictor = link_predictor
        self.driver = neo4j_driver
        self.job_mapping = job_mapping
        self.embedding_dim = embedding_dim
        
        # 提取所有Job嵌入并构建索引
        self._build_job_index()
        
        # 设置模型为评估模式
        self.predictor.eval()
        
        print(f"✅ HybridRecommender 初始化完成")
        print(f"   Job数量: {len(self.job_mapping)}")
        print(f"   嵌入维度: {embedding_dim}")
        print(f"   使用FAISS: {USE_FAISS}")
    
    def _build_job_index(self):
        """构建Job向量索引用于快速检索"""
        # 收集所有Job的嵌入
        job_ids = sorted(self.job_mapping.keys())
        job_embeddings = []
        
        for idx in job_ids:
            job_id = self.job_mapping[idx]
            if job_id in self.embeddings:
                emb = self.embeddings[job_id]
            elif idx in self.embeddings:
                emb = self.embeddings[idx]
            else:
                # 使用随机向量作为fallback
                emb = torch.randn(self.embedding_dim)
            
            if isinstance(emb, torch.Tensor):
                emb = emb.detach().cpu().numpy()
            job_embeddings.append(emb)
        
        self.job_embeddings_np = np.array(job_embeddings, dtype=np.float32)
        self.job_indices = job_ids
        
        # 归一化用于余弦相似度
        norms = np.linalg.norm(self.job_embeddings_np, axis=1, keepdims=True)
        norms[norms == 0] = 1  # 防止除零
        self.job_embeddings_normalized = self.job_embeddings_np / norms
        
        if USE_FAISS:
            # 使用FAISS构建索引 (内积 = 余弦相似度，因为已归一化)
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.index.add(self.job_embeddings_normalized)
        else:
            self.index = None
    
    # ==================== Layer 1: 快速召回 ====================
    def recall(self, student_id: str, top_k: int = 500, skills: List[str] = None) -> List[int]:
        """
        Layer 1: 基于向量相似度的快速召回
        
        Args:
            student_id: 学生ID
            top_k: 召回数量
            skills: 用户技能列表（用于冷启动用户的嵌入生成）
            
        Returns:
            候选Job索引列表
        """
        # 获取学生嵌入（支持基于技能的回退生成）
        student_emb = self._get_student_embedding_with_skills(student_id, skills)
        
        if student_emb is None:
            # 真正的冷启动（无嵌入且无有效技能）
            print(f"⚠️  学生 {student_id} 无嵌入且无有效技能，使用冷启动策略")
            return self._cold_start_recall(student_id, top_k)
        
        # 归一化
        if isinstance(student_emb, torch.Tensor):
            student_emb = student_emb.detach().cpu().numpy()
        student_emb = student_emb.astype(np.float32).reshape(1, -1)
        norm = np.linalg.norm(student_emb)
        if norm > 0:
            student_emb = student_emb / norm
        
        if USE_FAISS and self.index is not None:
            # 使用FAISS进行检索
            scores, indices = self.index.search(student_emb, min(top_k, len(self.job_indices)))
            return [self.job_indices[i] for i in indices[0]]
        else:
            # 使用NumPy计算余弦相似度
            similarities = np.dot(self.job_embeddings_normalized, student_emb.T).flatten()
            top_indices = np.argsort(similarities)[::-1][:top_k]
            return [self.job_indices[i] for i in top_indices]
    
    def _get_student_embedding(self, student_id: str) -> Optional[np.ndarray]:
        """获取学生嵌入向量"""
        if student_id in self.embeddings:
            return self.embeddings[student_id]
        # 尝试数字索引
        try:
            idx = int(student_id.replace('STU', '').replace('TEST', ''))
            if idx in self.embeddings:
                return self.embeddings[idx]
        except:
            pass
        return None
    
    def _get_student_embedding_with_skills(self, student_id: str, skills: List[str] = None) -> Optional[torch.Tensor]:
        """
        获取学生嵌入向量，支持基于技能的回退生成
        
        对于不在训练数据中的用户，根据其技能嵌入的平均值生成临时用户画像
        
        Args:
            student_id: 学生ID
            skills: 用户掌握的技能列表
            
        Returns:
            学生嵌入向量，如果无法生成则返回 None
        """
        # 1. 优先使用缓存的嵌入（训练数据中的学生）
        emb = self._get_student_embedding(student_id)
        if emb is not None:
            if isinstance(emb, np.ndarray):
                return torch.from_numpy(emb).float()
            return emb
        
        # 2. 基于技能聚合生成临时嵌入（冷启动用户）
        if skills:
            try:
                skill_embs = []
                for sk in skills:
                    # 技能可能以不同格式存储
                    if sk in self.embeddings:
                        emb = self.embeddings[sk]
                        if isinstance(emb, torch.Tensor):
                            skill_embs.append(emb.detach().clone())
                        elif isinstance(emb, np.ndarray):
                            skill_embs.append(torch.from_numpy(emb.copy()).float())
                    elif f"skill_{sk}" in self.embeddings:
                        emb = self.embeddings[f"skill_{sk}"]
                        if isinstance(emb, torch.Tensor):
                            skill_embs.append(emb.detach().clone())
                        elif isinstance(emb, np.ndarray):
                            skill_embs.append(torch.from_numpy(emb.copy()).float())
                
                if skill_embs:
                    # 将技能嵌入堆叠并取平均
                    stacked = torch.stack(skill_embs)
                    avg_emb = torch.mean(stacked, dim=0)
                    print(f"🎯 为 {student_id} 基于 {len(skill_embs)} 个技能生成临时嵌入")
                    return avg_emb
            except Exception as e:
                print(f"⚠️ 技能嵌入生成失败: {e}")
        
        return None
    
    def _cold_start_recall(self, student_id: str, top_k: int) -> List[int]:
        """
        冷启动召回：基于专业的粗排
        TODO: 可以通过Neo4j查询学生专业，然后匹配相关职位
        """
        # 简单实现：返回随机职位
        indices = list(self.job_indices)
        np.random.shuffle(indices)
        return indices[:top_k]
    
    # ==================== Layer 2: 精排序 ====================
    def rank(
        self, 
        student_id: str, 
        candidate_jobs: List[int],
        student_emb: Optional[torch.Tensor] = None
    ) -> List[Tuple[int, float]]:
        """
        Layer 2: 基于深度学习模型的精排序
        
        Args:
            student_id: 学生ID
            candidate_jobs: 候选Job索引列表
            student_emb: 可选的学生嵌入（避免重复获取）
            
        Returns:
            (job_idx, score) 元组列表，按分数降序排列
        """
        if student_emb is None:
            student_emb = self._get_student_embedding(student_id)
            if student_emb is None:
                # 无嵌入时返回随机排序
                return [(idx, 0.5) for idx in candidate_jobs]
        
        if isinstance(student_emb, np.ndarray):
            student_emb = torch.from_numpy(student_emb).float()
        
        # 批量预测
        scores = []
        batch_size = 128
        
        with torch.no_grad():
            for i in range(0, len(candidate_jobs), batch_size):
                batch_jobs = candidate_jobs[i:i+batch_size]
                
                # 获取Job嵌入
                job_embs = []
                for job_idx in batch_jobs:
                    job_id = self.job_mapping.get(job_idx, str(job_idx))
                    if job_id in self.embeddings:
                        job_embs.append(self.embeddings[job_id])
                    elif job_idx < len(self.job_embeddings_np):
                        job_embs.append(torch.from_numpy(self.job_embeddings_np[job_idx]))
                    else:
                        job_embs.append(torch.zeros(self.embedding_dim))
                
                job_embs = torch.stack([e if isinstance(e, torch.Tensor) else torch.from_numpy(e) 
                                        for e in job_embs]).float()
                
                # 构建边索引 (student -> jobs)
                student_embs = student_emb.unsqueeze(0).expand(len(batch_jobs), -1)
                
                # 拼接特征并预测
                combined = torch.cat([student_embs, job_embs], dim=-1)
                
                # 使用predictor的线性层
                if hasattr(self.predictor, 'lin'):
                    batch_scores = torch.sigmoid(self.predictor.lin(combined)).squeeze()
                else:
                    # 简单的点积相似度
                    batch_scores = torch.sum(student_embs * job_embs, dim=-1)
                    batch_scores = torch.sigmoid(batch_scores)
                
                if batch_scores.dim() == 0:
                    batch_scores = batch_scores.unsqueeze(0)
                
                scores.extend(list(zip(batch_jobs, batch_scores.tolist())))
        
        # 按分数降序排列
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
    
    # ==================== Layer 3: 重排序与融合 ====================
    def fuse_and_explain(
        self,
        student_id: str,
        ranked_jobs: List[Tuple[int, float]],
        top_k: int = 50,
        weights: Tuple[float, float, float] = (0.6, 0.3, 0.1)
    ) -> List[RecommendationResult]:
        """
        Layer 3: 神经符号融合与可解释性生成
        
        Args:
            student_id: 学生ID
            ranked_jobs: Layer 2的排序结果
            top_k: 需要融合处理的数量
            weights: (deep_weight, skill_weight, rule_weight)
            
        Returns:
            最终推荐结果列表
        """
        w_deep, w_skill, w_rule = weights
        results = []
        
        # 只对Top-K进行Neo4j查询以减少压力
        for job_idx, deep_score in ranked_jobs[:top_k]:
            job_id = self.job_mapping.get(job_idx, str(job_idx))
            
            # 查询技能重叠
            skill_info = self._query_skill_overlap(student_id, job_id)
            overlap_count = skill_info.get('overlap_count', 0)
            required_count = skill_info.get('required_count', 1)  # 防止除零
            matched_skills = skill_info.get('matched_skills', [])
            
            # 计算技能得分
            if required_count > 0:
                skill_score = min(overlap_count / required_count, 1.0)
            else:
                skill_score = 0.0
            
            # 规则得分（学历匹配等）
            rule_score = self._calculate_rule_score(student_id, job_id)
            
            # 融合公式
            final_score = w_deep * deep_score + w_skill * skill_score + w_rule * rule_score
            
            # 生成解释
            explanation = self._generate_explanation(
                deep_score, skill_score, rule_score, matched_skills
            )
            
            results.append(RecommendationResult(
                job_id=job_id,
                final_score=final_score,
                deep_score=deep_score,
                skill_score=skill_score,
                rule_score=rule_score,
                matched_skills=matched_skills,
                explanation=explanation
            ))
        
        # 按最终得分重排序
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
    
    def _query_skill_overlap(self, student_id: str, job_id: str) -> Dict:
        """
        查询学生与职位的技能重叠
        
        包含两条路径：
        1. 直接技能：Student -[:HAS_SKILL]-> Skill
        2. 课程赋予：Student -[:TAKES]-> Course -[:TEACHES_SKILL]-> Skill
        """
        query = """
        // 路径1: 直接拥有的技能
        MATCH (s:Student {student_id: $stu_id})-[:HAS_SKILL]->(k:Skill)
              <-[:REQUIRES_SKILL]-(j:Job)
        WHERE j.url ENDS WITH $job_suffix
        WITH collect(DISTINCT k.name) as direct_skills
        
        // 路径2: 通过课程获得的技能
        OPTIONAL MATCH (s2:Student {student_id: $stu_id})-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(k2:Skill)
              <-[:REQUIRES_SKILL]-(j2:Job)
        WHERE j2.url ENDS WITH $job_suffix
        WITH direct_skills, collect(DISTINCT k2.name) as course_skills
        
        // 合并技能（去重）
        WITH direct_skills, course_skills, 
             [x IN direct_skills + course_skills WHERE x IS NOT NULL | x] AS all_skills_raw
        UNWIND all_skills_raw AS skill
        WITH direct_skills, course_skills, collect(DISTINCT skill) AS all_skills
        
        // 获取职位要求的技能总数
        OPTIONAL MATCH (j3:Job)-[:REQUIRES_SKILL]->(k3:Skill)
        WHERE j3.url ENDS WITH $job_suffix
        WITH direct_skills, course_skills, all_skills, count(DISTINCT k3) as required_count
        
        RETURN SIZE(all_skills) as overlap_count, 
               all_skills as matched_skills, 
               required_count,
               direct_skills,
               course_skills
        """
        
        # 提取job_id后缀用于匹配
        job_suffix = job_id if '/' not in job_id else job_id.split('/')[-1]
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    query, 
                    stu_id=student_id, 
                    job_suffix=job_suffix
                ).single()
                
                if result:
                    return {
                        'overlap_count': result['overlap_count'] or 0,
                        'matched_skills': result['matched_skills'] or [],
                        'required_count': result['required_count'] or 1,
                        'direct_skills': result['direct_skills'] or [],
                        'course_skills': result['course_skills'] or []
                    }
        except Exception as e:
            # 查询失败时返回默认值
            print(f"技能匹配查询失败: {e}")
            pass
        
        return {'overlap_count': 0, 'matched_skills': [], 'required_count': 1, 'direct_skills': [], 'course_skills': []}
    
    def _calculate_rule_score(self, student_id: str, job_id: str) -> float:
        """
        计算规则得分（学历匹配等）
        
        简化实现：查询学历是否匹配
        """
        query = """
        MATCH (s:Student {student_id: $stu_id})
        OPTIONAL MATCH (j:Job) WHERE j.url ENDS WITH $job_suffix
        RETURN s.education as stu_edu, j.education as job_edu
        """
        
        job_suffix = job_id if '/' not in job_id else job_id.split('/')[-1]
        
        try:
            with self.driver.session() as session:
                result = session.run(query, stu_id=student_id, job_suffix=job_suffix).single()
                
                if result:
                    stu_edu = result['stu_edu']
                    job_edu = result['job_edu']
                    
                    # 学历等级映射
                    edu_levels = {'大专': 1, '本科': 2, '硕士': 3, '博士': 4, '不限': 0}
                    
                    stu_level = edu_levels.get(stu_edu, 2)
                    job_level = edu_levels.get(job_edu, 0)
                    
                    # 如果学历满足要求，返回1.0
                    if job_level == 0 or stu_level >= job_level:
                        return 1.0
                    else:
                        return 0.5  # 学历不完全匹配
        except:
            pass
        
        return 1.0  # 默认匹配
    
    def _generate_explanation(
        self,
        deep_score: float,
        skill_score: float,
        rule_score: float,
        matched_skills: List[str]
    ) -> str:
        """生成推荐理由文案"""
        reasons = []
        
        # 技能匹配（优先显示）
        if matched_skills:
            if len(matched_skills) <= 3:
                skills_str = ", ".join(matched_skills)
            else:
                skills_str = ", ".join(matched_skills[:3]) + f" 等{len(matched_skills)}项"
            reasons.append(f"您掌握的 [{skills_str}] 技能与职位要求匹配")
        
        # 深度学习匹配度
        if deep_score >= 0.8:
            reasons.append("深度学习匹配度极高")
        elif deep_score >= 0.6:
            reasons.append("深度学习匹配度较高")
        
        # 学历匹配
        if rule_score >= 1.0:
            reasons.append("学历完全满足要求")
        
        if reasons:
            return "推荐理由：" + "，".join(reasons)
        else:
            return "推荐理由：综合评估适合"
    
    # ==================== 主推荐接口 ====================
    def recommend(
        self,
        student_id: str,
        recall_k: int = 500,
        rank_k: int = 50,
        final_k: int = 10,
        weights: Tuple[float, float, float] = (0.5, 0.35, 0.15),  # 调整：更重视技能匹配
        city: Optional[str] = None,
        skills: List[str] = None
    ) -> List[RecommendationResult]:
        """
        完整的三层漏斗推荐流程
        
        Args:
            student_id: 学生ID
            recall_k: Layer 1 召回数量
            rank_k: Layer 2->3 精排数量
            final_k: 最终返回数量
            weights: 融合权重 (deep, skill, rule)
            city: 城市过滤
            skills: 用户技能列表（用于冷启动用户的嵌入生成）
            
        Returns:
            最终推荐结果列表
        """
        print(f"\n{'='*50}")
        print(f"🎯 为 {student_id} 生成推荐")
        if skills:
            print(f"   用户技能: {skills[:5]}{'...' if len(skills) > 5 else ''}")
        print(f"{'='*50}")
        
        # Layer 1: 召回（传入技能用于冷启动嵌入生成）
        print(f"📥 Layer 1: 快速召回 (Top-{recall_k})...")
        candidates = self.recall(student_id, recall_k, skills)
        print(f"   召回候选: {len(candidates)} 个职位")

        # 城市过滤
        if city:
            print(f"🏙️  应用城市过滤: {city}")
            original_count = len(candidates)
            candidates = self._filter_by_city(candidates, city)
            print(f"   过滤后剩余: {len(candidates)} / {original_count}")
            
            if not candidates:
                print("⚠️  警告: 城市过滤后无候选职位")
                return []
        
        # Layer 2: 精排
        print(f"🔬 Layer 2: 深度学习精排...")
        ranked = self.rank(student_id, candidates)
        print(f"   精排完成: Top score = {ranked[0][1]:.4f}")
        
        # Layer 3: 融合
        print(f"🔗 Layer 3: 神经符号融合 (Top-{rank_k})...")
        results = self.fuse_and_explain(student_id, ranked, rank_k, weights)
        
        # 返回最终结果
        final_results = results[:final_k]
        print(f"✅ 推荐完成: 返回 {len(final_results)} 个结果")
        
        return final_results
    
    def recommend_pure_dl(
        self,
        student_id: str,
        top_k: int = 50,
        city: Optional[str] = None,
        skills: List[str] = None,
        expected_position: str = None,
        education: str = None,
        courses: List[str] = None
    ) -> List[RecommendationResult]:
        """
        纯深度学习推荐（AI推荐模式）
        
        使用 Layer 1（向量召回）+ Layer 2（深度学习精排）+ 规则加权（学历、期望职业）
        
        Args:
            student_id: 学生ID
            top_k: 返回数量
            city: 城市过滤
            skills: 用户直接技能列表
            expected_position: 期望职业
            education: 用户学历
            courses: 用户已修课程列表
            
        Returns:
            推荐结果列表
        """
        print(f"\n{'='*50}")
        print(f"🤖 AI推荐 (纯深度学习模式) - {student_id}")
        
        # 1. 合并直接技能 + 课程技能
        all_skills = list(skills) if skills else []
        if courses:
            course_skills = self._get_course_skills(courses)
            if course_skills:
                # 去重合并
                all_skills = list(set(all_skills + course_skills))
                print(f"   课程技能: 从 {len(courses)} 门课程获得 {len(course_skills)} 个技能")
        
        if all_skills:
            print(f"   总技能数: {len(all_skills)} (直接技能: {len(skills or [])}, 课程技能: {len(all_skills) - len(skills or [])})")
        if expected_position:
            print(f"   期望职业: {expected_position}")
        if education:
            print(f"   学历: {education}")
        print(f"{'='*50}")
        
        # Layer 1: 召回
        recall_k = min(500, len(self.job_indices))
        print(f"📥 Layer 1: 向量相似度召回 (Top-{recall_k})...")
        candidates = self.recall(student_id, recall_k, all_skills)
        print(f"   召回候选: {len(candidates)} 个职位")
        
        # 城市过滤
        if city:
            print(f"🏙️  应用城市过滤: {city}")
            original_count = len(candidates)
            candidates = self._filter_by_city(candidates, city)
            print(f"   过滤后剩余: {len(candidates)} / {original_count}")
            
            if not candidates:
                print("⚠️  警告: 城市过滤后无候选职位")
                return []
        
        # Layer 2: 精排 - 使用深度学习模型
        print(f"🔬 Layer 2: 深度学习精排...")
        ranked = self.rank(student_id, candidates)
        if ranked:
            print(f"   精排完成: Top score = {ranked[0][1]:.4f}")
        
        # Layer 2.5: 规则加权（学历匹配、期望职业匹配）
        print(f"📐 Layer 2.5: 规则加权...")
        weighted_results = []
        
        for job_idx, deep_score in ranked:
            job_id = self.job_mapping.get(job_idx, str(job_idx))
            
            # 查询职位信息
            job_info = self._get_job_info_for_matching(job_id)
            job_title = job_info.get('title', '')
            job_edu = job_info.get('education', '')
            
            # 学历加权（AI模式：降低强度，鼓励探索）
            edu_boost = 1.0
            if education and job_edu:
                edu_match = self._calculate_education_match(education, job_edu)
                if edu_match == 'perfect':  # 完全匹配
                    edu_boost = 1.3  # 原1.3
                elif edu_match == 'compatible':  # 兼容（学历>=要求 或 不限）
                    edu_boost = 1.1  # 原1.1
                else:  # 不匹配（学历<要求）
                    edu_boost = 0.7  # 原0.7，降低惩罚鼓励探索
            
            # 期望职业加权（AI模式：弱化锚定，探索新机会）
            position_boost = 1.0
            if expected_position and job_title:
                position_match = self._calculate_position_match(expected_position, job_title)
                if position_match >= 0.8:  # 高度匹配
                    position_boost = 1.4  # 原1.5
                elif position_match >= 0.5:  # 部分匹配
                    position_boost = 1.3  # 原1.2
                elif position_match >= 0.3:  # 轻微相关
                    position_boost = 1.1  # 原1.1
            
            # 计算加权得分
            final_score = deep_score * edu_boost * position_boost
            
            weighted_results.append({
                'job_idx': job_idx,
                'job_id': job_id,
                'deep_score': deep_score,
                'final_score': final_score,
                'edu_boost': edu_boost,
                'position_boost': position_boost,
                'job_title': job_title,
                'job_edu': job_edu
            })
        
        # 按加权后的分数重新排序
        weighted_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 构建最终结果
        results = []
        for item in weighted_results[:top_k]:
            job_id = item['job_id']
            
            # 查询匹配的技能
            skill_info = self._query_skill_overlap(student_id, job_id)
            matched_skills = skill_info.get('matched_skills', [])
            
            explanation = self._generate_dl_explanation_v2(
                item['deep_score'], 
                item['edu_boost'], 
                item['position_boost'],
                matched_skills,
                education,
                item['job_edu'],
                expected_position,
                item['job_title']
            )
            
            results.append(RecommendationResult(
                job_id=job_id,
                final_score=item['final_score'],
                deep_score=item['deep_score'],
                skill_score=item['position_boost'] - 1.0,  # 用于展示期望职业匹配度
                rule_score=item['edu_boost'] - 1.0,  # 用于展示学历匹配度
                matched_skills=matched_skills,
                explanation=explanation
            ))
        
        print(f"✅ AI推荐完成: 返回 {len(results)} 个结果")
        return results
    
    def _generate_dl_explanation(self, deep_score: float, matched_skills: List[str]) -> str:
        """生成AI推荐的解释文案"""
        reasons = []
        
        if deep_score >= 0.8:
            reasons.append("深度学习模型判断匹配度极高")
        elif deep_score >= 0.6:
            reasons.append("深度学习模型判断匹配度较高")
        elif deep_score >= 0.4:
            reasons.append("深度学习模型判断基本匹配")
        else:
            reasons.append("深度学习模型判断可能匹配")
        
        if matched_skills:
            if len(matched_skills) <= 3:
                skills_str = ", ".join(matched_skills)
            else:
                skills_str = ", ".join(matched_skills[:3]) + f" 等{len(matched_skills)}项"
            reasons.append(f"技能匹配: {skills_str}")
        
        return "AI推荐理由：" + "，".join(reasons)
    
    def _get_course_skills(self, courses: List[str]) -> List[str]:
        """从 Neo4j 查询课程所教授的技能"""
        if not courses or not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                # 尝试多种匹配方式
                query = """
                MATCH (c:Course)-[:TEACHES_SKILL]->(s:Skill)
                WHERE c.name IN $courses OR c.course_name IN $courses
                RETURN DISTINCT s.name as skill
                """
                result = session.run(query, courses=courses)
                skills = [record["skill"] for record in result if record["skill"]]
                return skills
        except Exception as e:
            print(f"⚠️ 查询课程技能失败: {e}")
            return []
    
    def _get_job_info_for_matching(self, job_id: str) -> dict:
        """获取职位的标题和学历要求"""
        if not self.driver:
            return {}
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (j:Job)
                WHERE j.url = $job_id OR j.url ENDS WITH $job_id
                RETURN j.title as title, j.education as education
                LIMIT 1
                """
                result = session.run(query, job_id=job_id)
                record = result.single()
                if record:
                    return {
                        'title': record['title'] or '',
                        'education': record['education'] or ''
                    }
        except Exception as e:
            print(f"⚠️ 查询职位信息失败: {e}")
        
        return {'title': '', 'education': ''}
    
    def _calculate_education_match(self, user_edu: str, job_edu: str) -> str:
        """计算学历匹配程度"""
        # 学历等级映射
        edu_levels = {
            '高中': 1, '中专': 1, '中技': 1,
            '大专': 2, '专科': 2,
            '本科': 3, '学士': 3,
            '硕士': 4, '研究生': 4,
            '博士': 5,
            '不限': 0, '无要求': 0, '': 0
        }
        
        user_level = edu_levels.get(user_edu, 3)  # 默认本科
        job_level = edu_levels.get(job_edu, 0)  # 默认不限
        
        if job_level == 0:  # 不限
            return 'compatible'
        elif user_level == job_level:  # 完全匹配
            return 'perfect'
        elif user_level >= job_level:  # 学历高于要求
            return 'compatible'
        else:  # 学历低于要求
            return 'mismatch'
    
    def _calculate_position_match(self, expected: str, job_title: str) -> float:
        """计算期望职业与职位标题的匹配度"""
        if not expected or not job_title:
            return 0.0
        
        expected = expected.lower()
        job_title = job_title.lower()
        
        # 完全包含
        if expected in job_title or job_title in expected:
            return 1.0
        
        # 关键词匹配
        # 定义职位关键词映射
        position_keywords = {
            '前端': ['前端', 'frontend', 'web', 'vue', 'react', 'javascript', 'js', 'css', 'html', 'h5'],
            '后端': ['后端', 'backend', 'java', 'python', 'go', 'golang', 'php', 'node', 'spring', 'django'],
            '全栈': ['全栈', 'fullstack', '全端'],
            '算法': ['算法', 'algorithm', 'ai', '人工智能', '机器学习', 'ml', 'deep learning', 'dl', '深度学习'],
            '数据': ['数据', 'data', '大数据', 'hadoop', 'spark', 'etl', '数仓', 'bi', '分析'],
            '测试': ['测试', 'test', 'qa', 'quality'],
            '运维': ['运维', 'devops', 'sre', 'ops', '云', 'cloud'],
            '产品': ['产品', 'product', 'pm'],
            '设计': ['设计', 'design', 'ui', 'ux', '交互'],
            'android': ['android', '安卓', 'kotlin'],
            'ios': ['ios', 'swift', 'objective-c', 'oc'],
            '嵌入式': ['嵌入式', 'embedded', '单片机', 'mcu', 'stm32', 'arm'],
            '游戏': ['游戏', 'game', 'unity', 'unreal', 'u3d', 'ue4'],
        }
        
        # 找到期望职业对应的关键词列表
        expected_keywords = []
        for category, keywords in position_keywords.items():
            if any(kw in expected for kw in keywords):
                expected_keywords.extend(keywords)
        
        if not expected_keywords:
            # 使用原始期望职业作为关键词
            expected_keywords = expected.split()
        
        # 计算匹配度
        match_count = sum(1 for kw in expected_keywords if kw in job_title)
        if match_count > 0:
            return min(match_count / len(expected_keywords), 1.0)
        
        return 0.0
    
    def _generate_dl_explanation_v2(
        self, 
        deep_score: float, 
        edu_boost: float, 
        position_boost: float,
        matched_skills: List[str],
        user_edu: str,
        job_edu: str,
        expected_position: str,
        job_title: str
    ) -> str:
        """生成 AI 推荐的详细解释"""
        reasons = []
        
        # 期望职业匹配说明
        if position_boost >= 1.5:
            reasons.append(f"职位与您的期望「{expected_position}」高度匹配")
        elif position_boost >= 1.2:
            reasons.append(f"职位与您的期望「{expected_position}」相关")
        
        # 学历匹配说明
        if edu_boost >= 1.3:
            reasons.append(f"学历完全匹配（{user_edu}）")
        elif edu_boost >= 1.1:
            reasons.append(f"学历符合要求")
        elif edu_boost < 1.0:
            reasons.append(f"学历可能不足（职位要求{job_edu}）")
        
        # 深度学习得分说明
        if deep_score >= 0.7:
            reasons.append("AI模型判断匹配度高")
        elif deep_score >= 0.5:
            reasons.append("AI模型判断基本匹配")
        
        # 技能匹配
        if matched_skills:
            if len(matched_skills) <= 3:
                skills_str = ", ".join(matched_skills)
            else:
                skills_str = ", ".join(matched_skills[:3]) + f" 等{len(matched_skills)}项"
            reasons.append(f"技能匹配: {skills_str}")
        
        return "AI推荐：" + "，".join(reasons) if reasons else "AI推荐"
    
    def close(self):
        """关闭资源"""
        if self.driver:
            self.driver.close()

    def _filter_by_city(self, job_indices: List[int], city: str) -> List[int]:
        """根据城市过滤职位候选"""
        valid_indices = []
        # 转换为ID列表
        job_ids = []
        idx_map = {} # job_id -> list of indices (in case of duplicates, though unlikely)
        
        for idx in job_indices:
            if idx in self.job_mapping:
                jid = self.job_mapping[idx]
                job_ids.append(jid)
                idx_map[jid] = idx
        
        if not job_ids:
            print("⚠️  _filter_by_city: job_ids is empty after mapping")
            return []

        print(f"DEBUG _filter_by_city: Filtering {len(job_ids)} jobs for city '{city}'")
        # Sample job IDs
        print(f"DEBUG _filter_by_city: Sample job_ids: {job_ids[:3]}")

        # 批量查询Neo4j - 检查公司位于该城市的职位
        query = """
        MATCH (j:Job)-[:OFFERED_BY]->(:Company)-[:LOCATED_IN]->(:City {name: $city})
        WHERE j.url IN $job_ids
        RETURN j.url AS job_id
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, city=city, job_ids=job_ids)
                valid_job_ids = {record["job_id"] for record in result}
                print(f"DEBUG _filter_by_city: Found {len(valid_job_ids)} valid jobs in {city}")
                
                if len(valid_job_ids) == 0:
                    print(f"⚠️ WARNING: No jobs found in {city}! Check if city name matches Neo4j data.")
                    # 检查城市是否存在
                    city_check = session.run("MATCH (c:City {name: $city}) RETURN c.name", city=city).single()
                    if city_check:
                        print(f"   City '{city}' exists in Neo4j")
                    else:
                        print(f"   ❌ City '{city}' does NOT exist in Neo4j!")
                
                # 转换回索引
                for jid in valid_job_ids:
                    if jid in idx_map:
                        valid_indices.append(idx_map[jid])
                        
        except Exception as e:
            print(f"❌ 城市过滤出错: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        print(f"DEBUG _filter_by_city: Returning {len(valid_indices)} valid indices")
        return valid_indices


# ==================== 便捷函数 ====================
def create_recommender_from_trained_model(
    model_path: str = '输出/模型权重/graphsage_model.pth',
    data_path: str = 'graph_data.pt',
    neo4j_uri: str = 'bolt://localhost:7687',
    neo4j_user: str = 'neo4j',
    neo4j_password: str = 'TYH041113'
) -> HybridRecommender:
    """
    从训练好的模型创建混合推荐器
    """
    from model import RecommenderModel
    
    # 加载数据
    print("📂 加载图数据...")
    data = torch.load(data_path, weights_only=False)
    
    # 加载模型
    print("🧠 加载模型权重...")
    model = RecommenderModel(data.metadata(), hidden_channels=64, out_channels=32)
    model.load_state_dict(torch.load(model_path, weights_only=True))
    model.eval()
    
    # 获取节点嵌入
    print("🔗 生成节点嵌入...")
    with torch.no_grad():
        x_dict = model.encoder(data.x_dict, data.edge_index_dict)
    
    # 构建嵌入字典
    node_embeddings = {}
    
    # Student嵌入
    student_map = data['student'].node_map
    for stu_id, idx in student_map.items():
        node_embeddings[stu_id] = x_dict['student'][idx]
    print(f"   Student嵌入: {len(student_map)} 个")
    
    # Job嵌入
    job_map = data['job'].node_map
    for job_id, idx in job_map.items():
        node_embeddings[job_id] = x_dict['job'][idx]
    print(f"   Job嵌入: {len(job_map)} 个")
    
    # 构建Job索引映射
    job_mapping = {idx: job_id for job_id, idx in job_map.items()}
    
    # 先连接Neo4j（用于查询技能列表）
    print("🔌 连接Neo4j...")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # Skill嵌入（关键：用于冷启动用户的嵌入生成）
    # 从 Neo4j 查询所有技能名称，按字母顺序与 data_loader 中的 skill_encoder 对应
    try:
        with driver.session() as session:
            result = session.run("MATCH (s:Skill) RETURN s.name AS name ORDER BY s.name")
            skill_names = [record["name"] for record in result]
        
        if 'skill' in x_dict and skill_names:
            skill_embs = x_dict['skill']
            # 加载能匹配到的技能嵌入（允许少量数量差异）
            loaded_count = 0
            for i, skill_name in enumerate(skill_names):
                if i < skill_embs.shape[0]:
                    node_embeddings[skill_name] = skill_embs[i]
                    loaded_count += 1
            print(f"   Skill嵌入: {loaded_count} 个 (Neo4j有{len(skill_names)}个)")
    except Exception as e:
        print(f"   ⚠️ Skill嵌入加载失败: {e}")
    
    # 创建推荐器
    recommender = HybridRecommender(
        node_embeddings=node_embeddings,
        link_predictor=model.predictor,
        neo4j_driver=driver,
        job_mapping=job_mapping,
        embedding_dim=32
    )
    
    return recommender


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("="*60)
    print("🚀 三层漏斗式混合推荐系统测试")
    print("="*60)
    
    # 创建推荐器
    recommender = create_recommender_from_trained_model()
    
    # 测试推荐
    test_students = ['STU0001', 'STU0010', 'STU0050']
    
    for stu_id in test_students:
        results = recommender.recommend(stu_id, recall_k=500, rank_k=50, final_k=5)
        
        print(f"\n📋 {stu_id} 推荐结果:")
        print("-" * 60)
        for i, rec in enumerate(results, 1):
            print(f"\n  {i}. {rec.job_id[-25:]}")
            print(f"     最终得分: {rec.final_score:.4f}")
            print(f"     深度学习: {rec.deep_score:.4f} | 技能匹配: {rec.skill_score:.4f} | 规则: {rec.rule_score:.4f}")
            print(f"     {rec.explanation}")
    
    recommender.close()
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)
