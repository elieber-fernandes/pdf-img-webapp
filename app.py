from flask import Flask, request, render_template, send_from_directory, redirect, url_for, send_file, after_this_request
import os
from src.pdf_converter import pdf_para_jpg, pdf_para_png, pdf_para_txt, pdf_para_docx, pdf_para_pptx
import zipfile
import io
import shutil

app = Flask(__name__)

HOME = os.path.expanduser('~')
UPLOAD_FOLDER = os.path.join(HOME, 'uploads')
OUTPUT_FOLDER = os.path.join(HOME, 'output')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Limpa as pastas antes de processar novos arquivos
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Erro ao deletar {file_path}: {e}')

    if 'file' not in request.files:
        return "No file part", 400
    files = request.files.getlist('file')
    tipo = request.form.get('tipo', 'jpg')  # Pega o tipo do formulário
    if not files or all(f.filename == '' for f in files):
        return "No selected file", 400
    for file in files:
        if file and file.filename and file.filename.endswith('.pdf'):
            pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(pdf_path)
            # Chama a função de conversão correta
            if tipo == 'jpg':
                pdf_para_jpg(pdf_path, OUTPUT_FOLDER)
            elif tipo == 'png':
                pdf_para_png(pdf_path, OUTPUT_FOLDER)
            elif tipo == 'txt':
                pdf_para_txt(pdf_path, OUTPUT_FOLDER)
            elif tipo == 'docx':
                pdf_para_docx(pdf_path, OUTPUT_FOLDER)
            elif tipo == 'pptx':
                pdf_para_pptx(pdf_path, OUTPUT_FOLDER)
            else:
                return "Tipo de conversão não suportado", 400
        else:
            return "Invalid file type", 400
    return redirect(url_for('output_files', tipo=tipo))

@app.route('/output')
def output_files():
    tipo = request.args.get('tipo', 'jpg')
    files = sorted(os.listdir(OUTPUT_FOLDER))
    thumbnails = []
    if tipo in ['jpg', 'png']:
        thumbnails = files[:10]
        thumb_links = [url_for('download_file', filename=f) for f in thumbnails]
        thumbnails = zip(thumbnails, thumb_links)
    else:
        thumbnails = []
        thumb_links = []
    zip_link = url_for('download_zip')
    individual_links = None
    if len(files) > 0 and len(files) <= 5 and tipo in ['jpg', 'png']:
        individual_links = [
            (f, url_for('download_file', filename=f)) for f in files
        ]
    return render_template(
        'output.html',
        thumbnails=thumbnails,
        zip_link=zip_link,
        individual_links=individual_links,
        tipo=tipo,
        files=files  # Para mostrar arquivos TXT, DOCX, PPTX
    )

@app.route('/output/all.zip')
def download_zip():
    files = os.listdir(OUTPUT_FOLDER)
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for filename in files:
            file_path = os.path.join(OUTPUT_FOLDER, filename)
            zf.write(file_path, arcname=filename)
    memory_file.seek(0)

    @after_this_request
    def cleanup(response):
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Erro ao deletar {file_path}: {e}')
        return response

    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='all.zip'
    )

@app.route('/output/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run()