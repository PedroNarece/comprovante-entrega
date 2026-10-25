"""
ProofSnap - Simulador de Carga e Concorrência (v4 - Operations)
Simula múltiplos motoristas enviando comprovantes de entrega simultaneamente.
Mede latência, taxa de sucesso e throughput (requisições por segundo).
"""
import asyncio
import io
import time
import uuid
import statistics
import argparse
from typing import List, Dict, Any
from PIL import Image, ImageDraw
import httpx

def gerar_imagem_comprovante_sintetica(numero_carga: str, motorista: str) -> io.BytesIO:
    """Gera uma imagem sintética de canhoto na memória (sem salvar no disco local)."""
    largura, altura = 600, 400
    imagem = Image.new("RGB", (largura, altura), color="#ffffff")
    desenho = ImageDraw.Draw(imagem)
    
    # Desenha bordas de um canhoto comercial
    desenho.rectangle([10, 10, largura - 10, altura - 10], outline="#0284c7", width=3)
    desenho.rectangle([20, 20, largura - 20, 80], fill="#f1f5f9", outline="#cbd5e1")
    
    # Textos simulando uma nota de entrega
    desenho.text((30, 35), "COMPROVANTE DE ENTREGA - ALIANCA ATACADISTA", fill="#0f172a")
    desenho.text((30, 55), f"Carga: {numero_carga} | Motorista: {motorista}", fill="#475569")
    
    # Simula um campo e traço de assinatura
    desenho.rectangle([40, 250, 350, 330], outline="#94a3b8", width=1)
    desenho.text((50, 260), "Assinatura do Recebedor:", fill="#64748b")
    # Rabisco simulando a assinatura feita pelo cliente
    desenho.line([(60, 305), (120, 280), (160, 315), (220, 290), (300, 310)], fill="#1e3a8a", width=2)
    
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return buffer

async def simular_motorista(
    cliente: httpx.AsyncClient,
    url_alvo: str,
    id_motorista: int,
    resultados: List[Dict[str, Any]],
    semaforo: asyncio.Semaphore
) -> None:
    """Representa a ação de um motorista individual enviando um canhoto."""
    async with semaforo:
        carga = f"{1000 + id_motorista}"
        nome_motorista = f"Motorista_Virtual_{id_motorista:02d}"
        id_entrega = str(uuid.uuid4())
        
        # Gera o arquivo binário na memória RAM
        buffer_foto = gerar_imagem_comprovante_sintetica(carga, nome_motorista)
        
        inicio = time.perf_counter()
        sucesso = False
        status_code = 0
        erro_msg = ""
        
        try:
            arquivos = {
                "foto": ("canhoto.jpg", buffer_foto.getvalue(), "image/jpeg")
            }
            dados = {
                "carga": carga,
                "motorista": nome_motorista,
                "id_entrega": id_entrega
            }
            
            resposta = await cliente.post(
                f"{url_alvo.rstrip('/')}/upload/",
                data=dados,
                files=arquivos,
                timeout=60.0
            )
            duracao = time.perf_counter() - inicio
            status_code = resposta.status_code
            sucesso = (status_code == 200)
            
            if not sucesso:
                erro_msg = resposta.text[:100]
                
        except Exception as e:
            duracao = time.perf_counter() - inicio
            erro_msg = str(e)
            
        resultados.append({
            "motorista": nome_motorista,
            "carga": carga,
            "status_code": status_code,
            "sucesso": sucesso,
            "latencia_segundos": duracao,
            "erro": erro_msg
        })
        
        icone = "✅" if sucesso else "❌"
        print(f" {icone} [{nome_motorista}] Carga {carga} -> {status_code} ({duracao:.2f}s)")

async def executar_teste_de_carga(url_alvo: str, total_motoristas: int, concorrencia_maxima: int) -> None:
    """Orquestra todos os motoristas virtuais e gera o relatório final de operações."""
    print("=" * 65)
    print("  PROOFSNAP - SIMULADOR DE CONCORRÊNCIA E CARGA (v4 Operations)")
    print("=" * 65)
    print(f" Alvo do Teste:        {url_alvo}")
    print(f" Total de Motoristas:  {total_motoristas}")
    print(f" Concorrência Máxima:  {concorrencia_maxima} envios simultâneos")
    print("-" * 65)
    print(" Disparando envios concorrentes...")
    
    resultados: List[Dict[str, Any]] = []
    semaforo = asyncio.Semaphore(concorrencia_maxima)
    
    inicio_geral = time.perf_counter()
    
    async with httpx.AsyncClient() as cliente:
        tarefas = [
            simular_motorista(cliente, url_alvo, i + 1, resultados, semaforo)
            for i in range(total_motoristas)
        ]
        await asyncio.gather(*tarefas)
        
    tempo_total = time.perf_counter() - inicio_geral
    
    # Análise Estatística dos Resultados
    sucessos = [r for r in resultados if r["sucesso"]]
    falhas = [r for r in resultados if not r["sucesso"]]
    latencias = [r["latencia_segundos"] for r in resultados]
    
    taxa_sucesso = (len(sucessos) / len(resultados) * 100) if resultados else 0
    throughput = len(resultados) / tempo_total if tempo_total > 0 else 0
    
    lat_min = min(latencias) if latencias else 0
    lat_media = statistics.mean(latencias) if latencias else 0
    lat_mediana = statistics.median(latencias) if latencias else 0
    lat_max = max(latencias) if latencias else 0
    
    print("-" * 65)
    print("  RELATÓRIO DE CONFIABILIDADE OPERACIONAL (SRE)")
    print("=" * 65)
    print(f" Tempo Total de Execução:    {tempo_total:.2f} segundos")
    print(f" Envios Bem-Sucedidos:       {len(sucessos)} / {len(resultados)} ({taxa_sucesso:.1f}%)")
    print(f" Envios com Falha:           {len(falhas)}")
    print(f" Vazão (Throughput):         {throughput:.2f} requisições/segundo")
    print("-" * 65)
    print("  ANÁLISE DE LATÊNCIA (TEMPO DE RESPOSTA):")
    print(f" • Mínima:                  {lat_min:.2f}s")
    print(f" • Média:                   {lat_media:.2f}s")
    print(f" • Mediana:                 {lat_mediana:.2f}s")
    print(f" • Máxima (Pior caso):      {lat_max:.2f}s")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ProofSnap Load Simulator")
    parser.add_argument("--url", default="https://proofsnap-x8tx.onrender.com", help="URL base da API")
    parser.add_argument("--motoristas", type=int, default=5, help="Total de comprovantes a enviar")
    parser.add_argument("--concorrencia", type=int, default=3, help="Número de disparos simultâneos")
    
    args = parser.parse_args()
    asyncio.run(executar_teste_de_carga(args.url, args.motoristas, args.concorrencia))
