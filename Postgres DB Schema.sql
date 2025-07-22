-- 1. 主表
CREATE TABLE kb_records (
    id          BIGSERIAL PRIMARY KEY,
    echo_token  VARCHAR(64)  NOT NULL UNIQUE,
    summary     TEXT         NOT NULL,
    content     TEXT         NOT NULL,
    resources   TEXT[]       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    tags_cache  TEXT[]       NOT NULL DEFAULT '{}',
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);


-- 2. 标签维度表（可 ON CONFLICT DO NOTHING 插入）
CREATE TABLE kb_tags (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL
);

-- 3. 多对多桥接表
CREATE TABLE kb_record_tags (
    record_id BIGINT NOT NULL REFERENCES kb_records(id) ON DELETE CASCADE,
    tag_id    INT    NOT NULL REFERENCES kb_tags(id)    ON DELETE CASCADE,
    PRIMARY KEY (record_id, tag_id)
);

-- 4.1. 聚合视图01（方便一次性拿到 tags 数组）
CREATE OR REPLACE VIEW v_kb_search AS
SELECT r.id,
       r.echo_token,
       r.summary,
       r.content,
       r.resources,
	   r.is_active,
       r.created_at,
       COALESCE(ARRAY_AGG(t.name ORDER BY t.name), ARRAY[]::TEXT[]) AS tags
FROM kb_records r
LEFT JOIN kb_record_tags rt ON rt.record_id = r.id
LEFT JOIN kb_tags t        ON t.id = rt.tag_id
GROUP BY r.id;


-- 4.2. 聚合视图02（方便一次性拿到 tags 数组, 客户端查询时使用）
CREATE OR REPLACE VIEW v_active_kb_search AS
SELECT r.id,
       r.echo_token,
       r.summary,
       r.content,
       r.resources,
	   r.is_active,
       r.created_at,
       COALESCE(ARRAY_AGG(t.name ORDER BY t.name), ARRAY[]::TEXT[]) AS tags
FROM kb_records r
LEFT JOIN kb_record_tags rt ON rt.record_id = r.id
LEFT JOIN kb_tags t        ON t.id = rt.tag_id
WHERE r.is_active = TRUE
GROUP BY r.id
ORDER BY r.created_at DESC;

-- 5. 核心索引
CREATE INDEX idx_kb_tags_cache_gin ON kb_records USING GIN (tags_cache);

-- 客户端根据tags查询的例子: 
SELECT *
FROM v_active_kb_search
WHERE tags @> ARRAY['tag01', 'tag02']::varchar[];