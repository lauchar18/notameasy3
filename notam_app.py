from flask import Flask, request, render_template_string
import fitz  # PyMuPDF
import re
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FIR_MAP = {
    "YSSY": "YMMM", "YSCB": "YMMM", "YBAS": "YMMM", "YMML": "YMMM", "YPAD": "YMMM",
    "YMHB": "YMMM", "YMLT": "YMMM", "YARM": "YMMM", "YBHI": "YMMM", "YPPF": "YMMM",
    "YWLM": "YMMM", "YMMB": "YMMM", "YSBK": "YMMM", "YHSM": "YMMM", "YMTG": "YMMM",
    "YCOM": "YMMM", "YCNK": "YMMM", "YWLU": "YMMM", "YSNW": "YMMM", "YWLG": "YMMM",
    "YSHW": "YMMM", "YSRI": "YMMM", "YSWG": "YMMM", "YBTH": "YMMM", "YHOT": "YMMM",
    "YWYY": "YMMM", "YSDU": "YMMM", "YORG": "YMMM", "YMAY": "YMMM", "YPPH": "YMMM",
    "YPJT": "YMMM", "YPKG": "YMMM", "YBKE": "YMMM", "YBUN": "YMMM", "YPLM": "YMMM",
    "YBBN": "YBBB", "YBCG": "YBBB", "YBTL": "YBBB", "YBNA": "YBBB", "YBPN": "YBBB",
    "YBAF": "YBBB", "YBWW": "YBBB", "YBCS": "YBBB", "YBSU": "YBBB", "YBMA": "YBBB",
    "YBMC": "YBBB", "YBOK": "YBBB", "YBHM": "YBBB", "YBTR": "YBBB", "YBCV": "YBBB",
    "YBRK": "YBBB", "YBGD": "YBBB", "YGLA": "YBBB", "YGTN": "YBBB", "YMTI": "YBBB",
    "YBTG": "YBBB", "YBPI": "YBBB", "YBUD": "YBBB", "YWDH": "YBBB", "YWCK": "YBBB"
}

q_code_mapping = {
    "RUNWAY CLOSED": "QMRLC", "RWY CLOSED": "QMRLC", "RWY CLSD": "QMRLC",
    "RUNWAY WORK IN PROGRESS": "QMRXX", "RWY WIP": "QMRXX",
    "TAXIWAY CLOSED": "QMXLC", "TWY CLOSED": "QMXLC", "TWY CLSD": "QMXLC",
    "APRON CLOSED": "QMALC",
    "ILS U/S": "QLIAS", "VOR U/S": "QLVAS", "NDB U/S": "QLNAS",
    "NAVIGATION AID UNAVAILABLE": "QNAVU",
    "RUNWAY LIGHTING FAILED": "QLRLC", "RWY LIGHT FAIL": "QLRLC",
    "TWY LIGHT FAIL": "QLTLC", "APRON LIGHT FAIL": "QLALC",
    "CRANE": "QOBCE", "OBSTACLE": "QOBCE",
    "RADIO FAILURE": "QCAAS", "FREQUENCY UNAVAILABLE": "QCAAS",
    "WORK IN PROGRESS": "QMXLC", "WIP": "QMXLC",
    "DEFAULT": "QXXXX"
}

def detect_q_code(e_field_text):
    text = e_field_text.upper()
    for phrase, q_code in q_code_mapping.items():
        if phrase in text:
            return q_code
    return q_code_mapping["DEFAULT"]

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    notam_text = ""
    q_code = ""
    contact_info = ""
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            notam_text, q_code, contact_info = extract_notam_from_pdf(file_path)

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
            </div>
            <div style="width: 30%;">
                <h3>Contact Details:</h3>
                <pre>{{ contact_info }}</pre>
            </div>
        </div>
    ''', notam_text=notam_text, q_code=q_code, contact_info=contact_info)

def extract_notam_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        field_data = {}

        for page in doc:
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    key = widget.field_name.strip() if widget.field_name else None
                    val = widget.field_value.strip() if widget.field_value else ""
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_BUTTON and widget.field_flags & 32768:
                        val = "Yes" if widget.field_value == "Yes" else ""
                    if key:
                        field_data[key] = val

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
        q_code = detect_q_code(e_text)

        # Combine form values with final page text
        contact_lines = []
        for key in ["Contact Name", "Phone Number", "Email", "Organisation"]:
            val = field_data.get(key, "")
            if val and not set(val) <= {"_", " "}:
                contact_lines.append(f"{key}: {val}")

        # Extract any useful info from final page
        last_page = doc[-1].get_text()
        for line in last_page.splitlines():
            if ("contact" in line.lower() or "phone" in line.lower() or "email" in line.lower()) \
                and not re.fullmatch(r"_+", line.strip()) \
                and "automatic email" not in line.lower():
                contact_lines.append(line.strip())

        contact_info = "\n".join(contact_lines)

        notam = f"""
B0001/25 {notam_type}
Q) {fir_code}/{q_code}/IV/NBO/A/000/999/0000S00000E005
A) {location}
B) {b_time}
C) {c_time}
E) {e_text}
"""
        return notam, q_code, contact_info
    except Exception as e:
        return f"Error processing PDF: {e}", "", ""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
