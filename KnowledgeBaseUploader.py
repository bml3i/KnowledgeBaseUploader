#!/usr/bin/env python3
import os
import re
import json
import logging
import configparser
from pathlib import Path
import psycopg2
import psycopg2.extras
from datetime import datetime, date

# -------------------- 常量 --------------------
META_START = '<<<<.<<<<.<<<<'
META_END   = '>>>>.>>>>.>>>>'
SEP_LINE   = '----------'

# -------------------- 日志设置 ------------------
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f'kb_uploader_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# -------------------- 读配置 ------------------
try:
    cfg = configparser.ConfigParser()
    config_path = Path(__file__).with_name('.config.ini')
    sample_path = Path(__file__).with_name('.config.ini.sample')
    
    if not config_path.exists():
        if sample_path.exists():
            logging.error(f"配置文件不存在: {config_path}")
            logging.error(f"请从示例配置创建配置文件，执行命令: cp {sample_path} {config_path}")
            print(f"\n配置文件不存在: {config_path}")
            print(f"请从示例配置创建配置文件，执行命令: cp {sample_path} {config_path}\n")
        else:
            logging.error(f"配置文件不存在: {config_path}，示例配置文件也不存在: {sample_path}")
            print(f"\n配置文件不存在: {config_path}，示例配置文件也不存在: {sample_path}\n")
        exit(1)
        
    cfg.read(config_path, encoding='utf-8')
    
    ROOT = Path(cfg['common']['root_path']).expanduser()
    if not ROOT.exists():
        logging.warning(f"指定的根目录不存在: {ROOT}，将尝试创建")
        ROOT.mkdir(parents=True, exist_ok=True)
        
    EXT = cfg['common']['file_extension'].strip()
    EXT = None if EXT == '*' else {e.strip().lower() for e in EXT.split(',')}
    
    logging.info(f"扫描目录: {ROOT}")
    logging.info(f"文件扩展名过滤: {EXT if EXT else '所有文件'}")
    
    # 数据库连接
    DB = cfg['postgres']
    try:
        conn = psycopg2.connect(
            host=DB['server'], port=DB['port'], dbname=DB['db'],
            user=DB['user'], password=DB['password'],
            sslmode=DB.get('sslmode', 'prefer')
        )
        logging.info("数据库连接成功")
    except psycopg2.Error as e:
        logging.error(f"数据库连接失败: {e}")
        exit(1)
        
except KeyError as e:
    logging.error(f"配置文件缺少必要的配置项: {e}")
    exit(1)
except Exception as e:
    logging.error(f"读取配置文件时出错: {e}")
    exit(1)

# -------------------- 工具函数 ----------------
def extract_date_from_resources(resources):
    """从resources数组中提取yyyy-MM-dd格式的日期"""
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    for resource in resources:
        if isinstance(resource, str) and date_pattern.match(resource):
            try:
                # 验证是否为合法日期
                parsed_date = datetime.strptime(resource, '%Y-%m-%d').date()
                return parsed_date
            except ValueError:
                # 格式匹配但不是合法日期，继续检查下一个
                continue
    return None

def upsert_tags(cur, tags):
    """返回 tag_id 列表"""
    tag_ids = []
    for t in tags:
        cur.execute("""
            INSERT INTO kb_tags(name) VALUES(%s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
        """, (t,))
        if cur.rowcount:            # 刚插入
            tag_ids.append(cur.fetchone()[0])
        else:                       # 已存在
            cur.execute("SELECT id FROM kb_tags WHERE name=%s", (t,))
            tag_ids.append(cur.fetchone()[0])
    return tag_ids

