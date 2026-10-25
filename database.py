"""
Módulo de Banco de Dados - ProofSnap
Gerencia a persistência relacional das entregas utilizando SQLite.
"""
import sqlite3
from typing import List, Optional

# Nome do arquivo de banco de dados local
NOME_BANCO = "proofsnap.db"

def obter_conexao() -> sqlite3.Connection:
    """
    Abre uma conexão com o arquivo SQLite.
    row_factory = sqlite3.Row permite acessar as colunas pelo nome (ex: linha['carga'])
    em vez de apenas por índices numéricos (linha[0]).
    """
    conexao = sqlite3.connect(NOME_BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao

def inicializar_banco() -> None:
    """
    Cria a tabela de entregas caso ela ainda não exista.
    Essa função é executada quando o servidor inicia.
    """
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entregas (
                id TEXT PRIMARY KEY,
                carga TEXT NOT NULL,
                motorista TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conexao.commit()

def entrega_ja_existe(id_entrega: str) -> bool:
    """
    Verifica se uma entrega com determinado UUID já foi registrada.
    Utiliza busca indexada pela Chave Primária (PRIMARY KEY), que é extremamente rápida (O(log N)).
    """
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        # O uso de '?' é uma consulta parametrizada que impede ataques de SQL Injection
        cursor.execute("SELECT 1 FROM entregas WHERE id = ? LIMIT 1;", (id_entrega,))
        resultado = cursor.fetchone()
        return resultado is not None

def registrar_entrega(id_entrega: str, carga: str, motorista: str, nome_arquivo: str) -> None:
    """
    Insere um novo canhoto de entrega no banco de dados.
    """
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO entregas (id, carga, motorista, nome_arquivo)
            VALUES (?, ?, ?, ?);
        """, (id_entrega, carga, motorista, nome_arquivo))
        conexao.commit()

def listar_entregas() -> List[sqlite3.Row]:
    """
    Retorna todas as entregas ordenadas da mais recente para a mais antiga.
    Substitui a leitura pesada de 'os.listdir()' no dashboard.
    """
    with obter_conexao() as conexao:
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT id, carga, motorista, nome_arquivo, criado_em
            FROM entregas
            ORDER BY criado_em DESC;
        """)
        return cursor.fetchall()
