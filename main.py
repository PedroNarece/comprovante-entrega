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
from PIL import Image
from dotenv import load_dotenv
import database
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# Carrega as variáveis definidas no arquivo .env para o os.environ do sistema
load_dotenv()

app = FastAPI()
security = HTTPBasic()

os.makedirs("uploads", exist_ok=True)
# Cria o arquivo SQLite e a tabela 'entregas' automaticamente se não existirem
database.inicializar_banco()

def verificar_credenciais(credentials: HTTPBasicCredentials = Depends(security)):
    # Lê as variáveis de ambiente SEM valores padrão fixos
    user = os.environ.get("PROOFSNAP_USER")
    pwd = os.environ.get("PROOFSNAP_PASS")
    
    # Trava de segurança: se as variáveis não estiverem configuradas no terminal, o sistema recusa-se a funcionar
    if not user or not pwd:
        raise HTTPException(status_code=500, detail="Credenciais não configuradas no servidor.")
        
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

    # Idempotência ultra-rápida via SQLite (substitui o loop O(N) de os.listdir)
    if database.entrega_ja_existe(valido_id):
        return {"mensagem": "Foto já recebida e processada."}

    novo_nome = f"carga{carga}_{nome_limpo_motorista}_{valido_id}.{extensao}"
    caminho_final = os.path.join("uploads", novo_nome)
    caminho_temp = f"{caminho_final}.temp"
    
    # Limite de tamanho lendo em chunks para não estourar a memória RAM (Max 10MB)
    MAX_SIZE = 10 * 1024 * 1024
    tamanho_atual = 0
    
    try:
        # Gravação atômica: salva primeiro em .temp para evitar corrupção em caso de queda de rede
        with open(caminho_temp, "wb") as buffer:
            while chunk := await foto.read(1024 * 1024):  # Lê de 1 em 1 MB
                tamanho_atual += len(chunk)
                if tamanho_atual > MAX_SIZE:
                    raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo 10MB.")
                buffer.write(chunk)

        # Validação estrutural de imagem com Pillow (garante que é uma imagem real e íntegra)
        try:
            with Image.open(caminho_temp) as img:
                img.verify()
                if img.format.lower() not in ["jpeg", "png", "webp"]:
                    raise HTTPException(status_code=400, detail="Conteúdo da imagem não é suportado.")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Arquivo inválido ou corrompido. Não é uma imagem reconhecida.")
                
        # Renomeação atômica pelo SO: o arquivo final só passa a existir quando está 100% completo e validado
        os.replace(caminho_temp, caminho_final)
        
        # Persiste o registro de entrega no SQLite
        database.registrar_entrega(
            id_entrega=valido_id,
            carga=carga,
            motorista=nome_limpo_motorista,
            nome_arquivo=novo_nome
        )
    except Exception as erro:
        # Garante que nenhum arquivo temporário incompleto permaneça no disco
        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)
        raise erro
            
    return {"mensagem": f"Foto guardada como '{novo_nome}'!"}

@app.get("/dashboard", response_class=HTMLResponse)
def ver_dashboard(usuario: str = Depends(verificar_credenciais)):
    entregas = database.listar_entregas()
    
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard ProofSnap</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 30px; background-color: #f8f9fa; }
            h1 { color: #333; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #007bff; color: white; }
            tr:hover { background-color: #f1f5f9; }
            a { color: #007bff; text-decoration: none; font-weight: bold; }
            a:hover { text-decoration: underline; }
            .badge { background: #e2e8f0; padding: 4px 8px; border-radius: 4px; font-size: 14px; }
        </style>
    </head>
    <body>
        <h1>Dashboard ProofSnap - Canhotos Recebidos</h1>
        <p>Total de registros no banco: <strong>""" + str(len(entregas)) + """</strong></p>
        <table>
            <thead>
                <tr>
                    <th>Carga</th>
                    <th>Motorista</th>
                    <th>Data/Hora</th>
                    <th>ID da Entrega</th>
                    <th>Comprovante</th>
                </tr>
            </thead>
            <tbody>
    """
    
    if not entregas:
        html_content += "<tr><td colspan='5' style='text-align:center;'>Nenhum canhoto registrado ainda.</td></tr>"
    else:
        for entrega in entregas:
            nome_seguro = html.escape(entrega["nome_arquivo"])
            carga_segura = html.escape(str(entrega["carga"]))
            motorista_seguro = html.escape(str(entrega["motorista"]))
            data_segura = html.escape(str(entrega["criado_em"]))
            id_seguro = html.escape(str(entrega["id"]))
            
            html_content += f"""
                <tr>
                    <td><span class='badge'>{carga_segura}</span></td>
                    <td>{motorista_seguro}</td>
                    <td>{data_segura}</td>
                    <td><code>{id_seguro}</code></td>
                    <td><a href='/fotos/{nome_seguro}' target='_blank'>Visualizar Canhoto</a></td>
                </tr>
            """
            
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html_content
