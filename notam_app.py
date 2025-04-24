from flask import Flask, request, render_template_string
import fitz  # PyMuPDF
import re
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FIR_MAP = { ... }  # Keep existing FIR map from your version
q_code_mapping = { ... }  # Keep existing Q-code map from your version

def detect_q_code(e_field_text):
    text = e_field_text.upper()
    for phrase, q_code in q_code_mapping.items():
        if phrase in text:
            return q_code, phrase  # return reason phrase too
    return q_code_mapping["DEFAULT"], "No specific match"

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    notam_text = ""
    q_code = ""
    reason = ""
    contact_info = ""
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            notam_text, q_code, reason, contact_info = extract_notam_from_pdf(file_path)

    return render_template_string('''
        <h2>Upload NOTAM Request PDF</h2>
        <form method='post' enctype='multipart/form-data'>
            <input type='file' name='file'>
            <input type='submit' value='Upload'>
        </form>
        <div style="display: flex; gap: 20px;">
            <div style="width: 70%;">
                <h3>Generated NOTAM:</h3>
                <pre>{{ notam_text }}</pre>
                <h4>Q-code Selected: {{ q_code }}</h4>
                <p><strong>Reason:</strong> {{ reason }}</p>
            </div>
            <div style="width: 30%;">
                <h3>Contact Details:</h3>
                <pre>{{ contact_info }}</pre>
            </div>
        </div>
    ''', notam_text=notam_text, q_code=q_code, reason=reason, contact_info=contact_info)

def extract_notam_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        field_data = {}
        last_page_text = ""

        for i, page in enumerate(doc):
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    key = widget.field_name.strip() if widget.field_name else None
                    val = widget.field_value.strip() if widget.field_value else ""
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_BUTTON and widget.field_flags & 32768:
                        val = "Yes" if widget.field_value == "Yes" else ""
                    if key:
                        field_data[key] = val
            if i == len(doc) - 1:
                last_page_text = page.get_text()

        location = field_data.get("AD", "XXXX")
        fir_code = FIR_MAP.get(location, "XXXX")

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
        q_code, reason = detect_q_code(e_text)

        contact_info = "\n".join([line.strip() for line in last_page_text.splitlines() if "contact" in line.lower() or "phone" in line.lower() or "email" in line.lower()])

        notam = f"""
B0001/25 {notam_type}
Q) {fir_code}/{q_code}/IV/NBO/A/000/999/0000S00000E005
A) {location}
B) {b_time}
C) {c_time}
E) {e_text}
"""
        return notam, q_code, reason, contact_info
    except Exception as e:
        return f"Error processing PDF: {e}", "", "", ""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
