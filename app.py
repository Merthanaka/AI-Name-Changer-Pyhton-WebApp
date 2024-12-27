import os
import time
from flask import Flask, request, redirect, url_for, render_template, send_file
import google.generativeai as genai
from datetime import datetime

app = Flask(__name__)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Dosyayı Gemini'ye yükleme
def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

# Dosya işlenmesini bekleme
def wait_for_files_active(files):
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    print("...all files ready")
    print()

# Şirket adını almak ve dosya adını değiştirmek
def get_company_name(file):
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-002",
        generation_config={
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        },
        system_instruction="You are name identifier. User will send you any kind of file (it will be always invoices )and from that file you will identify the company, person, organization, or institution. As a response just give the name nothing else.",
    )

    chat_session = model.start_chat(history=[{"role": "user", "parts": [file]}])
    response = chat_session.send_message("Şirket adını al")
    return response.text.strip()

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join("uploads", file.filename)
            file.save(file_path)

            # Dosyayı Gemini'ye yükle ve işle
            gemini_file = upload_to_gemini(file_path, mime_type="application/pdf")
            wait_for_files_active([gemini_file])

            # Şirket adını al
            company_name = get_company_name(gemini_file)
            date_today = datetime.today().strftime("%Y-%m-%d")
            new_filename = f"{company_name}_{date_today}.pdf"
            new_file_path = os.path.join("uploads", new_filename)
            os.rename(file_path, new_file_path)

            return send_file(new_file_path, as_attachment=True)

    return '''
    <!doctype html>
    
    <style>
        /* Genel Stil Ayarları */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }

        /* Sayfanın Ortalanması */
        body {
            background-color: #f0f4f8;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            text-align: center;
        }

        .container {
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
            max-width: 400px;
            width: 100%;
        }

        

        /* Form Stil Ayarları */
        form {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* Dosya Yükleme Alanı */
        input[type="file"] {
            margin: 15px 0;
            padding: 15px;
            font-size: 1em;
            border: 2px dashed #ddd;
            border-radius: 4px;
            width: 100%;
            text-align: center;
            transition: border-color 0.3s ease;
            background-color: #f9f9f9;
            color: #888;
            cursor: pointer;
        }

        input[type="file"]:hover {
            border-color: #6c63ff;
        }

        /* Yükleme Butonu */
        input[type="submit"] {
            background-color: #6c63ff;
            color: #fff;
            font-size: 1.1em;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s ease;
            width: 100%;
            margin-top: 10px;
        }

        input[type="submit"]:hover {
            background-color: #5551d6;
        }
    </style>
    
    <div class="container">
        <h1>Drag Or Upload Invoice</h1>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <input type="submit" value="Upload">
        </form>
    </div>
    </form>
    '''

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)
