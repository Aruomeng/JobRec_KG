#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
职位数据进阶清洗脚本
====================
功能：
1. 去重 - 检测并删除重复职位（职位+公司+工作描述完全重复）
2. 薪资标准化 - 将"面议"转为null，统一薪资格式
3. 文本清理 - 去除工作描述中的特殊字符
4. 数据增强 - 提取薪资范围的最小值/最大值

作者：AI Assistant
日期：2026-01-12
"""

import os
import re
import pandas as pd
from datetime import datetime
import logging

# ==================== 配置 ====================
# 输入目录（第一次清洗后的数据）
INPUT_BASE_DIR = '第一次清洗'

# 输出目录
OUTPUT_BASE_DIR = '第二次清洗_进阶'

# 城市目录列表
CITY_DIRS = [
    'data_beijing_cleaned',
    'data_chengdu_cleaned',
    'data_chongqing_cleaned',
    'data_hangzhou_cleaned',
    'data_nanjin_cleaned',
    'data_shenzhen_cleaned',
    'data_wuhan_cleaned',
    'data_xiamen_cleaned',
    'data_zhengzhou_cleaned'
]

# 用于去重判断的字段
DEDUP_FIELDS = ['职位', '公司', '工作描述']

# ==================== 日志配置 ====================
def setup_logger(log_file, city_name):
    """配置日志记录器"""
    logger = logging.getLogger(f'AdvancedCleaner_{city_name}')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# ==================== 薪资处理函数 ====================
def parse_salary(salary_str):
    """
    解析薪资字符串，提取最小值和最大值（单位：元/月）
    
    支持格式:
    - "4-7万" -> (40000, 70000)
    - "3-5万·15薪" -> (30000, 50000)  # 月薪基础值
    - "2.5-4.5万·14薪" -> (25000, 45000)
    - "1.5-3万" -> (15000, 30000)
    - "面议" -> (None, None)
    - "20-99人" -> 这不是薪资，返回None
    
    返回:
        (min_salary, max_salary, annual_months): 最小月薪、最大月薪、年薪月数
    """
    if pd.isna(salary_str) or not isinstance(salary_str, str):
        return None, None, None
    
    salary_str = salary_str.strip()
    
    # 面议情况
    if salary_str == '面议' or salary_str == '':
        return None, None, None
    
    # 提取年薪月数 (如 15薪, 14薪, 16薪)
    annual_months = 12  # 默认12个月
    months_match = re.search(r'(\d+)薪', salary_str)
    if months_match:
        annual_months = int(months_match.group(1))
    
    # 匹配薪资范围: 数字-数字万 或 数字-数字千
    # 格式1: X-Y万 (如 4-7万, 2.5-4.5万)
    pattern_wan = r'([\d.]+)[-~]([\d.]+)\s*万'
    match_wan = re.search(pattern_wan, salary_str)
    
    if match_wan:
        try:
            min_val = float(match_wan.group(1)) * 10000
            max_val = float(match_wan.group(2)) * 10000
            return int(min_val), int(max_val), annual_months
        except ValueError:
            pass
    
    # 格式2: X-Yk (如 15-30k)
    pattern_k = r'([\d.]+)[-~]([\d.]+)\s*[kK]'
    match_k = re.search(pattern_k, salary_str)
    
    if match_k:
        try:
            min_val = float(match_k.group(1)) * 1000
            max_val = float(match_k.group(2)) * 1000
            return int(min_val), int(max_val), annual_months
        except ValueError:
            pass
    
    # 无法解析
    return None, None, None


def standardize_salary(salary_str):
    """
    标准化薪资字符串为数值格式
    - "面议" -> None
    - "4-7万" -> "40000-70000"
    - "4-7万·15薪" -> "40000-70000"
    - "2.5-4.5万" -> "25000-45000"
    - "15-30k" -> "15000-30000"
    """
    if pd.isna(salary_str) or not isinstance(salary_str, str):
        return None
    
    salary_str = salary_str.strip()
    
    if salary_str == '面议' or salary_str == '':
        return None
    
    # 格式1: X-Y万 (如 4-7万, 2.5-4.5万, 4-7万·15薪)
    pattern_wan = r'([\d.]+)[-~]([\d.]+)\s*万'
    match_wan = re.search(pattern_wan, salary_str)
    
    if match_wan:
        try:
            min_val = int(float(match_wan.group(1)) * 10000)
            max_val = int(float(match_wan.group(2)) * 10000)
            return f"{min_val}-{max_val}"
        except ValueError:
            pass
    
    # 格式2: X-Yk (如 15-30k)
    pattern_k = r'([\d.]+)[-~]([\d.]+)\s*[kK]'
    match_k = re.search(pattern_k, salary_str)
    
    if match_k:
        try:
            min_val = int(float(match_k.group(1)) * 1000)
            max_val = int(float(match_k.group(2)) * 1000)
            return f"{min_val}-{max_val}"
        except ValueError:
            pass
    
    # 无法解析的格式，返回None
    return None


# ==================== 文本清理函数 ====================
def clean_text(text):
    """
    清理文本中的特殊字符
    
    处理：
    - 去除不可见字符
    - 去除多余空白
    - 去除特殊控制字符
    """
    if pd.isna(text) or not isinstance(text, str):
        return text
    
    # 去除常见特殊字符和控制字符
    # 保留中文、英文、数字、常用标点
    cleaned = text
    
    # 替换特殊空白字符为普通空格
    cleaned = re.sub(r'[\u00a0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u3000]', ' ', cleaned)
    
    # 去除控制字符（保留换行和制表符）
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
    
    # 多个空格合并为一个
    cleaned = re.sub(r' +', ' ', cleaned)
    
    # 去除首尾空白
    cleaned = cleaned.strip()
    
    return cleaned

# ==================== 核心清洗函数 ====================
def advanced_clean_dataframe(df, logger):
    """
    进阶清洗DataFrame
    
    返回:
        (cleaned_df, stats): 清洗后的DataFrame和统计信息
    """
    stats = {
        'original_count': len(df),
        'duplicates_removed': 0,
        'salary_standardized': 0,
        'salary_negotiable': 0,  # 面议的数量
        'text_cleaned': 0,
        'salary_parsed': 0,
        'final_count': 0
    }
    
    logger.info(f"开始进阶清洗，原始记录数: {len(df)}")
    
    # ===== 1. 去重 =====
    logger.info("步骤1: 检测重复记录...")
    
    # 创建去重标识列
    df['_dedup_key'] = df[DEDUP_FIELDS].apply(
        lambda x: '|||'.join(str(v).strip() for v in x), axis=1
    )
    
    # 标记重复行（保留第一个）
    duplicates_mask = df.duplicated(subset=['_dedup_key'], keep='first')
    duplicate_count = duplicates_mask.sum()
    stats['duplicates_removed'] = duplicate_count
    
    if duplicate_count > 0:
        # 记录被删除的重复记录
        duplicate_rows = df[duplicates_mask]
        for idx, row in duplicate_rows.head(10).iterrows():  # 只记录前10条
            logger.warning(f"删除重复: [{row['职位']}]@[{row['公司']}]")
        if duplicate_count > 10:
            logger.warning(f"... 还有 {duplicate_count - 10} 条重复记录被删除")
        
        df = df[~duplicates_mask].copy()
        logger.info(f"去重完成，删除 {duplicate_count} 条重复记录")
    else:
        logger.info("未发现重复记录")
    
    # 删除临时列
    df = df.drop(columns=['_dedup_key'])
    
    # ===== 2. 薪资处理（先解析原始值，再标准化） =====
    logger.info("步骤2: 薪资处理...")
    
    if '薪资' in df.columns:
        # 保存原始薪资用于解析
        original_salary = df['薪资'].copy()
        
        # 统计面议数量
        negotiable_mask = original_salary.apply(
            lambda x: x == '面议' if isinstance(x, str) else False
        )
        stats['salary_negotiable'] = negotiable_mask.sum()
        
        # 先从原始薪资解析数值（最小值/最大值/年薪月数）
        salary_info = original_salary.apply(parse_salary)
        
        df['薪资_最小值'] = salary_info.apply(lambda x: x[0] if x else None)
        df['薪资_最大值'] = salary_info.apply(lambda x: x[1] if x else None)
        df['年薪月数'] = salary_info.apply(lambda x: x[2] if x else None)
        
        # 统计成功解析的数量
        parsed_count = df['薪资_最小值'].notna().sum()
        stats['salary_parsed'] = parsed_count
        
        # 再标准化薪资列（将"4-7万"转为"40000-70000"，"面议"转为None）
        df['薪资'] = original_salary.apply(standardize_salary)
        stats['salary_standardized'] = len(df)
        
        logger.info(f"薪资处理完成：解析成功 {parsed_count} 条，'面议' {stats['salary_negotiable']} 条")
    
    # ===== 3. 文本清理 =====
    logger.info("步骤3: 清理文本特殊字符...")
    
    text_columns = ['职位', '公司', '工作描述', '技能']
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)
    
    stats['text_cleaned'] = len(df)
    logger.info("文本清理完成")
    
    stats['final_count'] = len(df)
    
    return df, stats


def process_city(base_dir, input_city_dir, output_city_dir, timestamp, logger):
    """处理单个城市的数据"""
    
    city_name = input_city_dir.replace('data_', '').replace('_cleaned', '').upper()
    
    input_dir = os.path.join(base_dir, INPUT_BASE_DIR, input_city_dir)
    output_dir = os.path.join(base_dir, OUTPUT_BASE_DIR, output_city_dir)
    
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("="*60)
    logger.info(f"处理城市: {city_name}")
    logger.info("="*60)
    
    # 获取所有CSV文件（排除logs目录）
    csv_files = [f for f in os.listdir(input_dir) 
                 if f.endswith('.csv') and not f.startswith('.')]
    
    if not csv_files:
        logger.warning(f"城市 {city_name} 未找到CSV文件!")
        return None
    
    logger.info(f"找到 {len(csv_files)} 个CSV文件")
    
    city_stats = {
        'city': city_name,
        'files': len(csv_files),
        'original': 0,
        'final': 0,
        'duplicates': 0,
        'negotiable': 0,
        'salary_parsed': 0
    }
    
    for csv_file in sorted(csv_files):
        input_path = os.path.join(input_dir, csv_file)
        output_filename = csv_file.replace('_cleaned.csv', '_advanced.csv')
        output_path = os.path.join(output_dir, output_filename)
        
        logger.info(f"\n处理文件: {csv_file}")
        
        try:
            df = pd.read_csv(input_path, encoding='utf-8')
            cleaned_df, stats = advanced_clean_dataframe(df, logger)
            
            # 保存清洗后的数据
            cleaned_df.to_csv(output_path, index=False, encoding='utf-8')
            
            # 累计统计
            city_stats['original'] += stats['original_count']
            city_stats['final'] += stats['final_count']
            city_stats['duplicates'] += stats['duplicates_removed']
            city_stats['negotiable'] += stats['salary_negotiable']
            city_stats['salary_parsed'] += stats['salary_parsed']
            
            logger.info(f"保存至: {output_filename}")
            
        except Exception as e:
            logger.error(f"处理文件 {csv_file} 失败: {str(e)}")
            continue
    
    return city_stats


def main():
    """主函数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 创建输出目录
    output_base = os.path.join(base_dir, OUTPUT_BASE_DIR)
    log_dir = os.path.join(output_base, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 设置全局日志
    log_file = os.path.join(log_dir, f'advanced_cleaning_{timestamp}.log')
    logger = setup_logger(log_file, 'GLOBAL')
    
    print("\n" + "="*60)
    print("🚀 职位数据进阶清洗程序启动")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("\n🔧 清洗内容:")
    print("   1. 去重 - 删除(职位+公司+工作描述)完全重复的记录")
    print("   2. 薪资标准化 - \"面议\"转为空值")
    print("   3. 文本清理 - 去除特殊字符")
    print("   4. 数据增强 - 提取薪资最小值/最大值/年薪月数")
    print("="*60 + "\n")
    
    all_city_stats = []
    
    for city_dir in CITY_DIRS:
        input_path = os.path.join(base_dir, INPUT_BASE_DIR, city_dir)
        if os.path.exists(input_path):
            output_city_dir = city_dir.replace('_cleaned', '_advanced')
            stats = process_city(base_dir, city_dir, output_city_dir, timestamp, logger)
            if stats:
                all_city_stats.append(stats)
        else:
            print(f"⚠️ 目录不存在，跳过: {city_dir}")
    
    # 生成汇总报告
    print("\n" + "="*70)
    print("📊 进阶清洗完成 - 总体统计")
    print("="*70)
    
    total_original = sum(s['original'] for s in all_city_stats)
    total_final = sum(s['final'] for s in all_city_stats)
    total_duplicates = sum(s['duplicates'] for s in all_city_stats)
    total_negotiable = sum(s['negotiable'] for s in all_city_stats)
    total_parsed = sum(s['salary_parsed'] for s in all_city_stats)
    
    print(f"\n{'城市':<12} {'原始记录':<10} {'去重后':<10} {'删除重复':<10} {'面议数':<10} {'薪资解析':<10}")
    print("-"*70)
    
    for s in all_city_stats:
        print(f"{s['city']:<12} {s['original']:<10} {s['final']:<10} {s['duplicates']:<10} {s['negotiable']:<10} {s['salary_parsed']:<10}")
    
    print("-"*70)
    print(f"{'总计':<12} {total_original:<10} {total_final:<10} {total_duplicates:<10} {total_negotiable:<10} {total_parsed:<10}")
    print("="*70)
    
    print(f"\n📈 清洗效果:")
    print(f"   • 原始记录: {total_original}")
    print(f"   • 删除重复: {total_duplicates}")
    print(f"   • 最终保留: {total_final}")
    print(f"   • 保留率: {total_final/total_original*100:.2f}%")
    print(f"   • 面议职位: {total_negotiable} ({total_negotiable/total_original*100:.1f}%)")
    print(f"   • 成功解析薪资: {total_parsed} ({total_parsed/total_original*100:.1f}%)")
    
    print(f"\n✅ 清洗后的文件保存在: {output_base}")
    print(f"📋 详细日志保存在: {log_file}\n")
    
    # 保存汇总报告
    report_path = os.path.join(log_dir, f'advanced_report_{timestamp}.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("职位数据进阶清洗报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        f.write("清洗内容:\n")
        f.write("1. 去重 - 删除(职位+公司+工作描述)完全重复的记录\n")
        f.write("2. 薪资标准化 - \"面议\"转为空值\n")
        f.write("3. 文本清理 - 去除特殊字符\n")
        f.write("4. 数据增强 - 新增列: 薪资_最小值, 薪资_最大值, 年薪月数\n\n")
        f.write("-"*70 + "\n")
        f.write(f"{'城市':<12} {'原始记录':<10} {'去重后':<10} {'删除重复':<10} {'面议数':<10} {'薪资解析':<10}\n")
        f.write("-"*70 + "\n")
        for s in all_city_stats:
            f.write(f"{s['city']:<12} {s['original']:<10} {s['final']:<10} {s['duplicates']:<10} {s['negotiable']:<10} {s['salary_parsed']:<10}\n")
        f.write("-"*70 + "\n")
        f.write(f"{'总计':<12} {total_original:<10} {total_final:<10} {total_duplicates:<10} {total_negotiable:<10} {total_parsed:<10}\n")
        f.write("="*70 + "\n")
    
    logger.info("进阶清洗全部完成!")
    
    # 关闭日志处理器
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


if __name__ == '__main__':
    main()
