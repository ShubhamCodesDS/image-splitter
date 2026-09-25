import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/split-image', methods=['POST'])
def split_image():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image uploaded'})
        
        file = request.files['image']
        layout = request.form.get('layout', 'layout_5') # Default 5-pose

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'})

        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        img = Image.open(input_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        width, height = img.size
        margin = max(2, width // 300)
        custom_crops = {}

        # Layout ke hisab se dynamic cropping logic
        if layout == 'layout_5': # 4 left grid + 1 right big close-up
            half_w = width // 2
            quarter_h = height // 2
            left_col_w = half_w // 2
            custom_crops = {
                "Front View (Top-Left)": (margin, margin, left_col_w - margin, quarter_h - margin),
                "Side View (Top-Right)": (left_col_w + margin, margin, half_w - margin, quarter_h - margin),
                "Lower Front (Bottom-Left)": (margin, quarter_h + margin, left_col_w - margin, height - margin),
                "Back View (Bottom-Right)": (left_col_w + margin, quarter_h + margin, half_w - margin, height - margin),
                "Close-Up View (Right Side)": (half_w + margin, margin, width - margin, height - margin)
            }
        elif layout == 'layout_4': # 2x2 Equal Grid (4 Poses)
            half_w = width // 2
            half_h = height // 2
            custom_crops = {
                "Top-Left Pose": (margin, margin, half_w - margin, half_h - margin),
                "Top-Right Pose": (half_w + margin, margin, width - margin, half_h - margin),
                "Bottom-Left Pose": (margin, half_h + margin, half_w - margin, height - margin),
                "Bottom-Right Pose": (half_w + margin, half_h + margin, width - margin, height - margin)
            }
        elif layout == 'layout_6': # 3x2 Grid (6 Poses)
            col_w = width // 3
            row_h = height // 2
            for i in range(2):
                for j in range(3):
                    pos_name = f"Pose Row {i+1} Col {j+1}"
                    custom_crops[pos_name] = (
                        j * col_w + margin, 
                        i * row_h + margin, 
                        (j + 1) * col_w - margin, 
                        (i + 1) * row_h - margin
                    )

        output_files = {}
        base_name = os.path.splitext(filename)[0]
        
        for key, box in custom_crops.items():
            box = tuple(max(0, b) for b in box)
            cropped_img = img.crop(box)
            out_name = f"{key.replace(' ', '_').replace('(', '').replace(')', '')}_{base_name}.png"
            out_path = os.path.join(PROCESSED_FOLDER, out_name)
            
            cropped_img.save(out_path, "PNG", quality=100, optimize=False)
            output_files[key] = f"/download/{out_name}"

        return jsonify({'success': True, 'images': output_files})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(PROCESSED_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)