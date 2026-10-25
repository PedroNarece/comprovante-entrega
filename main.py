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
import time
import logging
from PIL import Image
from dotenv import load_dotenv
import database
import ai_validator
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# Configuração de Logging Estruturado (v4 - Operations)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("proofsnap.ops")

# Carrega as variáveis definidas no arquivo .env para o os.environ do sistema
load_dotenv()

app = FastAPI()
security = HTTPBasic()

# Middleware de Observabilidade e Métricas de Performance (v4)
@app.middleware("http")
async def registrar_metricas_requisicao(request: Request, call_next):
    inicio = time.perf_counter()
    resposta = await call_next(request)
    duracao_ms = (time.perf_counter() - inicio) * 1000
    
    # Injeta cabeçalho com o tempo de resposta para diagnóstico do cliente
    resposta.headers["X-Response-Time-Ms"] = f"{duracao_ms:.2f}"
    
    ip_cliente = request.client.host if request.client else "desconhecido"
    logger.info(
        f"MÉTRICA | {request.method} {request.url.path} | Status: {resposta.status_code} | "
        f"Latência: {duracao_ms:.2f}ms | IP: {ip_cliente}"
    )
    return resposta

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
    
    logger.info(f"UPLOAD INICIADO | Carga: {carga} | Motorista: {nome_limpo_motorista} | ID: {valido_id}")
    
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
        
        # Auditoria por Inteligência Artificial (Visão Computacional - Requisito v3)
        resultado_ia = ai_validator.validar_canhoto_com_ia(caminho_final)
        status_final = "APROVADO" if (resultado_ia["e_canhoto"] and resultado_ia["tem_assinatura"] and resultado_ia["legivel"]) else "REJEITADO"

        # Persiste o registro de entrega no SQLite com os dados da auditoria da IA
        database.registrar_entrega(
            id_entrega=valido_id,
            carga=carga,
            motorista=nome_limpo_motorista,
            nome_arquivo=novo_nome,
            status=status_final,
            motivo_ia=resultado_ia["motivo"],
            tem_assinatura=resultado_ia["tem_assinatura"]
        )
        
        logger.info(f"AUDITORIA CONCLUÍDA | Carga: {carga} | Status: {status_final} | Motivo: {resultado_ia['motivo']}")
    except Exception as erro:
        logger.error(f"FALHA NO UPLOAD | Carga: {carga} | Erro: {erro}")
        # Garante que nenhum arquivo temporário incompleto permaneça no disco
        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)
        raise erro
            
    return {
        "mensagem": f"Foto guardada como '{novo_nome}'!",
        "status": status_final,
        "motivo_ia": resultado_ia["motivo"]
    }

@app.get("/dashboard", response_class=HTMLResponse)
def ver_dashboard(usuario: str = Depends(verificar_credenciais)):
    entregas = database.listar_entregas()
    stats = database.obter_estatisticas()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard ProofSnap - IA & Operações</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 30px; background-color: #f8fafc; color: #1e293b; }}
            h1 {{ margin-bottom: 5px; }}
            .subtitulo {{ color: #64748b; margin-top: 0; margin-bottom: 25px; }}
            
            /* Cartões de Estatísticas Diárias (v3 Metrics) */
            .cards-container {{ display: flex; gap: 15px; margin-bottom: 30px; flex-wrap: wrap; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; flex: 1; min-width: 140px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
            .card-title {{ font-size: 13px; font-weight: 600; text-transform: uppercase; color: #64748b; margin-bottom: 8px; }}
            .card-valor {{ font-size: 28px; font-weight: 700; }}
            .card-verde {{ color: #16a34a; }}
            .card-vermelho {{ color: #dc2626; }}
            .card-azul {{ color: #2563eb; }}
            
            /* Tabela de Canhotos */
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
            th, td {{ padding: 14px 18px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
            th {{ background-color: #f1f5f9; font-weight: 600; color: #475569; }}
            tr:hover {{ background-color: #f8fafc; }}
            
            /* Badges de Status */
            .badge {{ display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; }}
            .badge-aprovado {{ background-color: #dcfce7; color: #15803d; }}
            .badge-rejeitado {{ background-color: #fee2e2; color: #b91c1c; }}
            .badge-carga {{ background-color: #e0f2fe; color: #0369a1; }}
            
            a.btn-ver {{ color: #2563eb; text-decoration: none; font-weight: 600; }}
            a.btn-ver:hover {{ text-decoration: underline; }}
            .motivo-ia {{ font-size: 13px; color: #475569; }}
        </style>
    </head>
    <body>
        <h1>Dashboard ProofSnap</h1>
        <p class="subtitulo">Auditoria Inteligente de Entregas em Tempo Real (v3)</p>
        
        <!-- Cartões de Métricas Operacionais (v3) -->
        <div class="cards-container">
            <div class="card">
                <div class="card-title">Total de Envios</div>
                <div class="card-valor card-azul">{stats["total"]}</div>
            </div>
            <div class="card">
                <div class="card-title">Aprovados pela IA</div>
                <div class="card-valor card-verde">{stats["aprovados"]}</div>
            </div>
            <div class="card">
                <div class="card-title">Rejeitados pela IA</div>
                <div class="card-valor card-vermelho">{stats["rejeitados"]}</div>
            </div>
            <div class="card">
                <div class="card-title">Taxa de Aprovação</div>
                <div class="card-valor card-verde">{stats["taxa_aprovacao"]}%</div>
            </div>
            <div class="card">
                <div class="card-title">Recebidos Hoje</div>
                <div class="card-valor">{stats["hoje"]}</div>
            </div>
        </div>
        
        <!-- Tabela Estruturada -->
        <table>
            <thead>
                <tr>
                    <th>Status IA</th>
                    <th>Carga</th>
                    <th>Motorista</th>
                    <th>Diagnóstico da IA</th>
                    <th>Data / Hora</th>
                    <th>Comprovante</th>
                </tr>
            </thead>
            <tbody>
    """
    
    if not entregas:
        html_content += "<tr><td colspan='6' style='text-align:center; padding: 30px; color: #94a3b8;'>Nenhum canhoto registrado ainda.</td></tr>"
    else:
        for entrega in entregas:
            nome_seguro = html.escape(entrega["nome_arquivo"])
            carga_segura = html.escape(str(entrega["carga"]))
            motorista_seguro = html.escape(str(entrega["motorista"]))
            data_segura = html.escape(str(entrega["criado_em"]))
            status_val = str(entrega["status"] if "status" in entrega.keys() else "APROVADO")
            motivo_val = html.escape(str(entrega["motivo_ia"] if "motivo_ia" in entrega.keys() else "Comprovante validado"))
            
            badge_classe = "badge-aprovado" if status_val == "APROVADO" else "badge-rejeitado"
            
            html_content += f"""
                <tr>
                    <td><span class='badge {badge_classe}'>{status_val}</span></td>
                    <td><span class='badge badge-carga'>{carga_segura}</span></td>
                    <td><strong>{motorista_seguro}</strong></td>
                    <td class='motivo-ia'>{motivo_val}</td>
                    <td>{data_segura}</td>
                    <td><a href='/fotos/{nome_seguro}' target='_blank' class='btn-ver'>Ver Foto</a></td>
                </tr>
            """
            
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html_content
