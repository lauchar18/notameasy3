from flask import Flask, request, render_template_string
import pytesseract
from pdf2image import convert_from_path
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
        images = convert_from_path(pdf_path)
        text = pytesseract.image_to_string(images[0])

        ad_match = re.search(r"AD\s*[:\-]?\s*([A-Z]{4})", text)
        location = ad_match.group(1) if ad_match else "XXXX"

        notam_type = "NOTAMN"
        if "NOTAM R" in text:
            notam_type = "NOTAMR"
        elif "NOTAM C" in text:
            notam_type = "NOTAMC"

        b_match = re.search(r"Item B.*?(\d{6})\s*(\d{4})", text)
        c_match = re.search(r"Item C.*?(\d{6})\s*(\d{4})", text)
        b_time = f"{b_match.group(1)}{b_match.group(2)}" if b_match else "YYMMDDHHMM"
        c_time = f"{c_match.group(1)}{c_match.group(2)}" if c_match else "YYMMDDHHMM"

        e_match = re.search(r"Item E\).*?\n(.*?)\n", text, re.DOTALL)
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
