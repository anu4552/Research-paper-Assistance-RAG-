#  app.py – Backend Ollama Summary + DOCX + PDF

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os, uuid, re, requests, traceback, base64
from jinja2 import Template
from markupsafe import Markup
from weasyprint import HTML
from docx import Document
from docx.shared import Inches

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
TEMPLATE_PATH = "preview.html"
PROMPT_PATH = "prompt_template.txt"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load HTML template on startup
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html_template = Template(f.read())

# Load prompt template
with open(PROMPT_PATH, "r") as f:
    prompt_template = f.read()

def generate_summary(data):
    prompt = prompt_template.format(**data)
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "deepseek-r1:1.5b",
        "prompt": prompt,
        "temperature": 0, 
        "stream": False
    })
    if response.status_code != 200:
        raise Exception(f"Ollama error: {response.status_code}: {response.text}")

    summary = response.json().get("response", "").strip()
    summary = re.sub(r"<think>.*?</think>", "", summary, flags=re.DOTALL)
    summary = re.sub(r"\**Summary\**:?", "", summary, flags=re.IGNORECASE).strip()
    return summary

def save_base64_image(base64_data):
    header, encoded = base64_data.split(",", 1)
    ext = header.split("/")[1].split(";")[0]
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, "wb") as f:
        f.write(base64.b64decode(encoded))
    return filepath

@app.route("/generate-preview", methods=["POST"])
def generate_preview():
    try:
        data = request.form.to_dict()
        photo_url = data.get("PHOTO_URL")

        if not photo_url:
            photo = request.files.get("photo")
            if photo:
                photo_ext = photo.filename.split(".")[-1]
                photo_filename = f"{uuid.uuid4().hex}.{photo_ext}"
                photo_path = os.path.join(UPLOAD_FOLDER, photo_filename)
                photo.save(photo_path)
                photo_url = f"/uploads/{photo_filename}"
            else:
                photo_url = "https://via.placeholder.com/120"

        data["PHOTO_URL"] = photo_url
        data["SUMMARY"] = generate_summary(data)

        context = {
            "NAME": data.get("name", ""),
            "ADDRESS": data.get("address", ""),
            "EMAIL": data.get("email", ""),
            "NUMBER": data.get("phone", ""),
            "ROLE": data.get("role", ""),
            "EXPERIENCE": Markup(data.get("experience", "")),
            "EDUCATION": Markup(data.get("education", "")),
            "PROFESSIONAL": data.get("prof_education", ""),
            "SKILLS": Markup(data.get("skills", "")),
            "PROJECTS": Markup(data.get("projects", "")),
            "AWARDS": Markup(data.get("awards", "")),
            "START": data.get("start", ""),
            "END": data.get("end", ""),
            "SUMMARY": data.get("SUMMARY"),
            "PHOTO_URL": photo_url
        }

        html_out = html_template.render(**context)
        return jsonify({"html": html_out, "summary": data.get("SUMMARY")})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    try:
        html = request.form.get("html", "")
        if not html:
            return jsonify({"error": "No HTML provided"}), 400

        pdf_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.pdf")
        HTML(string=html, base_url=os.getcwd()).write_pdf(pdf_path)

        return send_file(pdf_path, as_attachment=True, download_name="resume.pdf")

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/download-docx", methods=["POST"])
def download_docx():
    try:
        data = request.form.to_dict()
        summary = data.get("SUMMARY", "")

        doc = Document()
        doc.add_heading(data.get("name", ""), 0)
        doc.add_paragraph(f"Email: {data.get('email', '')}")
        doc.add_paragraph(f"Phone: {data.get('phone', '')}")
        doc.add_paragraph(f"Address: {data.get('address', '')}")
        doc.add_paragraph(f"Role: {data.get('role', '')}")
        doc.add_paragraph("Summary:")
        doc.add_paragraph(summary)
        doc.add_paragraph("Experience:")
        doc.add_paragraph(re.sub('<[^<]+?>', '', data.get("experience", "")))
        doc.add_paragraph("Education:")
        doc.add_paragraph(re.sub('<[^<]+?>', '', data.get("education", "")))
        doc.add_paragraph("Skills:")
        doc.add_paragraph(re.sub('<[^<]+?>', '', data.get("skills", "")))
        doc.add_paragraph("Projects:")
        doc.add_paragraph(re.sub('<[^<]+?>', '', data.get("projects", "")))
        doc.add_paragraph("Awards:")
        doc.add_paragraph(re.sub('<[^<]+?>', '', data.get("awards", "")))

        photo_url = data.get("PHOTO_URL", "")
        if photo_url.startswith("data:image"):
            image_path = save_base64_image(photo_url)
            doc.add_picture(image_path, width=Inches(1.5))

        output_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.docx")
        doc.save(output_path)
        return send_file(output_path, as_attachment=True, download_name="resume.docx")

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)















