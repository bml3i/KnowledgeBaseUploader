#!/usr/bin/env python3
"""
初始化脚本：创建必要的配置文件和目录
"""

import os
import shutil
from pathlib import Path

def main():
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    
    # 检查并创建配置文件
    config_file = script_dir / '.config.ini'
    sample_file = script_dir / '.config.ini.sample'
    
    if not config_file.exists() and sample_file.exists():
        print(f"创建配置文件: {config_file}")
        shutil.copy(sample_file, config_file)
        print("请编辑配置文件，填写正确的数据库连接信息和扫描目录")
    elif config_file.exists():
        print(f"配置文件已存在: {config_file}")
    else:
        print(f"错误: 示例配置文件不存在: {sample_file}")
        return
    
    # 创建日志目录
    logs_dir = script_dir / 'logs'
    if not logs_dir.exists():
        print(f"创建日志目录: {logs_dir}")
        logs_dir.mkdir(exist_ok=True)
    else:
        print(f"日志目录已存在: {logs_dir}")
    
    print("\n初始化完成！您现在可以编辑配置文件并运行程序：")
    print("1. 编辑配置文件: nano .config.ini")
    print("2. 运行程序: python KnowledgeBaseUploader.py")

if __name__ == "__main__":
    main()