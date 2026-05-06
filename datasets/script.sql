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

CREATE TABLE request_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_type TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE statuses (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
);

CREATE TABLE requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    request_type_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(student_id) REFERENCES students(student_id),
    FOREIGN KEY(request_type_id) REFERENCES request_types(id),
    FOREIGN KEY(status_id) REFERENCES statuses(id)
);

CREATE TABLE maxcourse_requests (
    request_id INTEGER PRIMARY KEY,
    course_code_1 TEXT NOT NULL,
    course_code_2 TEXT NOT NULL, 
    course_code_3 TEXT NOT NULL,
    course_code_4 TEXT NOT NULL,
    course_code_5 TEXT NOT NULL,
    plan TEXT NOT NULL,
    reason TEXT NOT NULL,

    FOREIGN KEY(request_id) REFERENCES requests(id)
);