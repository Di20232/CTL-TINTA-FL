#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camada de acesso ao banco de dados — Controle de Tinta e Toner.
Separada do app Tkinter para reutilização com Flask.
"""

import os
import logging
import math
import sqlite3
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "controle_suprimentos.db")

# Logger do módulo — WARNING por padrão; ERROR para exceções inesperadas.
# O app hospedeiro (Tkinter/Flask) pode reconfigurar nível/formato via
# logging.basicConfig() ou um handler próprio antes de importar este módulo.
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d — %(message)s",
)
logger = logging.getLogger(__name__)

# Tabelas permitidas para operacoes por nome (anti SQL-injection por controle de tabela)
TABELAS_VALIDAS = {"filiais", "departamentos", "itens", "entradas", "despachos"}


def _validar_tabela(tabela):
    """Garante que 'tabela' e uma das tabelas conhecidas. Levanta ValueError caso contrario."""
    if tabela not in TABELAS_VALIDAS:
        raise ValueError(f"Tabela invalida: {tabela!r}")


def get_conn():
    """Retorna uma conexao SQLite com foreign keys, WAL e busy_timeout habilitados."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria as tabelas se nao existirem."""
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS filiais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS departamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                tipo TEXT NOT NULL DEFAULT 'Toner',
                estoque_minimo INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS entradas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                item_id INTEGER NOT NULL REFERENCES itens(id),
                quantidade INTEGER NOT NULL,
                fornecedor TEXT,
                valor_unitario REAL,
                observacao TEXT
            );

            CREATE TABLE IF NOT EXISTS despachos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                filial_id INTEGER NOT NULL REFERENCES filiais(id),
                departamento_id INTEGER NOT NULL REFERENCES departamentos(id),
                item_id INTEGER NOT NULL REFERENCES itens(id),
                quantidade INTEGER NOT NULL,
                numero_chamado TEXT,
                recebido_por TEXT,
                observacao TEXT
            );

            -- Guardas no proprio banco (CHECK nao se aplica a tabelas ja criadas).
            CREATE TRIGGER IF NOT EXISTS trg_entradas_valida BEFORE INSERT ON entradas
            WHEN NEW.quantidade <= 0 OR NEW.valor_unitario < 0
            BEGIN SELECT RAISE(ABORT, 'entrada: quantidade/valor invalido'); END;

            CREATE TRIGGER IF NOT EXISTS trg_despachos_valida BEFORE INSERT ON despachos
            WHEN NEW.quantidade <= 0
            BEGIN SELECT RAISE(ABORT, 'despacho: quantidade invalida'); END;

            CREATE TRIGGER IF NOT EXISTS trg_itens_valida BEFORE INSERT ON itens
            WHEN NEW.estoque_minimo < 0
            BEGIN SELECT RAISE(ABORT, 'item: estoque minimo negativo'); END;
            """
        )
        conn.commit()
    except sqlite3.Error:
        logger.exception("Erro ao inicializar o banco de dados em %s", DB_PATH)
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

def hoje():
    """Retorna a data de hoje no formato dd/mm/aaaa."""
    return datetime.date.today().strftime("%d/%m/%Y")


def hoje_iso():
    """Retorna a data de hoje no formato ISO aaaa-mm-dd."""
    return datetime.date.today().strftime("%Y-%m-%d")


def to_iso(data_br):
    """Converte dd/mm/aaaa -> aaaa-mm-dd para ordenacao/filtro correto."""
    try:
        d = datetime.datetime.strptime(data_br.strip(), "%d/%m/%Y")
        return d.strftime("%Y-%m-%d")
    except ValueError:
        # Formato invalido — caso esperado; nao polui o log como erro.
        return None
    except Exception:
        logger.exception("Erro inesperado ao converter data BR->ISO: %r", data_br)
        return None


def to_display(data_iso):
    """Converte aaaa-mm-dd -> dd/mm/aaaa para exibicao."""
    if not data_iso:
        return ""
    try:
        d = datetime.datetime.strptime(data_iso.strip(), "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except ValueError:
        # Formato invalido — devolve a string original para a UI.
        return data_iso
    except Exception:
        logger.exception("Erro inesperado ao converter data ISO->display: %r", data_iso)
        return data_iso


def saldo_atual(item_id):
    """Retorna o saldo em estoque de um item (entradas - despachos)."""
    conn = get_conn()
    try:
        entradas = conn.execute(
            "SELECT COALESCE(SUM(quantidade), 0) FROM entradas WHERE item_id = ?",
            (item_id,),
        ).fetchone()[0]
        saidas = conn.execute(
            "SELECT COALESCE(SUM(quantidade), 0) FROM despachos WHERE item_id = ?",
            (item_id,),
        ).fetchone()[0]
        return entradas - saidas
    except Exception:
        logger.exception("Erro ao calcular saldo do item_id=%s", item_id)
        return 0
    finally:
        conn.close()


def saldo_itens():
    """Retorna dict {item_id: saldo} para todos os itens."""
    conn = get_conn()
    try:
        itens = conn.execute("SELECT id FROM itens").fetchall()
        result = {}
        for (iid,) in itens:
            ent = conn.execute(
                "SELECT COALESCE(SUM(quantidade), 0) FROM entradas WHERE item_id = ?",
                (iid,),
            ).fetchone()[0]
            sai = conn.execute(
                "SELECT COALESCE(SUM(quantidade), 0) FROM despachos WHERE item_id = ?",
                (iid,),
            ).fetchone()[0]
            result[iid] = ent - sai
        return result
    except Exception:
        logger.exception("Erro ao calcular saldo de todos os itens")
        return {}
    finally:
        conn.close()


def listar(tabela):
    """Retorna todas as linhas de uma tabela simples (filiais/departamentos)."""
    _validar_tabela(tabela)
    conn = get_conn()
    try:
        rows = conn.execute(f"SELECT id, nome FROM {tabela} ORDER BY nome").fetchall()
        return rows
    except Exception:
        logger.exception("Erro ao listar tabela %r", tabela)
        return []
    finally:
        conn.close()


def listar_itens():
    """Retorna todos os itens com id, nome, tipo, estoque_minimo."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, nome, tipo, estoque_minimo FROM itens ORDER BY nome"
        ).fetchall()
        return rows
    except Exception:
        logger.exception("Erro ao listar itens")
        return []
    finally:
        conn.close()


