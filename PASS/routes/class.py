"""Class and schedule management routes for the ERP.
Provides CRUD for classes and a simple calendar view for schedules.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Class, Teacher, Schedule, Enrollment
from decorators import role_required

class_bp = Blueprint('class', __name__, url_prefix='/classes')

@class_bp.route('/')
@login_required
@role_required(['admin', 'principal'])
def list_classes():
    classes = Class.query.order_by(Class.year.desc()).all()
    return render_template('classes/list.html', classes=classes)

@class_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal'])
def create_class():
    if request.method == 'POST':
        cls = Class(
            name=request.form['name'],
            year=int(request.form['year']),
            teacher_id=request.form.get('teacher_id') or None,
        )
        db.session.add(cls)
        db.session.commit()
        flash('Class created', 'success')
        return redirect(url_for('class.list_classes'))
    teachers = Teacher.query.all()
    return render_template('classes/form.html', cls=None, teachers=teachers)

@class_bp.route('/<int:cls_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal', 'teacher'])
def view_class(cls_id):
    cls = Class.query.get_or_404(cls_id)
    if request.method == 'POST':
        cls.name = request.form['name']
        cls.year = int(request.form['year'])
        cls.teacher_id = request.form.get('teacher_id') or None
        db.session.commit()
        flash('Class updated', 'success')
        return redirect(url_for('class.view_class', cls_id=cls.id))
    teachers = Teacher.query.all()
    enrollments = Enrollment.query.filter_by(class_id=cls.id).all()
    return render_template('classes/profile.html', cls=cls, teachers=teachers, enrollments=enrollments)
