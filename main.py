"""
ProofSnap - Delivery Receipt Capture & Validation
Autor: Pedro Narece Silva Guimarães

Nota de Desenvolvimento:
A arquitetura, a lógica de negócio e as decisões estruturais deste sistema foram 
desenhadas e revisadas por mim. Ferramentas de Inteligência Artificial foram 
utilizadas estritamente como assistentes de digitação para aceleração de sintaxe.
"""
import os
import shutil
# Adicionamos 'Form' à lista de importações do fastapi
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

os.makedirs("uploads", exist_ok=True)
app.mount("/fotos", StaticFiles(directory="uploads"), name="fotos")

@app.get("/")
def interface_motorista():
    return FileResponse("index.html")

# Atualizamos a carga para exigir a carga e o motorista
@app.post("/upload/")
def receber_foto(
    foto: UploadFile = File(...),
    carga: str = Form(...),
    motorista: str = Form(...)
):
    # 1. Descobrir a extensão original do ficheiro (ex: jpg, png)
    extensao = foto.filename.split(".")[-1]
    
    # 2. Criar o novo nome padronizado e remover espaços vazios
    nome_limpo_motorista = motorista.replace(" ", "_")
    novo_nome = f"carga{carga}_{nome_limpo_motorista}.{extensao}"
    
    # 3. Guardar com o novo nome
    caminho_arquivo = f"uploads/{novo_nome}"
    with open(caminho_arquivo, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)
        
    return {"mensagem": f"Foto guardada como '{novo_nome}'!"}

@app.get("/dashboard", response_class=HTMLResponse)
def ver_dashboard():
    ficheiros = os.listdir("uploads")
    html = "<h1>Dashboard ProofSnap - Canhotos Recebidos</h1><ul>"
    for ficheiro in ficheiros:
        html += f"<li><a href='/fotos/{ficheiro}' target='_blank'>{ficheiro}</a></li>"
    html += "</ul>"
    return html
