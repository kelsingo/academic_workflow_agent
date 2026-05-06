# Currently only save data, will refactor to add load data func in the future 

import json
import os
import sqlite3

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'datasets', 'fuv_data.db'))
current_semester = 'Spring 2026'  
current_course_offerings = 'course_2526'

#  SAVE DATA TO SQL DATABASE
def save_status(student_id, status, request_id): 
    """
    Save the status of the student request to SQL database. 
    Statuses: 
    - idle: The student has not made any request yet.
    - collecting: waiting for student to enter course IDs/reason/plan
    - checking: eligibility animation running (automated)
    - advisor_wait: advisor_wait	Request submitted, polling for advisor reply
    - registrar_wait: Advisor approved, polling for registrar reply
    - done: final outcome shown
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('''
        INSERT INTO requests (student_id, status, request_type_id)
        VALUES (?, ?, ?)
        ON CONFLICT(student_id) DO UPDATE SET status=excluded.status, request_type_id=excluded.request_type_id
    ''', (student_id, status, request_id))
    con.commit()
    con.close()

def update_status(student_id, new_status):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('''
        UPDATE requests
        SET status = ?
        WHERE student_id = ?
    ''', (new_status, student_id))
    con.commit()
    con.close()

def save_maxcourse_info(course_ids, reason, plan):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    for id in course_ids:
        course_id_1 = id[0]
        course_id_2 = id[1] 
        course_id_3 = id[2]
        course_id_4 = id[3]
        course_id_5 = id[4]    
    cur.execute('''
        INSERT INTO maxcourse_requests (course_id_1, course_id_2, course_id_3, course_id_4, course_id_5, reason, plan)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (course_id_1, course_id_2, course_id_3, course_id_4, course_id_5, reason, plan))
    con.commit()
    con.close()

def update_maxcourse_info(student_id, course_ids=None, reason=None, plan=None):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    if course_ids is not None:
        cur.execute('''
            UPDATE maxcourse_requests
            SET course_id_1 = ?, course_id_2 = ?, course_id_3 = ?, course_id_4 = ?, course_id_5 = ?
            WHERE student_id = ?
        ''', (course_ids[0], course_ids[1], course_ids[2], course_ids[3], course_ids[4], student_id))
    
    if reason is not None:
        cur.execute('''
            UPDATE maxcourse_requests
            SET reason = ?
            WHERE student_id = ?
        ''', (reason, student_id))
    
    if plan is not None:
        cur.execute('''
            UPDATE maxcourse_requests
            SET plan = ?
            WHERE student_id = ?
        ''', (plan, student_id))
    
    con.commit()
    con.close()

#  LOAD DATA FROM SQL DATABASE
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

def load_maxcourse_status(student_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('''
        SELECT status
        FROM maxcourse_requests
        WHERE student_id = ?
    ''', (student_id,))
    result = cur.fetchone()
    con.close()
    if result:
        return result[0]
    else:
        return None
