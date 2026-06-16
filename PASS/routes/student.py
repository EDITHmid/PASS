"""Student management routes for the ERP.
These routes extend the original PASS dashboards with full CRUD
operations and expose the PASS risk widget on the profile page.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Student, ContactInfo, Enrollment
from decorators import role_required

student_bp = Blueprint('student', __name__, url_prefix='/students')

@student_bp.route('/')
@login_required
@role_required(['admin', 'principal', 'teacher'])
def list_students():
    q = request.args.get('q', '')
    students = Student.query.filter(
        (Student.first_name.ilike(f"%{q}%")) |
        (Student.last_name.ilike(f"%{q}%"))
    ).order_by(Student.last_name).all()
    return render_template('students/list.html', students=students, query=q)

@student_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal'])
def create_student():
    if request.method == 'POST':
        stud = Student(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            dob=request.form['dob'],
            gender=request.form.get('gender')
        )
        db.session.add(stud)
        db.session.flush()  # get id before commit
        ci = ContactInfo(
            student_id=stud.id,
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address')
        )
        db.session.add(ci)
        db.session.commit()
        flash('Student created', 'success')
        return redirect(url_for('student.list_students'))
    return render_template('students/form.html', student=None)

@student_bp.route('/<int:stu_id>')
@login_required
@role_required(['admin', 'principal', 'teacher', 'parent'])
def view_student(stu_id):
    stud = Student.query.get_or_404(stu_id)
    # PASS score – the helper lives on the model
    try:
        pass_score = stud.get_pass_score()
    except Exception:
        pass_score = None
    return render_template('students/profile.html', student=stud, pass_score=pass_score)
