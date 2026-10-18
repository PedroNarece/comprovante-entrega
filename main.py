"""
ProofSnap - Delivery Receipt Capture & Validation
Autor: Pedro Narece Silva Guimarães

Nota de Desenvolvimento:
Projeto prático desenvolvido para otimização logística de entregas,
evoluindo em paralelo com a minha graduação em Engenharia da Computação.
A visão do produto, arquitetura de dados e validação do fluxo foram estruturadas 
por mim. O código-fonte foi escrito, refatorado e auditado em colaboração com 
Inteligência Artificial, atuando como ferramenta de aprendizado e co-piloto técnico.
"""
import os
import re
import html
import secrets
import uuid
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
security = HTTPBasic()

os.makedirs("uploads", exist_ok=True)

def verificar_credenciais(credentials: HTTPBasicCredentials = Depends(security)):
    # Lê as variáveis de ambiente ou usa os valores padrão para desenvolvimento
    user = os.environ.get("PROOFSNAP_USER", "admin")
    pwd = os.environ.get("PROOFSNAP_PASS", "alianca123")
    
    usuario_correto = secrets.compare_digest(credentials.username, user)
    senha_correta = secrets.compare_digest(credentials.password, pwd)
    if not (usuario_correto and senha_correta):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/")
def interface_motorista():
    return FileResponse("index.html")

# 5. Rota de fotos agora é protegida pela mesma autenticação do dashboard
@app.get("/fotos/{nome_arquivo}")
def servir_foto(nome_arquivo: str, usuario: str = Depends(verificar_credenciais)):
    # Previne path traversal na leitura do arquivo
    nome_seguro = os.path.basename(nome_arquivo)
    caminho = os.path.join("uploads", nome_seguro)
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    return FileResponse(caminho)

@app.post("/upload/")
async def receber_foto(
    foto: UploadFile = File(...),
    carga: str = Form(...),
    motorista: str = Form(...),
    id_entrega: str = Form(...)
):
    # 1. Validação estrita de UUID para impedir Path Traversal
    try:
        valido_id = str(uuid.UUID(id_entrega))
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de entrega inválido.")

    # 7. Rejeita se não estiver no mapa de extensões permitidas
    mapa_extensoes = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    if foto.content_type not in mapa_extensoes:
        raise HTTPException(status_code=400, detail="Formato de imagem não suportado. Apenas JPEG, PNG ou WEBP.")
    extensao = mapa_extensoes[foto.content_type]

    if not carga.isdigit():
        raise HTTPException(status_code=400, detail="Carga inválida.")
    nome_limpo_motorista = re.sub(r"[^a-zA-Z0-9_-]", "", motorista.replace(" ", "_"))

    for ficheiro in os.listdir("uploads"):
        if f"_{valido_id}." in ficheiro:
            return {"mensagem": "Foto já recebida e processada."}

    novo_nome = f"carga{carga}_{nome_limpo_motorista}_{valido_id}.{extensao}"
    caminho_arquivo = f"uploads/{novo_nome}"
    
    # 8. Limite de tamanho lendo em chunks para não estourar a memória RAM (Max 10MB)
    MAX_SIZE = 10 * 1024 * 1024
    tamanho_atual = 0
    
    with open(caminho_arquivo, "wb") as buffer:
        while chunk := await foto.read(1024 * 1024):  # Lê de 1 em 1 MB
            tamanho_atual += len(chunk)
            if tamanho_atual > MAX_SIZE:
                os.remove(caminho_arquivo)  # Apaga o que já foi escrito
                raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo 10MB.")
            buffer.write(chunk)
            
    return {"mensagem": f"Foto guardada como '{novo_nome}'!"}

@app.get("/dashboard", response_class=HTMLResponse)
def ver_dashboard(usuario: str = Depends(verificar_credenciais)):
    ficheiros = os.listdir("uploads")
    ficheiros.sort(key=lambda x: os.path.getmtime(os.path.join("uploads", x)), reverse=True)
    
    html_content = "<h1>Dashboard ProofSnap - Canhotos Recebidos</h1><ul>"
    for ficheiro in ficheiros:
        nome_seguro = html.escape(ficheiro)
        html_content += f"<li><a href='/fotos/{nome_seguro}' target='_blank'>{nome_seguro}</a></li>"
    html_content += "</ul>"
    return html_content
