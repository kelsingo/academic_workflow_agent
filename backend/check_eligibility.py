"""
Check eligibilities of students
"""

import os
from datetime import datetime
from .data_adapter import load_deadline, load_course_availability, load_credits_required, load_student_data

BASE_DIR = os.path.dirname(__file__)
current_semester = 'Spring 2026'  

def eligible_check(data):
    # data: dict with 'student_id' and 'course_ids'
    # Return: True if eligible, False if insufficient credits, or error string

    student_id = data.get('student_id')
    course_ids = data.get('course_ids', [])
    
    # Load student info
    student = load_student_data(student_id)
    if not student:
        return f"Student ID {student_id} not found in database."
    
    credit_available = student.get('credit_available', 0)
    
    # Check course availability
    unavailable_courses = load_course_availability(course_ids)
    if unavailable_courses:
        return f"Course(s) {unavailable_courses} not available for this semester. Please re-check the course information."

    # Check deadline
    deadline = load_deadline(current_semester)
    if deadline is None:
        return "Courses for this semester are not available."
    elif deadline < datetime.today().date():
        return "The deadline for course registration has passed."

    # Calculate required credits
    credit_required = load_credits_required(course_ids) or 0
    
    # Check if student has enough available credits
    if credit_available >= credit_required:
        return True  # eligible
    else:
        return False # not eligible


if __name__ == "__main__":
    data = {
        'student_id': 25372,
        'course_ids': ['CS101', 'CS400'],
        'reason': 'Fulfill graduation requirements',
        'plan': 'Spend extra time on coursework and seek support from instructor and Academic Affairs when needed.'
    }
    print(eligible_check(data))
    