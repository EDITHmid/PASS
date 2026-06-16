"""Grade management routes for the ERP.
Provides CRUD for student grades.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..models import db, Grade, Student
from ..decorators import role_required

grade_bp = Blueprint('grade', __name__, url_prefix='/grades')

@grade_bp.route('/')
@login_required
@role_required(['admin', 'principal', 'teacher'])
def list_grades():
    grades = Grade.query.order_by(Grade.student_id).all()
    return render_template('grades/list.html', grades=grades)

@grade_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal', 'teacher'])
def create_grade():
    if request.method == 'POST':
        g = Grade(
            student_id=request.form['student_id'],
            subject=request.form['subject'],
            score=float(request.form['score'])
        )
        db.session.add(g)
        db.session.commit()
        flash('Grade added', 'success')
        return redirect(url_for('grade.list_grades'))
    students = Student.query.all()
    return render_template('grades/form.html', grade=None, students=students)

@grade_bp.route('/<int:grade_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal', 'teacher'])
def view_grade(grade_id):
    grade = Grade.query.get_or_404(grade_id)
    if request.method == 'POST':
        grade.subject = request.form['subject']
        grade.score = float(request.form['score'])
        db.session.commit()
        flash('Grade updated', 'success')
        return redirect(url_for('grade.list_grades'))
    students = Student.query.all()
    return render_template('grades/form.html', grade=grade, students=students)
