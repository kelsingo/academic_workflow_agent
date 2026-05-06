"""
Check eligibilities of students
"""

import sqlite3
import os
from datetime import datetime
from .data_adapter import save_status
from .data_adapter import save_maxcourse_info, load_deadline, load_all_data, load_course_availability, load_credits_required

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'datasets', 'fuv_data.db'))
current_semester = 'Spring 2026'  
current_course_offerings = 'course_2526'

def eligible_check(data):
    load_all_data(data)

    unavailable_courses = load_course_availability(data['course_code'])
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


if __name__ == "__main__":
    data = {
        'student_id': 25372,
        'course_code': ['CS101', 'CS400'],
        'reason': 'Fulfill graduation requirements',
        'plan': 'Spend extra time on coursework and seek support from instructor and Academic Affairs when needed.'
    }
    print(eligible_check(data))
    