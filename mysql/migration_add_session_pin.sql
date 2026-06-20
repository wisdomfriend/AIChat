-- 为 chat_sessions 增加固定（pin）字段
-- 说明：已有数据库执行一次即可；新库请直接使用 init.sql

ALTER TABLE chat_sessions
ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE COMMENT '是否固定到侧栏顶部';

CREATE INDEX idx_chat_sessions_pinned ON chat_sessions (user_id, is_pinned, updated_at);
