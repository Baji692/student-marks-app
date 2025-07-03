from flask import Flask, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import os
import io
import json

app = Flask(__name__)

# PostgreSQL connection (Render or local fallback)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:yourpassword@localhost:5432/studentmarks'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Result table definition
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100))
    subject_data = db.Column(db.Text)  # JSON string
    total = db.Column(db.Integer)
    max_total = db.Column(db.Integer)
    percentage = db.Column(db.Float)
    grade = db.Column(db.String(50))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    name = request.form['name']
    num_subjects = int(request.form['num_subjects'])

    subjects = []
    total = 0
    max_total = 0
    failed_subjects = []

    for i in range(1, num_subjects + 1):
        subject_name = request.form.get(f"subject_name_{i}")
        mark = int(request.form.get(f"subject_mark_{i}"))
        max_mark = int(request.form.get(f"subject_max_{i}"))
        total += mark
        max_total += max_mark
        if mark < 35:
            failed_subjects.append(subject_name)
        subjects.append((subject_name, mark, max_mark))

    percentage = (total / max_total) * 100

    if percentage >= 90:
        grade = 'A+ (Outstanding)'
    elif percentage >= 80:
        grade = 'A (Excellent)'
    elif percentage >= 70:
        grade = 'B (Good)'
    elif percentage >= 60:
        grade = 'C (Average)'
    elif percentage >= 50:
        grade = 'D (Pass)'
    else:
        grade = 'F (Fail)'

    feedback = (
        "🎉 Excellent performance!" if percentage >= 85 else
        "📈 You're on track, keep going!" if percentage >= 65 else
        "⚠️ You can do better next time."
    )

    # Save to PostgreSQL
    db.session.add(Result(
        student_name=name,
        subject_data=json.dumps(subjects),
        total=total,
        max_total=max_total,
        percentage=round(percentage, 2),
        grade=grade
    ))
    db.session.commit()

    return render_template(
        'result.html',
        name=name,
        subjects=subjects,
        total=total,
        max_total=max_total,
        percentage=round(percentage, 2),
        grade=grade,
        feedback=feedback,
        failed_subjects=failed_subjects
    )

@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    try:
        name = request.form['name']
        subjects = json.loads(request.form['subjects'])
        total = request.form['total']
        max_total = request.form['max_total']
        percentage = request.form['percentage']
        grade = request.form['grade']

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=16)
        pdf.cell(0, 10, f"Result for {name}", ln=True, align='C')
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(80, 10, "Subject", 1, 0, 'C', True)
        pdf.cell(55, 10, "Marks Obtained", 1, 0, 'C', True)
        pdf.cell(55, 10, "Max Marks", 1, 1, 'C', True)

        pdf.set_font("Arial", '', 12)
        for subject_name, obtained, max_marks in subjects:
            pdf.cell(80, 10, subject_name, 1)
            pdf.cell(55, 10, str(obtained), 1, 0, 'C')
            pdf.cell(55, 10, str(max_marks), 1, 1, 'C')

        pdf.set_fill_color(200, 245, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(80, 10, "Total", 1, 0, 'C', True)
        pdf.cell(55, 10, str(total), 1, 0, 'C', True)
        pdf.cell(55, 10, str(max_total), 1, 1, 'C', True)

        pdf.set_fill_color(210, 245, 225)
        pdf.cell(80, 10, "Percentage", 1, 0, 'C', True)
        pdf.cell(110, 10, f"{percentage}%", 1, 1, 'C', True)

        pdf.set_fill_color(255, 255, 200)
        pdf.cell(80, 10, "Grade", 1, 0, 'C', True)
        pdf.cell(110, 10, grade, 1, 1, 'C', True)

        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        pdf_output = io.BytesIO(pdf_bytes)
        pdf_output.seek(0)

        return send_file(pdf_output, download_name=f"{name}_Result.pdf", as_attachment=True)

    except Exception as e:
        print("PDF Export Error:", e)
        return f"An error occurred while generating the PDF: {e}", 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
