from flask import Flask, request, render_template_string
import fitz  # PyMuPDF
import re
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    notam_text = ""
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            notam_text = extract_notam_from_pdf(file_path)

    return render_template_string("""
        <h2>Upload NOTAM Request PDF</h2>
        <form method='post' enctype='multipart/form-data'>
            <input type='file' name='file'>
            <input type='submit' value='Upload'>
        </form>
        <pre>{{ notam_text }}</pre>
    """, notam_text=notam_text)

def extract_notam_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        field_texts = []
        for page in doc:
            for widget in page.widgets():
                if widget.field_name and widget.field_value:
                    field_texts.append(f"{widget.field_name.strip()}: {widget.field_value.strip()}")
        text = "\n".join(field_texts)

        ad_match = re.search(r"AD:\s*([A-Z]{4})", text)
        location = ad_match.group(1) if ad_match else "XXXX"

        notam_type = "NOTAMN"
        if re.search(r"NOTAM Type:\s*Cancel", text):
            notam_type = "NOTAMC"
        elif re.search(r"NOTAM Type:\s*Review", text):
            notam_type = "NOTAMR"

        b_match = re.search(r"Start Date:\s*(\d{6})\s*Start Time:\s*(\d{4})", text)
        c_match = re.search(r"Finish Date:\s*(\d{6})\s*Finish Time:\s*(\d{4})", text)
        b_time = f"{b_match.group(1)}{b_match.group(2)}" if b_match else "YYMMDDHHMM"
        c_time = f"{c_match.group(1)}{c_match.group(2)}" if c_match else "YYMMDDHHMM"

        e_match = re.search(r"NOTAM Text:\s*(.*?)\n", text)
        e_text = e_match.group(1).strip() if e_match else "NOTAM TEXT MISSING"

        notam = f"""\nB0001/25 {notam_type}
Q) {location}/QXXXX/IV/NBO/A/000/999/0000S00000E005
A) {location}
B) {b_time}
C) {c_time}
E) {e_text}
"""
        return notam
    except Exception as e:
        return f"Error processing PDF: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
