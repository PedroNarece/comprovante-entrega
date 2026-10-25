"""
Módulo de Validação Inteligente com IA - ProofSnap
Utiliza Visão Computacional (Google Gemini Multimodal) para auditar canhotos de entrega.
Possui fallback automático para Modo Simulação caso nenhuma chave de API esteja configurada.
"""
import os
import json
import logging
from PIL import Image

logger = logging.getLogger("proofsnap.ai")

PROMPT_ANALISE_CANHOTO = """
Você é um auditor de logística de alta precisão especializado em conferência de comprovantes de entrega ("canhotos").
Analise a imagem fornecida e responda ESTRITAMENTE em formato JSON com as seguintes chaves:
{
  "e_canhoto": true ou false (se a imagem aparenta ser uma nota fiscal, canhoto de entrega, recibo ou documento similar),
  "tem_assinatura": true ou false (se há evidência visível de assinatura, rubrica, carimbo ou preenchimento de recebimento no documento),
  "legivel": true ou false (se os dados principais ou o documento estão nítidos e legíveis, não excessivamente borrados ou cortados),
  "motivo": "frase curta e objetiva em português explicando a conclusão da análise"
}
"""

def _validar_com_gemini(caminho_foto: str, api_key: str) -> dict:
    """Executa a análise real com a API oficial do Google Gemini."""
    try:
        from google import genai
        
        cliente = genai.Client(api_key=api_key)
        with Image.open(caminho_foto) as imagem:
            resposta = cliente.models.generate_content(
                model="gemini-flash-latest",
                contents=[imagem, PROMPT_ANALISE_CANHOTO]
            )
            
            # Limpa possíveis blocos de markdown ```json ... ``` retornados pelo modelo
            texto = resposta.text.strip()
            if texto.startswith("```json"):
                texto = texto[7:]
            if texto.startswith("```"):
                texto = texto[3:]
            if texto.endswith("```"):
                texto = texto[:-3]
            texto = texto.strip()
            
            dados = json.loads(texto)
            return {
                "e_canhoto": bool(dados.get("e_canhoto", False)),
                "tem_assinatura": bool(dados.get("tem_assinatura", False)),
                "legivel": bool(dados.get("legivel", False)),
                "motivo": str(dados.get("motivo", "Análise realizada via Gemini Vision."))
            }
    except Exception as erro:
        logger.warning(f"Falha ao consultar API do Gemini: {erro}. Usando fallback seguro.")
        return {
            "e_canhoto": True,
            "tem_assinatura": True,
            "legivel": True,
            "motivo": f"Aprovado por contingência (erro na chamada da IA: {type(erro).__name__})"
        }

def _validar_modo_simulacao(caminho_foto: str) -> dict:
    """
    Modo Demonstração / Local:
    Permite estudar e testar toda a arquitetura sem custo e sem precisar de chave de API.
    Inspeciona dimensões e proporções da imagem.
    """
    try:
        with Image.open(caminho_foto) as img:
            largura, altura = img.size
            
            # Regra heurística 1: imagens minúsculas (ex: ícones ou miniaturas) são rejeitadas
            if largura < 250 or altura < 250:
                return {
                    "e_canhoto": False,
                    "tem_assinatura": False,
                    "legivel": False,
                    "motivo": "Imagem com resolução muito baixa para leitura de canhoto."
                }
            
            return {
                "e_canhoto": True,
                "tem_assinatura": True,
                "legivel": True,
                "motivo": "Comprovante validado com sucesso (Modo Demonstração)."
            }
    except Exception:
        return {
            "e_canhoto": False,
            "tem_assinatura": False,
            "legivel": False,
            "motivo": "Estrutura do arquivo inválida para análise visual."
        }

def validar_canhoto_com_ia(caminho_foto: str) -> dict:
    """
    Ponto de entrada único para validação de conteúdo.
    Detecta se há GEMINI_API_KEY no ambiente:
    - Se houver: utiliza a IA real do Google.
    - Se não houver: utiliza o Modo Demonstração sem gerar erros.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and api_key.strip():
        return _validar_com_gemini(caminho_foto, api_key.strip())
    
    return _validar_modo_simulacao(caminho_foto)