def upsert_record(cur, meta, content):
    """插入或更新一条知识记录"""
    # 1. 提取字段（确保每个变量都先定义）
    echo_token = meta['echoToken']
    summary    = meta['summary']
    resources  = meta['resources']
    tags       = [t.lower() for t in meta['tags']]
    is_active  = meta.get('isActive')
    if is_active is None:
        is_active = True            # 新增时默认 True

    # 2. 检查是否存在记录（判断是否为更新操作）
    cur.execute("SELECT id, created_at FROM kb_records WHERE echo_token = %s", (echo_token,))
    existing_record = cur.fetchone()
    is_update = existing_record is not None
    
    # 3. 检查resources中是否包含日期格式
    target_date = extract_date_from_resources(resources)
    
    # 4. 构建SQL语句
    if is_update and target_date:
        # 更新操作且找到日期：需要更新created_at的日期部分
        existing_id, existing_created_at = existing_record
        # 保持原有的时间部分，只替换日期部分
        new_created_at = datetime.combine(target_date, existing_created_at.time())
        if existing_created_at.tzinfo:
            new_created_at = new_created_at.replace(tzinfo=existing_created_at.tzinfo)
        
        cur.execute("""
             INSERT INTO kb_records(echo_token, summary, content, resources, tags_cache, is_active, created_at)
             VALUES (%s, %s, %s, %s, %s, %s, %s)
             ON CONFLICT (echo_token) DO UPDATE
             SET summary    = EXCLUDED.summary,
                 content    = EXCLUDED.content,
                 resources  = EXCLUDED.resources,
                 tags_cache = EXCLUDED.tags_cache,
                 created_at = EXCLUDED.created_at,
                 is_active  = CASE
                        WHEN EXCLUDED.is_active IS NULL   -- JSON 里没给值
                        THEN kb_records.is_active         -- 保持原值
                        ELSE EXCLUDED.is_active           -- 用 JSON 提供的 true/false
                      END
             RETURNING id
         """, (echo_token, summary, content, resources, tags, is_active, new_created_at))
        
        logging.info(f"更新记录 {echo_token} 的created_at日期部分为: {target_date}")
    else:
        # 新增操作或更新操作但没有日期：使用原有逻辑
        cur.execute("""
            INSERT INTO kb_records(echo_token, summary, content, resources, tags_cache, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (echo_token) DO UPDATE
            SET summary    = EXCLUDED.summary,
                content    = EXCLUDED.content,
                resources  = EXCLUDED.resources,
                tags_cache = EXCLUDED.tags_cache,
                is_active  = CASE
                       WHEN EXCLUDED.is_active IS NULL   -- JSON 里没给值
                       THEN kb_records.is_active         -- 保持原值
                       ELSE EXCLUDED.is_active           -- 用 JSON 提供的 true/false
                     END
            RETURNING id
        """, (echo_token, summary, content, resources, tags, is_active))
    
    rid = cur.fetchone()[0]

    # 3. 维护 tag 关系
    tag_ids = upsert_tags(cur, tags)
    cur.execute("DELETE FROM kb_record_tags WHERE record_id = %s", (rid,))
    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO kb_record_tags(record_id, tag_id) VALUES %s",
        [(rid, tid) for tid in tag_ids]
    )

# -------------------- 主循环 ------------------
def validate_metadata(meta, path):
    """验证元数据是否包含所有必要字段"""
    required_fields = ['echoToken', 'summary', 'tags', 'resources']
    for field in required_fields:
        if field not in meta:
            logging.error(f"元数据缺少必要字段 '{field}' 在文件 {path}")
            return False
            
    # 验证字段类型
    if not isinstance(meta['tags'], list):
        logging.error(f"元数据中 'tags' 必须是数组类型 在文件 {path}")
        return False
        
    if not isinstance(meta['resources'], list):
        logging.error(f"元数据中 'resources' 必须是数组类型 在文件 {path}")
        return False
        
    return True

try:
    meta_re = re.compile(re.escape(META_START) + r'(.*?)' + re.escape(META_END), re.DOTALL)

    files = ROOT.rglob('*') if EXT is None else \
            (p for p in ROOT.rglob('*') if p.suffix.lower().lstrip('.') in EXT)

    total_files = 0
    processed_files = 0
    records_found = 0
    records_updated = 0
    records_failed = 0

    logging.info("开始扫描文件...")

    for path in files:
        if not path.is_file():
            continue
            
        total_files += 1
        
        # 跳过日志文件夹中的文件
        if log_dir in path.parents:
            continue
            
        try:
            text = path.read_text(encoding='utf-8', errors='ignore')
            processed_files += 1
        except Exception as e:
            logging.error(f"读取文件失败: {path}, 错误: {e}")
            continue

        for m in meta_re.finditer(text):
            records_found += 1
            meta_json = m.group(1).strip()
            try:
                meta = json.loads(meta_json)
            except Exception as e:          # 捕获所有解析异常
                logging.error(f"JSON解析失败 在文件 {path}, 错误: {e}")
                logging.debug(f"有问题的JSON >>> {meta_json} <<<")
                records_failed += 1
                continue                    # 必须跳过，不能往下走

            # 验证元数据
            if not isinstance(meta, dict):
                logging.error(f"元数据不是字典类型 在文件 {path}")
                records_failed += 1
                continue
                
            if not validate_metadata(meta, path):
                records_failed += 1
                continue

            start = m.end()
            end_sep = text.find(SEP_LINE, start)
            content = text[start:end_sep if end_sep != -1 else None].strip()

            try:
                with conn.cursor() as cur:
                    upsert_record(cur, meta, content)
                conn.commit()
                records_updated += 1
                logging.info(f"成功更新记录: {meta['echoToken']} 从文件 {path}")
            except psycopg2.Error as e:
                conn.rollback()
                logging.error(f"数据库操作失败: {e}, 在文件 {path}, echoToken: {meta.get('echoToken', '未知')}")
                records_failed += 1

    logging.info(f"扫描完成: 总文件数 {total_files}, 处理文件数 {processed_files}")
    logging.info(f"知识库记录: 发现 {records_found}, 更新 {records_updated}, 失败 {records_failed}")

except Exception as e:
    logging.error(f"程序执行过程中发生错误: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
        logging.info("数据库连接已关闭")
    
    logging.info("KnowledgeBaseUploader 执行完毕")
    print(f"KnowledgeBaseUploader 执行完毕，详细日志请查看: {log_file}")