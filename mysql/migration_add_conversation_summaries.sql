-- 数据库迁移：创建对话摘要表
-- 执行时间：2024年
-- 说明：用于存储对话压缩后的摘要，支持无限上下文对话

-- 创建对话摘要表
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    message_count INT NOT NULL COMMENT '覆盖的消息轮数（从第0轮开始）',
    summary_content TEXT NOT NULL COMMENT '摘要内容',
    token_count INT COMMENT '摘要的token数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    INDEX idx_session_created (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话摘要表，用于上下文压缩';

