BEGIN;

DROP TABLE IF EXISTS request_status_history CASCADE;
DROP TABLE IF EXISTS consultation_reminder_logs CASCADE;
DROP TABLE IF EXISTS support_tickets CASCADE;
DROP TABLE IF EXISTS consultation_requests CASCADE;
DROP TABLE IF EXISTS support_categories CASCADE;
DROP TABLE IF EXISTS consultation_slots CASCADE;
DROP TABLE IF EXISTS lesson_reminder_logs CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS assignments CASCADE;
DROP TABLE IF EXISTS subject_resources CASCADE;
DROP TABLE IF EXISTS announcements CASCADE;
DROP TABLE IF EXISTS faq_questions CASCADE;
DROP TABLE IF EXISTS schedules CASCADE;
DROP TABLE IF EXISTS subject_teachers CASCADE;
DROP TABLE IF EXISTS student_subjects CASCADE;
DROP TABLE IF EXISTS college_info CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;
DROP TABLE IF EXISTS user_roles CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS courses CASCADE;

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    telegram_user_id BIGINT UNIQUE,
    active_role TEXT CHECK (active_role IN ('student', 'teacher', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE user_roles (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE courses (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    year_number INTEGER NOT NULL CHECK (year_number BETWEEN 1 AND 6),
    group_code TEXT NOT NULL UNIQUE
);

CREATE TABLE students (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    patronymic TEXT,
    last_name TEXT NOT NULL,
    course_id BIGINT NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    lesson_reminders_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE teachers (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    first_name TEXT NOT NULL,
    patronymic TEXT,
    last_name TEXT NOT NULL,
    office TEXT,
    consultation_notes TEXT
);

CREATE TABLE subjects (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    course_id BIGINT NOT NULL REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE student_subjects (
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id BIGINT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    PRIMARY KEY (student_id, subject_id)
);

CREATE TABLE subject_teachers (
    subject_id BIGINT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    teacher_id BIGINT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    PRIMARY KEY (subject_id, teacher_id)
);

CREATE TABLE schedules (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    teacher_id BIGINT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    course_id BIGINT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    starts_at TIME NOT NULL,
    ends_at TIME NOT NULL,
    room TEXT NOT NULL
);

CREATE TABLE faq_questions (
    id BIGSERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT ''
);

CREATE TABLE announcements (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE subject_resources (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT
);

CREATE TABLE assignments (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    due_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE grades (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id BIGINT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    grade NUMERIC(5,2) NOT NULL CHECK (grade >= 0),
    max_grade NUMERIC(5,2) NOT NULL DEFAULT 100 CHECK (max_grade > 0),
    comment TEXT,
    graded_at DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE lesson_reminder_logs (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    schedule_id BIGINT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    lesson_date DATE NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (student_id, schedule_id, lesson_date)
);

CREATE TABLE consultation_slots (
    id BIGSERIAL PRIMARY KEY,
    teacher_id BIGINT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    slot_date DATE NOT NULL,
    starts_at TIME NOT NULL,
    ends_at TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (teacher_id, slot_date, starts_at)
);

CREATE TABLE consultation_requests (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    teacher_id BIGINT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    consultation_slot_id BIGINT NOT NULL REFERENCES consultation_slots(id) ON DELETE RESTRICT,
    requested_date DATE NOT NULL,
    starts_at TIME NOT NULL,
    ends_at TIME NOT NULL,
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'approved', 'rejected', 'done', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE support_categories (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE support_tickets (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES support_categories(id) ON DELETE RESTRICT,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'in_progress', 'resolved', 'closed', 'cancelled')),
    resolution_comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE request_status_history (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('consultation', 'support')),
    entity_id BIGINT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE consultation_reminder_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL UNIQUE REFERENCES consultation_requests(id) ON DELETE CASCADE,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE college_info (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE INDEX idx_users_telegram_user_id ON users(telegram_user_id);
CREATE UNIQUE INDEX uq_users_normalized_phone ON users (
    regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g')
) WHERE phone IS NOT NULL AND regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g') <> '';
CREATE INDEX idx_roles_code ON roles(code);
CREATE INDEX idx_students_user_id ON students(user_id);
CREATE INDEX idx_teachers_user_id ON teachers(user_id);
CREATE INDEX idx_student_subjects_student_id ON student_subjects(student_id);
CREATE INDEX idx_schedules_course_weekday ON schedules(course_id, weekday);
CREATE INDEX idx_faq_questions_search ON faq_questions USING gin (
    to_tsvector('simple', question || ' ' || answer || ' ' || keywords)
);
CREATE INDEX idx_announcements_course_active ON announcements(course_id, is_active, published_at DESC);
CREATE INDEX idx_assignments_subject_due_date ON assignments(subject_id, due_date);
CREATE INDEX idx_grades_student_subject ON grades(student_id, subject_id);
CREATE INDEX idx_lesson_reminder_logs_student_date ON lesson_reminder_logs(student_id, lesson_date);
CREATE INDEX idx_consultation_slots_teacher_date ON consultation_slots(teacher_id, slot_date, starts_at);
CREATE UNIQUE INDEX uq_active_consultation_slot ON consultation_requests(consultation_slot_id)
WHERE status IN ('new', 'approved');
CREATE INDEX idx_support_categories_active ON support_categories(is_active, name);
CREATE INDEX idx_request_status_history_entity ON request_status_history(entity_type, entity_id, created_at);

COMMIT;
