# UPDATE: Load and query data from existing database tables

from datetime import datetime
import os
import sqlite3

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'datasets', 'fuv_data.db'))
current_semester = 'Spring 2026'  
current_course_offerings = 'course_2526'


def load_deadline(current_semester):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    cur.execute('''
        SELECT deadline_date
        FROM maxcourse_deadline
        WHERE semester = ?
    ''', (current_semester,))
    
    result = cur.fetchone()
    con.close()
    
    if result:
        return datetime.strptime(result[0], "%Y-%m-%d").date()
    else:
        return None


def load_student_data(student_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    cur.execute('''
        SELECT student_name, email, advisor_name, credit_available
        FROM students 
        WHERE student_id = ?
    ''', (student_id,))
    
    result = cur.fetchone()
    con.close()
    
    if result:
        student_name, email, advisor_name, credit_available = result
        return {
            'student_name': student_name,
            'email': email,
            'advisor_name': advisor_name,
            'credit_available': credit_available,
        }
    else:
        return None


def load_credits_required(courses):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    result = [] 
    for course in courses:
        cur.execute(f'''
            SELECT credits
            FROM {current_course_offerings} 
            WHERE course_code = ? OR course_name = ?
        ''', (course, course))
        row = cur.fetchone()
        if row is not None:
            result.append(row[0])
    con.close()
    
    if result:
        credits = sum(result)
        return credits
    else:
        return None


def load_course_availability(courses):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    result = []
    for course in courses:
        cur.execute(f'''
            SELECT *
            FROM {current_course_offerings}
            WHERE course_code = ? OR course_name = ?
        ''', (course, course))
        if cur.fetchone() is None:
            result.append(course)
    con.close()
    if result:
        return result
    else:
        return None
