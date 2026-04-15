import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'datasets', 'fuv_data.db'))
current_semester = 'Fall 2026'  
current_course_offerings = 'course_2526'

def eligible_check(data):
    load_all_data(data)

    unavailable_courses = check_course_availability(data['course_code'])
    if unavailable_courses:
        return f"Course(s) {unavailable_courses} not available for this semester. Please re-check the course information."

    deadline = load_deadline(current_semester)
    if deadline is None:
        return "Courses for this semester are not available."
    elif deadline < datetime.today().strftime('%Y-%m-%d'):
        return "The deadline for course registration has passed."

    if data['credit_available'] >= data['credit_required']:
        return True  # eligible
    
    else:
        return False # not eligible

def check_course_availability(courses):
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
        return datetime.strptime(result[0], "%Y-%m-%d").date()
    else:
        return None

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
        return result[0]
    else:
        return None

def load_all_data(data):
    student_id = data['student_id']
    student_data = load_student_data(student_id)
    if 'course_code' in data:
        courses = data['course_code']
        credits = load_credits_required(courses)
    elif 'course_name' in data:
        courses = data['course_name']
        credits = load_credits_required(courses)
    else:
        return "Course information missing"

    data.update(student_data)
    data['credit_required'] = credits
    return data 


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
    
        result.append(cur.fetchone()[0])
    con.close()
    
    if result:
        credits = sum(result)
        return credits
    else:
        return None


if __name__ == "__main__":
    data = {
        'student_id': 25372,
        'course_code': ['CS101', 'CS103'],
        'reason': 'Fulfill graduation requirements',
        'plan': 'Spend extra time on coursework and seek support from instructor and Academic Affairs when needed.'
    }
    print(eligible_check(data))
    