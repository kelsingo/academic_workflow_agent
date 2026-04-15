import sqlite3
import os
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'datasets', 'fuv_data.db'))


def eligible_check(data):
    load_all_data(data)
    if data['credit_available'] >= data['credit_required']:
        return True  # eligible
    else:
        return False # not eligible

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
        cur.execute('''
            SELECT credits
            FROM course_2425
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
        'course_code': ['CS101', 'MATH202'],
        'reason': 'Fulfill graduation requirements',
        'plan': 'Spend extra time on coursework and seek support from instructor and Academic Affairs when needed.'
    }
    print(eligible_check(data))
    