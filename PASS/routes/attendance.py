"""Attendance management routes for the ERP.
Provides list, add, and edit functionality.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..models import db, Attendance, Student
from ..decorators import role_required

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/')
@login_required
@role_required(['admin', 'principal', 'teacher'])
def list_attendance():
    records = Attendance.query.order_by(Attendance.date.desc()).all()
    return render_template('attendance/list.html', records=records)

@attendance_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal', 'teacher'])
def add_attendance():
    if request.method == 'POST':
        rec = Attendance(
            student_id=request.form['student_id'],
            date=request.form['date'],
            status=request.form['status']
        )
        db.session.add(rec)
        db.session.commit()
        flash('Attendance recorded', 'success')
        return redirect(url_for('attendance.list_attendance'))
    students = Student.query.all()
    return render_template('attendance/form.html', record=None, students=students)

@attendance_bp.route('/<int:rec_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal', 'teacher'])
def edit_attendance(rec_id):
    rec = Attendance.query.get_or_404(rec_id)
    if request.method == 'POST':
        rec.student_id = request.form['student_id']
        rec.date = request.form['date']
        rec.status = request.form['status']
        db.session.commit()
        flash('Attendance updated', 'success')
        return redirect(url_for('attendance.list_attendance'))
    students = Student.query.all()
    return render_template('attendance/form.html', record=rec, students=students)
