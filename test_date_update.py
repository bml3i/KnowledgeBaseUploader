#!/usr/bin/env python3
"""
测试日期更新功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, date
import re
from KnowledgeBaseUploader import extract_date_from_resources

def test_extract_date_from_resources():
    """测试日期提取函数"""
    print("测试日期提取功能...")
    
    # 测试用例
    test_cases = [
        # (resources数组, 期望结果)
        (["2025-07-24"], date(2025, 7, 24)),
        (["file.txt", "2025-12-31", "other"], date(2025, 12, 31)),
        (["2025-02-29"], None),  # 无效日期
        (["2024-02-29"], date(2024, 2, 29)),  # 闰年有效日期
        (["25-07-24"], None),  # 格式不匹配
        (["2025-7-24"], None),  # 格式不匹配（月份缺少前导零）
        (["2025-07-32"], None),  # 无效日期
        (["file.txt", "other"], None),  # 没有日期
        ([], None),  # 空数组
        (["2025-01-01", "2025-02-02"], date(2025, 1, 1)),  # 多个日期，返回第一个
    ]
    
    for i, (resources, expected) in enumerate(test_cases, 1):
        result = extract_date_from_resources(resources)
        status = "✓" if result == expected else "✗"
        print(f"测试 {i}: {status} resources={resources} -> {result} (期望: {expected})")
        
        if result != expected:
            print(f"  错误: 期望 {expected}, 得到 {result}")

def test_datetime_combination():
    """测试日期时间组合功能"""
    print("\n测试日期时间组合功能...")
    
    # 模拟现有的created_at时间戳
    existing_created_at = datetime(2024, 1, 15, 14, 30, 45, 123456)
    target_date = date(2025, 7, 24)
    
    # 组合新的日期时间
    new_created_at = datetime.combine(target_date, existing_created_at.time())
    
    print(f"原始时间: {existing_created_at}")
    print(f"目标日期: {target_date}")
    print(f"新时间: {new_created_at}")
    
    # 验证结果
    assert new_created_at.date() == target_date
    assert new_created_at.time() == existing_created_at.time()
    print("✓ 日期时间组合测试通过")

if __name__ == "__main__":
    test_extract_date_from_resources()
    test_datetime_combination()
    print("\n所有测试完成！")