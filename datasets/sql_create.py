import pandas as pd
import sqlite3

# Load dataframes
advisors_df = pd.read_csv('advisor_dataset.csv')
courses_df = pd.read_csv('course2425_dataset.csv')
students_df = pd.read_csv('student_dataset.csv')
deadlines_df = pd.read_csv('deadline_dataset.csv')
courses_2526_df = pd.read_csv('course2526_dataset.csv')

# Pre-processing
deadlines_df['deadline'] = pd.to_datetime(deadlines_df['deadline'], dayfirst=True).dt.strftime('%Y-%m-%d')
courses_df['Faculty'] = courses_df['Faculty'].fillna('Unknown')
courses_df['Category'] = courses_df['Category'].fillna('')
courses_df['Cross-listed'] = courses_df['Cross-listed'].fillna('')
courses_df['Pre-requisite'] = courses_df['Pre-requisite'].fillna('')

courses_2526_df['Faculty'] = courses_2526_df['Faculty'].fillna('Unknown')
courses_2526_df['Category'] = courses_2526_df['Category'].fillna('')
courses_2526_df['Cross-listed'] = courses_2526_df['Cross-listed'].fillna('')
courses_2526_df['Pre-requisite'] = courses_2526_df['Pre-requisite'].fillna('')

# Initialize SQLite connection
conn = sqlite3.connect('fuv_data.db')
cursor = conn.cursor()

# 1. Create Tables
cursor.execute("DROP TABLE IF EXISTS students")
cursor.execute("DROP TABLE IF EXISTS course_2425")
cursor.execute("DROP TABLE IF EXISTS course_2526")
cursor.execute("DROP TABLE IF EXISTS advisors")
cursor.execute("DROP TABLE IF EXISTS maxcourse_deadline")

cursor.execute('''
CREATE TABLE advisors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisor_name TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL
)''')

cursor.execute('''
CREATE TABLE course_2425 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester TEXT NOT NULL,
    course_code TEXT NOT NULL,
    cross_listed TEXT,
    category TEXT,
    course_name TEXT NOT NULL,
    session_num INTEGER NOT NULL,
    faculty TEXT,
    prerequisite TEXT,
    credits INTEGER NOT NULL
)''')

cursor.execute('''
CREATE TABLE course_2526 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester TEXT NOT NULL,
    course_code TEXT NOT NULL,
    cross_listed TEXT,
    category TEXT,
    course_name TEXT NOT NULL,
    session_num INTEGER NOT NULL,
    faculty TEXT,
    prerequisite TEXT,
    credits INTEGER NOT NULL
)''')

cursor.execute('''
CREATE TABLE students (
    student_id INTEGER PRIMARY KEY,
    student_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    advisor_name TEXT,
    credit_available INTEGER NOT NULL,
    FOREIGN KEY (advisor_name) REFERENCES advisors(advisor_name)
)''')

cursor.execute('''
CREATE TABLE maxcourse_deadline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester TEXT NOT NULL,
    deadline_date TEXT NOT NULL
)''')

# 2. Insert Data
advisors_df.to_sql('advisors', conn, if_exists='append', index=False)

courses_to_db = courses_df.rename(columns={
    'Semester': 'semester',
    'Course Code': 'course_code',
    'Cross-listed': 'cross_listed',
    'Category': 'category',
    'Course Name': 'course_name',
    'Session #': 'session_num',
    'Faculty': 'faculty',
    'Pre-requisite': 'prerequisite',
    'Credits': 'credits'
})
courses_to_db.to_sql('course_2425', conn, if_exists='append', index=False)
courses_2526_to_db = courses_2526_df.rename(columns={
    'Semester': 'semester',
    'Course Code': 'course_code',
    'Cross-listed': 'cross_listed',
    'Category': 'category',
    'Course Name': 'course_name',
    'Session #': 'session_num',
    'Faculty': 'faculty',
    'Pre-requisite': 'prerequisite',
    'Credits': 'credits'
})
courses_2526_to_db.to_sql('course_2526', conn, if_exists='append', index=False)

students_to_db = students_df.rename(columns={
    'advisor': 'advisor_name',
    'credit_availability': 'credit_available'
})
students_to_db.to_sql('students', conn, if_exists='append', index=False)

deadlines_to_db = deadlines_df.rename(columns={
    'semester': 'semester',
    'deadline': 'deadline_date'
})
deadlines_to_db.to_sql('maxcourse_deadline', conn, if_exists='append', index=False)

conn.commit()
conn.close()

print("Database 'fuv_data.db' created successfully with simplified structure.")