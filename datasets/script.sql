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
    prerequisites TEXT, -- Added back as a text field
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