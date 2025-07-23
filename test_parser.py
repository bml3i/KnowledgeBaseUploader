#!/usr/bin/env python3
"""
测试脚本：验证知识库解析功能，但不会实际写入数据库
用法：python test_parser.py [文件路径]
"""

import sys
import re
import json
from pathlib import Path

# 常量
META_START = '<<<<.<<<<.<<<<'
META_END   = '>>>>.>>>>.>>>>'
SEP_LINE   = '----------'

def validate_metadata(meta):
    """验证元数据是否包含所有必要字段"""
    required_fields = ['echoToken', 'summary', 'tags', 'resources']
    missing_fields = [field for field in required_fields if field not in meta]
    
    if missing_fields:
        return False, f"缺少必要字段: {', '.join(missing_fields)}"
        
    # 验证字段类型
    if not isinstance(meta['tags'], list):
        return False, "'tags' 必须是数组类型"
        
    if not isinstance(meta['resources'], list):
        return False, "'resources' 必须是数组类型"
        
    return True, "验证通过"

def parse_file(file_path):
    """解析文件中的知识库内容"""
    path = Path(file_path)
    if not path.exists():
        print(f"错误: 文件不存在 {path}")
        return
        
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"错误: 无法读取文件 {path}, {e}")
        return
        
    meta_re = re.compile(re.escape(META_START) + r'(.*?)' + re.escape(META_END), re.DOTALL)
    matches = list(meta_re.finditer(text))
    
    if not matches:
        print(f"未找到知识库内容 在文件 {path}")
        return
        
    print(f"在文件 {path} 中找到 {len(matches)} 个知识库条目")
    print("-" * 50)
    
    for i, m in enumerate(matches, 1):
        print(f"条目 #{i}:")
        meta_json = m.group(1).strip()
        
        try:
            meta = json.loads(meta_json)
        except Exception as e:
            print(f"  JSON解析失败: {e}")
            print(f"  有问题的JSON >>> {meta_json[:100]}... <<<")
            print("-" * 50)
            continue
            
        if not isinstance(meta, dict):
            print(f"  错误: 元数据不是字典类型")
            print("-" * 50)
            continue
            
        valid, message = validate_metadata(meta)
        if not valid:
            print(f"  元数据验证失败: {message}")
            print("-" * 50)
            continue
            
        # 提取内容
        start = m.end()
        end_sep = text.find(SEP_LINE, start)
        content = text[start:end_sep if end_sep != -1 else None].strip()
        
        # 打印元数据和内容摘要
        print(f"  echoToken: {meta.get('echoToken', '未知')}")
        print(f"  summary: {meta.get('summary', '未知')}")
        print(f"  tags: {', '.join(meta.get('tags', []))}")
        print(f"  resources: {len(meta.get('resources', []))} 个资源")
        print(f"  isActive: {meta.get('isActive', True)}")
        
        content_preview = content[:100] + "..." if len(content) > 100 else content
        print(f"  内容预览: {content_preview}")
        print(f"  内容长度: {len(content)} 字符")
        print("-" * 50)

def main():
    if len(sys.argv) < 2:
        # 如果没有提供文件路径，使用示例文件
        example_path = Path(__file__).parent / 'example.md'
        if example_path.exists():
            parse_file(example_path)
        else:
            print("用法: python test_parser.py [文件路径]")
            print("示例文件不存在，请提供要解析的文件路径")
    else:
        parse_file(sys.argv[1])

if __name__ == "__main__":
    main()