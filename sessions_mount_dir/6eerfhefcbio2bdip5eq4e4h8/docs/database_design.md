# 数据库设计文档

## 概述

本文档描述了健身管理系统的数据库设计，包括表结构、关系和约束。系统使用 PostgreSQL 作为数据库，通过 SQLAlchemy 进行 ORM 映射。

## 数据库表设计

### 1. 用户表 (users)

存储系统用户信息，包括管理员和会员。

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'member')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. 教练表 (coaches)

存储教练信息，与用户表关联。

```sql
CREATE TABLE coaches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    specialization VARCHAR(100),
    certification VARCHAR(100),
    bio TEXT,
    is_available BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. 课程表 (courses)

存储健身课程信息。

```sql
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    duration INTEGER NOT NULL, -- 课程时长（分钟）
    max_capacity INTEGER NOT NULL,
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. 课程安排表 (course_schedules)

存储具体的课程安排信息。

```sql
CREATE TABLE course_schedules (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    coach_id INTEGER REFERENCES coaches(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    location VARCHAR(100),
    current_capacity INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_capacity CHECK (current_capacity <= (SELECT max_capacity FROM courses WHERE id = course_id)),
    CONSTRAINT check_time CHECK (end_time > start_time)
);
```

### 5. 预约表 (bookings)

存储会员预约课程的信息。

```sql
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    schedule_id INTEGER REFERENCES course_schedules(id) ON DELETE CASCADE,
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled', 'completed')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(member_id, schedule_id)
);
```

## 索引设计

```sql
-- 用户表索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- 教练表索引
CREATE INDEX idx_coaches_user_id ON coaches(user_id);
CREATE INDEX idx_coaches_available ON coaches(is_available);

-- 课程表索引
CREATE INDEX idx_courses_active ON courses(is_active);
CREATE INDEX idx_courses_difficulty ON courses(difficulty_level);

-- 课程安排表索引
CREATE INDEX idx_schedules_course_id ON course_schedules(course_id);
CREATE INDEX idx_schedules_coach_id ON course_schedules(coach_id);
CREATE INDEX idx_schedules_start_time ON course_schedules(start_time);
CREATE INDEX idx_schedules_status ON course_schedules(status);

-- 预约表索引
CREATE INDEX idx_bookings_member_id ON bookings(member_id);
CREATE INDEX idx_bookings_schedule_id ON bookings(schedule_id);
CREATE INDEX idx_bookings_status ON bookings(status);
```

## 视图设计

### 1. 课程详情视图 (course_details_view)

```sql
CREATE VIEW course_details_view AS
SELECT 
    c.id as course_id,
    c.name as course_name,
    c.description,
    c.duration,
    c.max_capacity,
    c.difficulty_level,
    cs.id as schedule_id,
    cs.start_time,
    cs.end_time,
    cs.location,
    cs.current_capacity,
    cs.status as schedule_status,
    co.id as coach_id,
    u.full_name as coach_name,
    co.specialization
FROM courses c
JOIN course_schedules cs ON c.id = cs.course_id
JOIN coaches co ON cs.coach_id = co.id
JOIN users u ON co.user_id = u.id
WHERE c.is_active = true;
```

### 2. 会员预约视图 (member_bookings_view)

```sql
CREATE VIEW member_bookings_view AS
SELECT 
    b.id as booking_id,
    b.member_id,
    u.full_name as member_name,
    b.schedule_id,
    c.name as course_name,
    cs.start_time,
    cs.end_time,
    cs.location,
    u2.full_name as coach_name,
    b.status as booking_status,
    b.booking_time
FROM bookings b
JOIN users u ON b.member_id = u.id
JOIN course_schedules cs ON b.schedule_id = cs.id
JOIN courses c ON cs.course_id = c.id
JOIN coaches co ON cs.coach_id = co.id
JOIN users u2 ON co.user_id = u2.id;
```

## 触发器设计

### 1. 更新时间戳触发器

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_coaches_updated_at BEFORE UPDATE ON coaches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_courses_updated_at BEFORE UPDATE ON courses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_schedules_updated_at BEFORE UPDATE ON course_schedules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_bookings_updated_at BEFORE UPDATE ON bookings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2. 课程容量更新触发器

```sql
CREATE OR REPLACE FUNCTION update_schedule_capacity()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE course_schedules 
        SET current_capacity = current_capacity + 1 
        WHERE id = NEW.schedule_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE course_schedules 
        SET current_capacity = current_capacity - 1 
        WHERE id = OLD.schedule_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_capacity_on_booking 
AFTER INSERT OR DELETE ON bookings 
FOR EACH ROW EXECUTE FUNCTION update_schedule_capacity();
```

## 数据库关系图

```
users (1) -----> (1) coaches
 |
 | (member)
 |
 (1) -----> (N) bookings
                |
                | (schedule)
                |
                (N) -----> (1) course_schedules
                                |
                                | (course)
                                |
                                (N) -----> (1) courses
                                |
                                | (coach)
                                |
                                (N) -----> (1) coaches
```

## 初始化数据

```sql
-- 插入管理员用户
INSERT INTO users (username, email, password_hash, full_name, role) VALUES
('admin', 'admin@gym.com', '$2b$12$...', '系统管理员', 'admin');

-- 插入示例教练
INSERT INTO users (username, email, password_hash, full_name, phone, role) VALUES
('coach1', 'coach1@gym.com', '$2b$12$...', '张教练', '13800138001', 'member'),
('coach2', 'coach2@gym.com', '$2b$12$...', '李教练', '13800138002', 'member');

INSERT INTO coaches (user_id, specialization, certification, bio) VALUES
(2, '瑜伽', 'RYT-500', '10年瑜伽教学经验'),
(3, '力量训练', 'NASM-CPT', '专业健身教练');

-- 插入示例课程
INSERT INTO courses (name, description, duration, max_capacity, difficulty_level) VALUES
('瑜伽基础', '适合初学者的瑜伽课程', 60, 20, 'beginner'),
('力量训练', '全身力量训练课程', 45, 15, 'intermediate'),
('HIIT训练', '高强度间歇训练', 30, 10, 'advanced');
```

## 备份与恢复策略

1. **定期备份**：每天凌晨2点自动备份数据库
2. **备份保留**：保留最近30天的备份
3. **备份命令**：
   ```bash
   pg_dump -U username -d gym_management > backup_$(date +%Y%m%d).sql
   ```
4. **恢复命令**：
   ```bash
   psql -U username -d gym_management < backup_20231201.sql
   ```

## 性能优化建议

1. 定期分析表统计信息：`ANALYZE;`
2. 重建索引：`REINDEX DATABASE gym_management;`
3. 监控慢查询并优化
4. 考虑对大表进行分区
5. 使用连接池管理数据库连接

## 安全考虑

1. 所有密码使用 bcrypt 加密存储
2. 敏感操作需要适当的权限验证
3. 定期更新数据库密码
4. 限制数据库访问IP
5. 启用数据库审计日志

## 版本控制

- 当前版本：v1.0.0
- 最后更新：2023-12-01
- 更新内容：初始版本设计