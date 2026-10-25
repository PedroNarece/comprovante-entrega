"""
Módulo de Banco de Dados - ProofSnap
Gerencia a persistência relacional das entregas utilizando SQLite.
"""
import sqlite3
from typing import List, Dict, Any, Optional

NOME_BANCO = "proofsnap.db"

def obter_conexao() -> sqlite3.Connection:
    """Abre uma conexão com o SQLite permitindo acesso a colunas por nome."""
    conexao = sqlite3.connect(NOME_BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao

def inicializar_banco() -> None:
    """
    Cria a tabela inicial e executa migrações automáticas para novas colunas.
    Garante evolução do esquema (schema) sem perda de dados existentes.
    """
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        
        # 1. Cria a tabela base caso não exista
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entregas (
                id TEXT PRIMARY KEY,
                carga TEXT NOT NULL,
                motorista TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Migração: verifica as colunas existentes para adicionar os campos da IA (v3)
        cursor.execute("PRAGMA table_info(entregas);")
        colunas_existentes = [coluna["name"] for coluna in cursor.fetchall()]
        
        if "status" not in colunas_existentes:
            cursor.execute("ALTER TABLE entregas ADD COLUMN status TEXT DEFAULT 'APROVADO';")
            
        if "motivo_ia" not in colunas_existentes:
            cursor.execute("ALTER TABLE entregas ADD COLUMN motivo_ia TEXT DEFAULT 'Canhoto validado';")
            
        if "tem_assinatura" not in colunas_existentes:
            cursor.execute("ALTER TABLE entregas ADD COLUMN tem_assinatura INTEGER DEFAULT 1;")
            
        conexao.commit()

def entrega_ja_existe(id_entrega: str) -> bool:
    """Verifica se uma entrega com determinado UUID já foi registrada (O(log N))."""
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM entregas WHERE id = ? LIMIT 1;", (id_entrega,))
        return cursor.fetchone() is not None

def registrar_entrega(
    id_entrega: str,
    carga: str,
    motorista: str,
    nome_arquivo: str,
    status: str = "APROVADO",
    motivo_ia: str = "Canhoto validado",
    tem_assinatura: bool = True
) -> None:
    """Insere um novo canhoto de entrega no banco de dados com a auditoria da IA."""
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO entregas (id, carga, motorista, nome_arquivo, status, motivo_ia, tem_assinatura)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (id_entrega, carga, motorista, nome_arquivo, status, motivo_ia, 1 if tem_assinatura else 0))
        conexao.commit()

def listar_entregas() -> List[sqlite3.Row]:
    """Retorna todas as entregas ordenadas da mais recente para a mais antiga."""
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT id, carga, motorista, nome_arquivo, status, motivo_ia, tem_assinatura, criado_em
            FROM entregas
            ORDER BY criado_em DESC;
        """)
        return cursor.fetchall()

def obter_estatisticas() -> Dict[str, Any]:
    """
    Calcula as métricas operacionais para o dashboard diário (requisito v3 do roadmap).
    """
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        
        # Total geral
        cursor.execute("SELECT COUNT(*) FROM entregas;")
        total = cursor.fetchone()[0]
        
        # Aprovados
        cursor.execute("SELECT COUNT(*) FROM entregas WHERE status = 'APROVADO';")
        aprovados = cursor.fetchone()[0]
        
        # Rejeitados
        cursor.execute("SELECT COUNT(*) FROM entregas WHERE status = 'REJEITADO';")
        rejeitados = cursor.fetchone()[0]
        
        # Entregas de hoje
        cursor.execute("SELECT COUNT(*) FROM entregas WHERE date(criado_em) = date('now');")
        hoje = cursor.fetchone()[0]
        
        taxa_aprovacao = round((aprovados / total * 100), 1) if total > 0 else 100.0
        
        return {
            "total": total,
            "aprovados": aprovados,
            "rejeitados": rejeitados,
            "hoje": hoje,
            "taxa_aprovacao": taxa_aprovacao
        }
