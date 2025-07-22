#!/usr/bin/env python3
import os
import re
import json
import configparser
from pathlib import Path
import psycopg2
import psycopg2.extras

# -------------------- 常量 --------------------
META_START = '<<<<.<<<<.<<<<'
META_END   = '>>>>.>>>>.>>>>'
SEP_LINE   = '----------'

# -------------------- 读配置 ------------------
cfg = configparser.ConfigParser()
cfg.read(Path(__file__).with_name('config.ini'), encoding='utf-8')

ROOT = Path(cfg['common']['root_path']).expanduser()
EXT  = cfg['common']['file_extension'].strip()
EXT  = None if EXT == '*' else {e.strip().lower() for e in EXT.split(',')}

DB = cfg['postgres']
conn = psycopg2.connect(
    host=DB['server'], port=DB['port'], dbname=DB['db'],
    user=DB['user'], password=DB['password']
)

# -------------------- 工具函数 ----------------
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

    # 新增时插入；冲突时只有 is_active 有提供才更新，否则保持原值
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
meta_re = re.compile(re.escape(META_START) + r'(.*?)' + re.escape(META_END), re.DOTALL)

files = ROOT.rglob('*') if EXT is None else \
        (p for p in ROOT.rglob('*') if p.suffix.lower().lstrip('.') in EXT)

for path in files:
    if not path.is_file():
        continue
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print('Read error:', path, e)
        continue

    for m in meta_re.finditer(text):
        meta_json = m.group(1).strip()
        try:
            meta = json.loads(meta_json)
        except Exception as e:          # 捕获所有解析异常
            print('Invalid JSON in', path, e)
            print('Problematic JSON >>>', meta_json, '<<<')
            continue                    # 必须跳过，不能往下走

        # 下面这一行只是防御式二次检查，可留可不留
        if not isinstance(meta, dict):
            print('Meta is not dict in', path)
            continue

        start = m.end()
        end_sep = text.find(SEP_LINE, start)
        content = text[start:end_sep if end_sep != -1 else None].strip()

        with conn.cursor() as cur:
            upsert_record(cur, meta, content)
        conn.commit()

conn.close()
print('KnowledgeBaseUploader finished.')