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
        field_data = {}

        for page in doc:
            widgets = page.widgets()
            if not widgets:
                continue
            for widget in widgets:
                key = widget.field_name.strip() if widget.field_name else None
                val = widget.field_value.strip() if widget.field_value else ""
                if widget.field_type == fitz.PDF_WIDGET_TYPE_BUTTON and widget.field_flags & 32768:
                    # Checkbox handling
                    val = "Yes" if widget.field_value == "Yes" else ""
                if key:
                    field_data[key] = val

        location = field_data.get("AD", "XXXX")

        notam_type = "NOTAMN"
        notam_type_text = field_data.get("NOTAM Type", "New")
        if "Cancel" in notam_type_text:
            notam_type = "NOTAMC"
        elif "Review" in notam_type_text:
            notam_type = "NOTAMR"

        start_date = field_data.get("Start Date", "")
        start_time = field_data.get("Start Time", "")
        finish_date = field_data.get("Finish Date", "")
        finish_time = field_data.get("Finish Time", "")

        # Handle WIE and UFN checkbox overrides
        if field_data.get("WIE") == "Yes":
            b_time = "WIE"
        elif start_date and start_time:
            b_time = f"{start_date}{start_time}"
        else:
            b_time = "YYMMDDHHMM"

        if field_data.get("UFN") == "Yes":
            c_time = "UFN"
        elif finish_date and finish_time:
            c_time = f"{finish_date}{finish_time}"
        else:
            c_time = "YYMMDDHHMM"

        e_text = field_data.get("NOTAM Text", "NOTAM TEXT MISSING")

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
