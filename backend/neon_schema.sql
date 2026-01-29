-- ============================================
-- Neon PostgreSQL 用户表结构和测试账号
-- ============================================

-- 1. 创建用户资料表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT NOT NULL CHECK (role IN ('student', 'enterprise', 'university')),
    neo4j_id TEXT,
    email TEXT,
    -- 企业端扩展字段
    company_name TEXT,
    industry TEXT,
    company_scale TEXT,
    city TEXT,
    contact_info TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ============================================
-- 插入测试账号 (密码: 123456)
-- ============================================

-- 学生端账号: 18162572004 / 123456
INSERT INTO users (username, password_hash, display_name, role, neo4j_id)
VALUES (
    '18162572004',
    '$2b$12$J9zdRuHj7Lp6b0SFsEbkzucvn7ZbNyDYUnypA.86pQb05jIHgHSHO',
    '田雨航',
    'student',
    'STU0501'
) ON CONFLICT (username) DO UPDATE SET 
    password_hash = EXCLUDED.password_hash;

-- 企业端账号: admin / 123456
INSERT INTO users (username, password_hash, display_name, role)
VALUES (
    'admin',
    '$2b$12$J9zdRuHj7Lp6b0SFsEbkzucvn7ZbNyDYUnypA.86pQb05jIHgHSHO',
    '企业管理员',
    'enterprise'
) ON CONFLICT (username) DO UPDATE SET 
    password_hash = EXCLUDED.password_hash;

-- 高校端账号: admin / 123456
INSERT INTO users (username, password_hash, display_name, role)
VALUES (
    'admin',
    '$2b$12$J9zdRuHj7Lp6b0SFsEbkzucvn7ZbNyDYUnypA.86pQb05jIHgHSHO',
    '高校管理员',
    'university'
) ON CONFLICT (username) DO UPDATE SET 
    password_hash = EXCLUDED.password_hash;

-- 验证
SELECT id, username, display_name, role, neo4j_id FROM users;