def _validar_data_iso(data_iso):
    """Levanta ValueError se nao for uma data ISO canonica (aaaa-mm-dd) real.

    strptime aceita '2024-1-1'; o round-trip exige o formato exato, pois o resto
    do app ordena e filtra datas como texto.
    """
    texto = str(data_iso)
    try:
        data = datetime.datetime.strptime(texto, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Data invalida: {data_iso!r}") from None
    if data.strftime("%Y-%m-%d") != texto:
        raise ValueError(f"Data invalida: {data_iso!r}")


def _validar_numero(valor, nome, minimo_exclusivo=None, minimo=None):
    """Levanta ValueError se 'valor' nao for numero finito dentro do limite."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ValueError(f"{nome} invalido: {valor!r}")
    if minimo_exclusivo is not None and valor <= minimo_exclusivo:
        raise ValueError(f"{nome} deve ser maior que {minimo_exclusivo}: {valor!r}")
    if minimo is not None and valor < minimo:
        raise ValueError(f"{nome} nao pode ser menor que {minimo}: {valor!r}")


def inserir(tabela, nome):
    """Insere em filiais ou departamentos. Retorna True, ou False se o nome ja existe.

    Qualquer outra falha do banco e propagada (nao se confunde com duplicado).
    """
    _validar_tabela(tabela)
    conn = get_conn()
    try:
        conn.execute(f"INSERT INTO {tabela} (nome) VALUES (?)", (nome,))
        conn.commit()
        return True
    except sqlite3.IntegrityError as exc:
        # Violação de UNIQUE (nome duplicado) — caso esperado, sinalizado à UI.
        logger.warning("IntegrityError ao inserir em %r (%r): %s", tabela, nome, exc)
        return False
    except Exception:
        # Falha do banco (lock, disco, ...) nao e nome duplicado: propaga.
        logger.exception("Erro inesperado ao inserir em %r (%r)", tabela, nome)
        raise
    finally:
        conn.close()


def inserir_item(nome, tipo, estoque_minimo):
    """Insere um item. Retorna True ou False (nome duplicado).

    Levanta ValueError se o estoque minimo for negativo ou nao for numero finito.
    """
    _validar_numero(estoque_minimo, "Estoque minimo", minimo=0)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO itens (nome, tipo, estoque_minimo) VALUES (?, ?, ?)",
            (nome, tipo, estoque_minimo),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError as exc:
        # Nome de item duplicado — caso esperado.
        logger.warning("IntegrityError ao inserir item %r: %s", nome, exc)
        return False
    except Exception:
        logger.exception("Erro inesperado ao inserir item %r", nome)
        return False
    finally:
        conn.close()


def excluir(tabela, item_id):
    """Exclui um registro. Retorna True ou False (FK violation ou id inexistente)."""
    _validar_tabela(tabela)
    conn = get_conn()
    try:
        cur = conn.execute(f"DELETE FROM {tabela} WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.IntegrityError as exc:
        # FK violation (registro referenciado por outra tabela).
        logger.warning("IntegrityError ao excluir de %r (id=%s): %s", tabela, item_id, exc)
        return False
    except Exception:
        logger.exception("Erro inesperado ao excluir de %r (id=%s)", tabela, item_id)
        return False
    finally:
        conn.close()


def inserir_entrada(data_iso, item_id, quantidade, fornecedor, valor_unitario, observacao):
    """Registra uma entrada de estoque (compra).

    Levanta ValueError para dado invalido (data impossivel, quantidade nao
    positiva ou nao finita, valor negativo) e sqlite3.Error para falha do banco
    (inclui IntegrityError de item inexistente). Quem chama deve tratar: retorno
    normal significa que a entrada foi gravada.
    """
    _validar_data_iso(data_iso)
    _validar_numero(quantidade, "Quantidade", minimo_exclusivo=0)
    if valor_unitario is not None:
        _validar_numero(valor_unitario, "Valor unitario", minimo=0)
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO entradas (data, item_id, quantidade, fornecedor, valor_unitario, observacao)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data_iso, item_id, quantidade, fornecedor or None, valor_unitario, observacao or None),
        )
        conn.commit()
    except sqlite3.Error:
        logger.exception(
            "Erro ao inserir entrada (item_id=%s, qtd=%s)", item_id, quantidade,
        )
        raise
    finally:
        conn.close()


def inserir_despacho(data_iso, filial_id, departamento_id, item_id, quantidade,
                     numero_chamado, recebido_por, observacao):
    """Registra um despacho para filial.

    Mesmo contrato de inserir_entrada: ValueError para dado invalido,
    sqlite3.Error para falha do banco; retorno normal = gravado.
    """
    _validar_data_iso(data_iso)
    _validar_numero(quantidade, "Quantidade", minimo_exclusivo=0)
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO despachos
               (data, filial_id, departamento_id, item_id, quantidade,
                numero_chamado, recebido_por, observacao)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (data_iso, filial_id, departamento_id, item_id, quantidade,
             numero_chamado or None, recebido_por or None, observacao or None),
        )
        conn.commit()
    except sqlite3.Error:
        logger.exception(
            "Erro ao inserir despacho (item_id=%s, filial=%s, qtd=%s)",
            item_id, filial_id, quantidade,
        )
        raise
    finally:
        conn.close()


def ultimas_entradas(limite=200):
    """Retorna as ultimas entradas registradas."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT e.id, e.data, i.nome, e.quantidade, e.fornecedor, e.valor_unitario, e.observacao
               FROM entradas e JOIN itens i ON i.id = e.item_id
               ORDER BY e.data DESC, e.id DESC LIMIT ?""",
            (limite,),
        ).fetchall()
        return rows
    except Exception:
        logger.exception("Erro ao listar ultimas entradas (limite=%s)", limite)
        return []
    finally:
        conn.close()


def ultimos_despachos(limite=200):
    """Retorna os ultimos despachos registrados."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT d.id, d.data, f.nome AS filial, dp.nome AS departamento,
                      i.nome AS item, d.quantidade,
                      d.numero_chamado, d.recebido_por, d.observacao
               FROM despachos d
               JOIN filiais f ON f.id = d.filial_id
               JOIN departamentos dp ON dp.id = d.departamento_id
               JOIN itens i ON i.id = d.item_id
               ORDER BY d.data DESC, d.id DESC LIMIT ?""",
            (limite,),
        ).fetchall()
        return rows
    except Exception:
        logger.exception("Erro ao listar ultimos despachos (limite=%s)", limite)
        return []
    finally:
        conn.close()


def estoque_atual():
    """Retorna estoque de todos os itens: (nome, tipo, estoque_minimo, entradas, saidas, saldo)."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT i.id, i.nome, i.tipo, i.estoque_minimo,
                      COALESCE((SELECT SUM(quantidade) FROM entradas WHERE item_id=i.id), 0) AS ent,
                      COALESCE((SELECT SUM(quantidade) FROM despachos WHERE item_id=i.id), 0) AS sai
               FROM itens i ORDER BY i.nome"""
        ).fetchall()

        result = []
        for r in rows:
            saldo = r["ent"] - r["sai"]
            result.append({
                "id": r["id"], "nome": r["nome"], "tipo": r["tipo"],
                "minimo": r["estoque_minimo"], "entradas": r["ent"],
                "saidas": r["sai"], "saldo": saldo,
            })
        return result
    except Exception:
        # Propaga: [] seria exibido como "estoque vazio" quando o banco falhou.
        logger.exception("Erro ao calcular estoque atual")
        raise
    finally:
        conn.close()


def relatorio_despachos(filtro):
    """
    Consulta de despachos com filtros.
    filtro: dict com chaves opcionais: de, ate, filial, departamento, item.
    Retorna lista de dicts.
    """
    sql = """
        SELECT d.id, d.data, f.nome AS filial, dp.nome AS departamento,
               i.nome AS item, d.quantidade, d.numero_chamado, d.recebido_por
        FROM despachos d
        JOIN filiais f ON f.id = d.filial_id
        JOIN departamentos dp ON dp.id = d.departamento_id
        JOIN itens i ON i.id = d.item_id
        WHERE 1=1
    """
    params = []

    if filtro.get("de"):
        sql += " AND d.data >= ?"
        params.append(filtro["de"])
    if filtro.get("ate"):
        sql += " AND d.data <= ?"
        params.append(filtro["ate"])
    if filtro.get("filial"):
        sql += " AND f.nome = ?"
        params.append(filtro["filial"])
    if filtro.get("departamento"):
        sql += " AND dp.nome = ?"
        params.append(filtro["departamento"])
    if filtro.get("item"):
        sql += " AND i.nome = ?"
        params.append(filtro["item"])

    sql += " ORDER BY d.data DESC, d.id DESC"

    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return rows
    except Exception:
        logger.exception("Erro ao gerar relatorio de despachos (filtro=%r)", filtro)
        return []
    finally:
        conn.close()


def dashboard_stats():
    """Retorna estatisticas para o dashboard."""
    conn = get_conn()
    try:
        total_filiais = conn.execute("SELECT COUNT(*) FROM filiais").fetchone()[0]
        total_deptos = conn.execute("SELECT COUNT(*) FROM departamentos").fetchone()[0]
        total_itens = conn.execute("SELECT COUNT(*) FROM itens").fetchone()[0]
        total_entradas = conn.execute("SELECT COALESCE(SUM(quantidade), 0) FROM entradas").fetchone()[0]
        total_despachos = conn.execute("SELECT COALESCE(SUM(quantidade), 0) FROM despachos").fetchone()[0]

        # Itens com estoque abaixo do minimo (calcula saldo em Python para evitar
        # HAVING sobre query sem GROUP BY, que nao e suportado no SQLite em alguns casos)
        alertas = []
        for i in conn.execute(
            """SELECT i.nome, i.estoque_minimo,
                      COALESCE((SELECT SUM(quantidade) FROM entradas WHERE item_id=i.id), 0) -
                      COALESCE((SELECT SUM(quantidade) FROM despachos WHERE item_id=i.id), 0) AS saldo
               FROM itens i
               WHERE i.estoque_minimo > 0"""
        ).fetchall():
            if i["saldo"] <= i["estoque_minimo"]:
                alertas.append(i)

        # Ultimos despachos
        ult_desp = conn.execute(
            """SELECT d.data, f.nome AS filial, dp.nome AS departamento,
                      i.nome AS item, d.quantidade, d.recebido_por
               FROM despachos d
               JOIN filiais f ON f.id = d.filial_id
               JOIN departamentos dp ON dp.id = d.departamento_id
               JOIN itens i ON i.id = d.item_id
               ORDER BY d.data DESC, d.id DESC LIMIT 5"""
        ).fetchall()

        # Ultimas entradas
        ult_ent = conn.execute(
            """SELECT e.data, i.nome AS nome, e.quantidade, e.fornecedor
               FROM entradas e JOIN itens i ON i.id = e.item_id
               ORDER BY e.data DESC, e.id DESC LIMIT 5"""
        ).fetchall()

        # Calcula saldos separados por tipo de unidade
        saldo_litros = 0
        saldo_unidades = 0
        for i in conn.execute(
            """SELECT i.tipo,
                      COALESCE((SELECT SUM(quantidade) FROM entradas WHERE item_id=i.id), 0) -
                      COALESCE((SELECT SUM(quantidade) FROM despachos WHERE item_id=i.id), 0) AS saldo
               FROM itens i"""
        ).fetchall():
            if i["tipo"].lower() == "tinta":
                saldo_litros += i["saldo"]
            else:
                saldo_unidades += i["saldo"]

        return {
            "total_filiais": total_filiais,
            "total_deptos": total_deptos,
            "total_itens": total_itens,
            "total_entradas": total_entradas,
            "total_despachos": total_despachos,
            "saldo_litros": saldo_litros,
            "saldo_unidades": int(saldo_unidades),
            "alertas": alertas,
            "ult_despachos": ult_desp,
            "ult_entradas": ult_ent,
        }
    except Exception:
        logger.exception("Erro ao gerar estatisticas do dashboard")
        # Retorna estrutura neutra para a UI não quebrar com KeyError.
        return {
            "total_filiais": 0,
            "total_deptos": 0,
            "total_itens": 0,
            "total_entradas": 0,
            "total_despachos": 0,
            "saldo_litros": 0,
            "saldo_unidades": 0,
            "alertas": [],
            "ult_despachos": [],
            "ult_entradas": [],
        }
    finally:
        conn.close()
