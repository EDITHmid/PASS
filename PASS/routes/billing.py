"""Billing (Invoice) management routes for the ERP.
Provides list, create, and edit functionality for student fees.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..models import db, Invoice, Student
from ..decorators import role_required

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/')
@login_required
@role_required(['admin', 'principal', 'finance'])
def list_invoices():
    invoices = Invoice.query.order_by(Invoice.due_date.asc()).all()
    return render_template('billing/list.html', invoices=invoices)

@billing_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal', 'finance'])
def create_invoice():
    if request.method == 'POST':
        inv = Invoice(
            student_id=request.form['student_id'],
            amount=float(request.form['amount']),
            due_date=request.form['due_date'],
            paid=('paid' in request.form)
        )
        db.session.add(inv)
        db.session.commit()
        flash('Invoice created', 'success')
        return redirect(url_for('billing.list_invoices'))
    students = Student.query.all()
    return render_template('billing/form.html', invoice=None, students=students)

@billing_bp.route('/<int:inv_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal', 'finance'])
def edit_invoice(inv_id):
    inv = Invoice.query.get_or_404(inv_id)
    if request.method == 'POST':
        inv.student_id = request.form['student_id']
        inv.amount = float(request.form['amount'])
        inv.due_date = request.form['due_date']
        inv.paid = ('paid' in request.form)
        db.session.commit()
        flash('Invoice updated', 'success')
        return redirect(url_for('billing.list_invoices'))
    students = Student.query.all()
    return render_template('billing/form.html', invoice=inv, students=students)
