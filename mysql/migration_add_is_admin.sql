-- 数据库迁移脚本：添加 is_admin 字段
-- 用于在现有数据库中添加用户管理员权限字段

-- 检查并添加 is_admin 字段（如果不存在）
-- 注意：MySQL 不支持直接检查列是否存在，所以使用 ALTER TABLE ... ADD COLUMN IF NOT EXISTS（MySQL 8.0.19+）
-- 对于旧版本 MySQL，如果列已存在会报错，需要手动处理

ALTER TABLE users 
ADD COLUMN is_admin BOOLEAN DEFAULT FALSE 
AFTER is_active;

-- 如果需要将某个用户设置为管理员，可以执行以下 SQL（替换 'admin' 为实际的用户名）
-- UPDATE users SET is_admin = TRUE WHERE username = 'admin';

