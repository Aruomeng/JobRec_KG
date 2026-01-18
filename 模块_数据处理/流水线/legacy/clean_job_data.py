#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
职位数据清洗脚本
================
功能：
1. 检查并删除缺少"职位/公司/工作描述"的记录
2. 生成详细的清洗日志（包含删除理由）
3. 支持批量处理多个城市目录下所有CSV文件
4. 每个城市单独输出清洗结果和日志

作者：AI Assistant
日期：2026-01-12
"""

import os
import pandas as pd
from datetime import datetime
import logging

# ==================== 配置 ====================
# 必须字段 - 缺少任意一个则删除该记录
REQUIRED_FIELDS = ['职位', '公司', '工作描述']

# 需要处理的城市数据目录
DATA_DIRS = [
    'data_beijing',
    'data_chengdu', 
    'data_chongqing',
    'data_hangzhou',
    'data_nanjin',
    'data_shenzhen',
    'data_wuhan',
    'data_xiamen',
    'data_zhengzhou'
]

# ==================== 日志配置 ====================
def setup_logger(log_file, city_name):
    """配置日志记录器"""
    logger = logging.getLogger(f'DataCleaner_{city_name}')
    logger.setLevel(logging.INFO)
    
    # 清除之前的处理器
    logger.handlers = []
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# ==================== 核心清洗函数 ====================
def check_required_fields(row, required_fields):
    """
    检查记录是否缺少必须字段
    
    返回:
        (bool, str): (是否有效, 删除理由)
    """
    missing_fields = []
    
    for field in required_fields:
        value = row.get(field, None)
        # 检查是否为空值
        if pd.isna(value) or (isinstance(value, str) and value.strip() == ''):
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"缺少必填字段: {', '.join(missing_fields)}"
    
    return True, ""


def clean_single_file(input_path, output_path, logger):
    """
    清洗单个CSV文件
    """
    filename = os.path.basename(input_path)
    logger.info(f"{'='*60}")
    logger.info(f"开始处理文件: {filename}")
    logger.info(f"{'='*60}")
    
    stats = {
        'filename': filename,
        'original_count': 0,
        'cleaned_count': 0,
        'removed_count': 0,
        'removal_reasons': []
    }
    
    try:
        # 读取CSV文件
        df = pd.read_csv(input_path, encoding='utf-8')
        stats['original_count'] = len(df)
        logger.info(f"原始记录数: {len(df)}")
        
        # 检查必须字段是否存在
        for field in REQUIRED_FIELDS:
            if field not in df.columns:
                logger.error(f"错误: 文件缺少必须列 '{field}'")
                return stats
        
        # 存储有效记录和删除记录
        valid_rows = []
        removed_entries = []
        
        for idx, row in df.iterrows():
            is_valid, reason = check_required_fields(row, REQUIRED_FIELDS)
            
            if is_valid:
                valid_rows.append(row)
            else:
                job_title = row.get('职位', 'N/A')
                company = row.get('公司', 'N/A')
                removed_entry = {
                    'row_number': idx + 2,
                    'job_title': job_title if pd.notna(job_title) else 'N/A',
                    'company': company if pd.notna(company) else 'N/A',
                    'reason': reason
                }
                removed_entries.append(removed_entry)
                logger.warning(f"删除记录 [行{idx+2}]: 职位='{removed_entry['job_title']}', "
                             f"公司='{removed_entry['company']}' | 理由: {reason}")
        
        stats['cleaned_count'] = len(valid_rows)
        stats['removed_count'] = len(removed_entries)
        stats['removal_reasons'] = removed_entries
        
        if valid_rows:
            cleaned_df = pd.DataFrame(valid_rows)
            cleaned_df.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"清洗后记录数: {len(valid_rows)}")
            logger.info(f"删除记录数: {len(removed_entries)}")
            logger.info(f"保留率: {len(valid_rows)/len(df)*100:.2f}%")
        else:
            logger.warning(f"警告: 清洗后没有剩余有效记录!")
        
    except Exception as e:
        logger.error(f"处理文件时发生错误: {str(e)}")
        raise
    
    return stats


def generate_city_report(city_name, all_stats, output_path, logger):
    """生成城市汇总报告"""
    total_original = sum(s['original_count'] for s in all_stats)
    total_cleaned = sum(s['cleaned_count'] for s in all_stats)
    total_removed = sum(s['removed_count'] for s in all_stats)
    
    report_lines = [
        "="*70,
        f"【{city_name}】职位数据清洗报告",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "="*70,
        "",
        "【统计摘要】",
        f"  处理文件数: {len(all_stats)}",
        f"  原始总记录数: {total_original}",
        f"  清洗后总记录数: {total_cleaned}",
        f"  删除总记录数: {total_removed}",
        f"  保留率: {total_cleaned/total_original*100:.2f}%" if total_original > 0 else "  保留率: N/A",
        "",
        "-"*70,
        "【删除记录明细】",
        "-"*70,
    ]
    
    for stats in all_stats:
        if stats['removal_reasons']:
            report_lines.append(f"\n文件: {stats['filename']}")
            for entry in stats['removal_reasons']:
                report_lines.append(
                    f"  行{entry['row_number']}: [{entry['job_title']}]@[{entry['company']}] | {entry['reason']}"
                )
    
    # 如果没有删除记录
    if total_removed == 0:
        report_lines.append("\n无删除记录，所有数据完整有效。")
    
    report_lines.extend(["", "="*70, "报告结束", "="*70])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    
    logger.info(f"报告已保存: {output_path}")
    
    return {
        'city': city_name,
        'files': len(all_stats),
        'original': total_original,
        'cleaned': total_cleaned,
        'removed': total_removed
    }


def process_city(base_dir, city_dir, timestamp):
    """处理单个城市的数据"""
    city_name = city_dir.replace('data_', '').upper()
    input_dir = os.path.join(base_dir, city_dir)
    
    # 每个城市单独的输出目录
    output_dir = os.path.join(base_dir, f'{city_dir}_cleaned')
    log_dir = os.path.join(output_dir, 'logs')
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    # 设置日志
    log_file = os.path.join(log_dir, f'cleaning_log_{timestamp}.log')
    logger = setup_logger(log_file, city_name)
    
    logger.info("="*60)
    logger.info(f"开始处理城市: {city_name}")
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"输出目录: {output_dir}")
    logger.info("="*60)
    
    # 获取所有CSV文件
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    
    if not csv_files:
        logger.warning(f"城市 {city_name} 未找到CSV文件!")
        return None
    
    logger.info(f"找到 {len(csv_files)} 个CSV文件")
    
    all_stats = []
    
    for csv_file in sorted(csv_files):
        input_path = os.path.join(input_dir, csv_file)
        output_filename = csv_file.replace('.csv', '_cleaned.csv')
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            stats = clean_single_file(input_path, output_path, logger)
            all_stats.append(stats)
        except Exception as e:
            logger.error(f"处理文件 {csv_file} 失败: {str(e)}")
            continue
    
    # 生成城市报告
    report_path = os.path.join(log_dir, f'cleaning_report_{timestamp}.txt')
    city_summary = generate_city_report(city_name, all_stats, report_path, logger)
    
    logger.info(f"\n{city_name} 处理完成!")
    
    # 关闭日志处理器
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    
    return city_summary


def main():
    """主函数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("\n" + "="*60)
    print("🚀 职位数据清洗程序启动")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 基础目录: {base_dir}")
    print(f"🏙️  待处理城市: {len(DATA_DIRS)} 个")
    print("="*60 + "\n")
    
    all_city_summaries = []
    
    for city_dir in DATA_DIRS:
        city_path = os.path.join(base_dir, city_dir)
        if os.path.exists(city_path):
            summary = process_city(base_dir, city_dir, timestamp)
            if summary:
                all_city_summaries.append(summary)
        else:
            print(f"⚠️ 目录不存在，跳过: {city_dir}")
    
    # 打印总汇总
    print("\n" + "="*60)
    print("📊 全部城市清洗完成 - 总体统计")
    print("="*60)
    
    total_files = sum(s['files'] for s in all_city_summaries)
    total_original = sum(s['original'] for s in all_city_summaries)
    total_cleaned = sum(s['cleaned'] for s in all_city_summaries)
    total_removed = sum(s['removed'] for s in all_city_summaries)
    
    print(f"{'城市':<12} {'文件数':<8} {'原始记录':<12} {'保留记录':<12} {'删除记录':<10} {'保留率':<10}")
    print("-"*60)
    
    for s in all_city_summaries:
        rate = f"{s['cleaned']/s['original']*100:.1f}%" if s['original'] > 0 else "N/A"
        print(f"{s['city']:<12} {s['files']:<8} {s['original']:<12} {s['cleaned']:<12} {s['removed']:<10} {rate:<10}")
    
    print("-"*60)
    total_rate = f"{total_cleaned/total_original*100:.1f}%" if total_original > 0 else "N/A"
    print(f"{'总计':<12} {total_files:<8} {total_original:<12} {total_cleaned:<12} {total_removed:<10} {total_rate:<10}")
    print("="*60)
    
    print("\n✅ 清洗后的文件保存在各城市目录下的 *_cleaned 文件夹中")
    print("📋 详细日志和报告保存在各文件夹的 logs 子目录中\n")


if __name__ == '__main__':
    main()
