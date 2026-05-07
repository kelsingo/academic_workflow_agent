-- Core tables for student data
CREATE TABLE advisors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisor_name TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE course_2425 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester TEXT NOT NULL,
    course_code TEXT NOT NULL,
    cross_listed TEXT,
    category TEXT,
    course_name TEXT NOT NULL,
    session_num INTEGER NOT NULL,
    faculty TEXT,
    prerequisites TEXT,
    credits INTEGER NOT NULL
);

CREATE TABLE course_2526 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester TEXT NOT NULL,
    course_code TEXT NOT NULL,
    cross_listed TEXT,
    category TEXT,
    course_name TEXT NOT NULL,
    session_num INTEGER NOT NULL,
    faculty TEXT,
    prerequisites TEXT,
    credits INTEGER NOT NULL
);

CREATE TABLE students (
    student_id INTEGER PRIMARY KEY,
    student_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    advisor_name TEXT,
    credit_available INTEGER NOT NULL,
    FOREIGN KEY (advisor_name) REFERENCES advisors(advisor_name)
);

CREATE TABLE maxcourse_deadline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester TEXT NOT NULL,
    deadline_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS course_load_requests (
    request_id TEXT PRIMARY KEY,
    student_id INTEGER NOT NULL,
    student_name TEXT NOT NULL,
    student_email TEXT NOT NULL,
    advisor_name TEXT,
    advisor_email TEXT,
    courses TEXT NOT NULL,
    reason TEXT,
    plan TEXT,
    credit_required INTEGER,
    status TEXT NOT NULL DEFAULT 'pending_advisor',
    advisor_decision TEXT,
    advisor_reason TEXT,
    registrar_decision TEXT,
    registrar_reason TEXT,
    submitted_at TEXT NOT NULL,
    advisor_deadline TEXT,
    last_updated TEXT NOT NULL,
    notify_push INTEGER NOT NULL DEFAULT 0
);