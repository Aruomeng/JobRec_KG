-- Neo4j 索引优化脚本
-- 用于提升高频查询性能
-- 运行方式: 在 Neo4j Browser 中执行或通过 cypher-shell

-- 学生节点索引
CREATE INDEX student_id_idx IF NOT EXISTS FOR (s:Student) ON (s.student_id);
CREATE INDEX student_username_idx IF NOT EXISTS FOR (s:Student) ON (s.username);

-- 技能节点索引 (最高频查询)
CREATE INDEX skill_name_idx IF NOT EXISTS FOR (sk:Skill) ON (sk.name);

-- 职位节点索引
CREATE INDEX job_url_idx IF NOT EXISTS FOR (j:Job) ON (j.url);
CREATE INDEX job_title_idx IF NOT EXISTS FOR (j:Job) ON (j.title);

-- 公司节点索引
CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.name);

-- 城市节点索引
CREATE INDEX city_name_idx IF NOT EXISTS FOR (ct:City) ON (ct.name);

-- 课程节点索引
CREATE INDEX course_name_idx IF NOT EXISTS FOR (c:Course) ON (c.name);
