from flask import Flask, request, jsonify
import filetype
import os
import re
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
from paddleocr import PaddleOCR

app = Flask(__name__)
ocr = PaddleOCR(use_angle_cls=True, lang='en')  # 'en' for English, can change to 'en+hi' etc.

def is_valid_prescription(text):
    text = text.lower()
    patterns = [
        r'\brx\b',                               # 'Rx'
        r'dr\.\s?[a-z]{2,}',                     # 'Dr. Sharma'
        r'\b\d{2,4}\s?(mg|ml)\b',                # '500mg'
        r'\btake\s?(once|twice|daily)?\b',       # 'Take once daily'
        r'\btablet|capsule|syrup\b'              # medicine forms
    ]
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False

def extract_text(file):
    kind = filetype.guess(file.read(2048))
    file.seek(0)
    mime_type = kind.mime if kind else file.mimetype
    text_output = ""

    def ocr_image(image):
        result = ocr.ocr(np.array(image), cls=True)
        return " ".join([line[1][0] for line in result[0]])

    if "image" in mime_type:
        image = Image.open(file).convert('RGB')
        text_output = ocr_image(image)

    elif "pdf" in mime_type:
        temp_path = "temp_prescription.pdf"
        with open(temp_path, 'wb') as f:
            f.write(file.read())

        images = convert_from_path(temp_path, dpi=300)
        for img in images:
            text_output += ocr_image(img) + " "
        os.remove(temp_path)

    else:
        return None

    return text_output.strip()

@app.route('/verify', methods=['POST'])
def verify_prescription():
    file = request.files.get('prescription')
    if not file:
        return jsonify({"verified": False, "error": "No file uploaded"}), 400

    try:
        text = extract_text(file)
        if not text:
            return jsonify({"verified": False, "error": "Unable to extract text"}), 400

        verified = is_valid_prescription(text)
        return jsonify({
            "verified": verified,
            "extractedText": text
        })
    except Exception as e:
        return jsonify({
            "verified": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(port=6000, debug=True)
