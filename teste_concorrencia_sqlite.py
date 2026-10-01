#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de condicoes de corrida / concorrencia no SQLite em db.py.

Detecta:
  - sqlite3.OperationalError "database is locked"
  - sqlite3.DatabaseError / corrupcao de banco
  - Falhas silenciosas (funcoes que engolem excecoes de concorrencia)
  - Perda de dados (count esperado vs real)
  - Excecoes de concorrencia em geral

Rode via:  python teste_concorrencia_sqlite.py
"""

import os
import sys
import time
import shutil
import tempfile
import threading
import sqlite3
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# Adiciona o diretorio do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db as db_module

# ---------------------------------------------------------------------------
# Setup: banco de teste em arquivo temporario (nao toca no banco de producao)
# ---------------------------------------------------------------------------
TEST_DIR = tempfile.mkdtemp(prefix="concurrency_test_")
TEST_DB = os.path.join(TEST_DIR, "test_concurrency.db")

# Monkeypatch DB_PATH para apontar para o banco de teste
db_module.DB_PATH = TEST_DB
db_module.init_db()

# Dados base para FKs
conn = db_module.get_conn()
conn.execute("INSERT INTO filiais (nome) VALUES ('Filial Teste 1')")
conn.execute("INSERT INTO filiais (nome) VALUES ('Filial Teste 2')")
conn.execute("INSERT INTO departamentos (nome) VALUES ('Depto Teste 1')")
conn.execute("INSERT INTO departamentos (nome) VALUES ('Depto Teste 2')")
conn.execute("INSERT INTO itens (nome, tipo, estoque_minimo) VALUES ('Item Tinta', 'Tinta', 1)")
conn.execute("INSERT INTO itens (nome, tipo, estoque_minimo) VALUES ('Item Toner', 'Toner', 5)")
conn.execute("INSERT INTO itens (nome, tipo, estoque_minimo) VALUES ('Item Cartucho', 'Cartucho', 2)")
conn.commit()
conn.close()

conn = db_module.get_conn()
filial_ids = [r[0] for r in conn.execute("SELECT id FROM filiais ORDER BY id").fetchall()]
depto_ids = [r[0] for r in conn.execute("SELECT id FROM departamentos ORDER BY id").fetchall()]
item_ids = [r[0] for r in conn.execute("SELECT id FROM itens ORDER BY id").fetchall()]
conn.close()

# ---------------------------------------------------------------------------
# Coletor de falhas e contadores (thread-safe)
# ---------------------------------------------------------------------------
failures = []
failures_lock = threading.Lock()
counters = {
    "writes_attempted": 0,
    "writes_succeeded": 0,
    "reads_attempted": 0,
    "reads_succeeded": 0,
}
counters_lock = threading.Lock()


def record_failure(category, thread_name, exc_trace, extra=""):
    with failures_lock:
        failures.append({
            "category": category,
            "thread": thread_name,
            "trace": exc_trace,
            "extra": extra,
        })


def inc_counter(key, delta=1):
    with counters_lock:
        counters[key] = counters.get(key, 0) + delta


# ---------------------------------------------------------------------------
# Workers de ESCRITA (via db.py — que engole excecoes)
# ---------------------------------------------------------------------------

def worker_inserir_entrada(thread_id, num_ops=50):
    """Insere entradas repetidamente via db.inserir_entrada (que engola erros)."""
    tname = f"entrada-{thread_id}"
    for i in range(num_ops):
        inc_counter("writes_attempted")
        try:
            db_module.inserir_entrada(
                data_iso="2026-09-14",
                item_id=item_ids[i % len(item_ids)],
                quantidade=10,
                fornecedor=f"Fornecedor {thread_id}-{i}",
                valor_unitario=25.50,
                observacao=f"Obs entrada {thread_id}-{i}",
            )
            # inserir_entrada NAO retorna status — nao sabemos se gravou
            inc_counter("writes_succeeded")
        except Exception:
            # So chega aqui se houver erro ANTES do try interno do db.py
            record_failure("entrada_write_unexpected", tname, traceback.format_exc())


def worker_inserir_despacho(thread_id, num_ops=50):
    """Insere despachos repetidamente via db.inserir_despacho (que engola erros)."""
    tname = f"despacho-{thread_id}"
    for i in range(num_ops):
        inc_counter("writes_attempted")
        try:
            db_module.inserir_despacho(
                data_iso="2026-09-14",
                filial_id=filial_ids[i % len(filial_ids)],
                departamento_id=depto_ids[i % len(depto_ids)],
                item_id=item_ids[i % len(item_ids)],
                quantidade=5,
                numero_chamado=f"CH-{thread_id}-{i}",
                recebido_por=f"Recebedor {thread_id}",
                observacao=f"Obs despacho {thread_id}-{i}",
            )
            inc_counter("writes_succeeded")
        except Exception:
            record_failure("despacho_write_unexpected", tname, traceback.format_exc())


def worker_inserir_item(thread_id, num_ops=20):
    """Insere itens com nome unico."""
    tname = f"item-{thread_id}"
    for i in range(num_ops):
        inc_counter("writes_attempted")
        try:
            nome = f"Item Conc {thread_id}-{i}-{time.time_ns()}"
            result = db_module.inserir_item(nome, "Toner", 5)
            if result:
                inc_counter("writes_succeeded")
        except Exception:
            record_failure("item_write_unexpected", tname, traceback.format_exc())


def worker_inserir_filial(thread_id, num_ops=20):
    """Insere filiais com nome unico."""
    tname = f"filial-{thread_id}"
    for i in range(num_ops):
        inc_counter("writes_attempted")
        try:
            nome = f"Filial Conc {thread_id}-{i}-{time.time_ns()}"
            result = db_module.inserir("filiais", nome)
            if result:
                inc_counter("writes_succeeded")
        except Exception:
            record_failure("filial_write_unexpected", tname, traceback.format_exc())


def worker_excluir_reinserir(thread_id, num_ops=20):
    """Cria e exclui itens repetidamente."""
    tname = f"excluir-{thread_id}"
    for i in range(num_ops):
        inc_counter("writes_attempted")
        try:
            nome = f"Temp Item {thread_id}-{i}-{time.time_ns()}"
            created = db_module.inserir_item(nome, "Cartucho", 0)
            if created:
                conn = db_module.get_conn()
                try:
                    row = conn.execute(
                        "SELECT id FROM itens WHERE nome = ?", (nome,)
                    ).fetchone()
                    if row:
                        db_module.excluir("itens", row[0])
                finally:
                    conn.close()
            inc_counter("writes_succeeded")
        except Exception:
            record_failure("excluir_write_unexpected", tname, traceback.format_exc())


# ---------------------------------------------------------------------------
# Workers de LEITURA (via db.py)
# ---------------------------------------------------------------------------

def worker_leitura(thread_id, num_ops=100):
    """Le varios dados repetidamente."""
    tname = f"reader-{thread_id}"
    for i in range(num_ops):
        inc_counter("reads_attempted")
        try:
            op = i % 7
            if op == 0:
                db_module.saldo_atual(item_ids[i % len(item_ids)])
            elif op == 1:
                db_module.listar("filiais")
            elif op == 2:
                db_module.listar_itens()
            elif op == 3:
                db_module.estoque_atual()
            elif op == 4:
                db_module.dashboard_stats()
            elif op == 5:
                db_module.ultimas_entradas(50)
            elif op == 6:
                db_module.ultimos_despachos(50)
            inc_counter("reads_succeeded")
        except Exception:
            record_failure("read", tname, traceback.format_exc())


def worker_relatorio(thread_id, num_ops=50):
    """Gera relatorios repetidamente."""
    tname = f"relatorio-{thread_id}"
    for i in range(num_ops):
        inc_counter("reads_attempted")
        try:
            filtro = {}
            if i % 3 == 0:
                filtro["filial"] = "Filial Teste 1"
            if i % 3 == 1:
                filtro["de"] = "2026-01-01"
            db_module.relatorio_despachos(filtro)
            inc_counter("reads_succeeded")
        except Exception:
            record_failure("relatorio_read", tname, traceback.format_exc())


# ---------------------------------------------------------------------------
# Worker de transacao longa (segura lock de escrita por N segundos)
# ---------------------------------------------------------------------------

def worker_long_transaction(thread_id, duration=2.0):
    """Abre uma transacao de escrita e segura o lock por 'duration' segundos."""
    tname = f"longtx-{thread_id}"
    inc_counter("writes_attempted")
    conn = db_module.get_conn()
    try:
        conn.execute(
            "INSERT INTO filiais (nome) VALUES (?)",
            (f"LongTX {thread_id}-{time.time_ns()}",),
        )
        time.sleep(duration)
        conn.commit()
        inc_counter("writes_succeeded")
    except Exception:
        record_failure("long_tx", tname, traceback.format_exc())
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Worker de ESCRITA CRUA (sqlite3 direto — NAO engola erros)
# Este worker detecta erros de lock que db.py engole silenciosamente
# ---------------------------------------------------------------------------

def worker_raw_write(thread_id, num_ops=30, timeout=0.1):
    """
    Escreve diretamente via sqlite3 com timeout curto.
    Diferente das funcoes db.py, este worker NAO engola excecoes —
    captura e reporta todos os "database is locked" e outras excecoes.
    """
    tname = f"raw-{thread_id}"
    for i in range(num_ops):
        inc_counter("writes_attempted")
        conn = sqlite3.connect(db_module.DB_PATH, timeout=timeout)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """INSERT INTO entradas
                   (data, item_id, quantidade, fornecedor, valor_unitario, observacao)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("2026-09-14", item_ids[i % len(item_ids)], 1,
                 f"Raw {thread_id}-{i}", 1.0, ""),
            )
            conn.commit()
            inc_counter("writes_succeeded")
        except sqlite3.OperationalError as e:
            record_failure(
                "raw_write_locked", tname,
                traceback.format_exc(), str(e),
            )
        except sqlite3.DatabaseError as e:
            record_failure(
                "raw_write_dberror", tname,
                traceback.format_exc(), str(e),
            )
        except Exception as e:
            record_failure(
                "raw_write_other", tname,
                traceback.format_exc(), str(e),
            )
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Worker de LEITURA CRUA (sqlite3 direto com timeout curto)
# ---------------------------------------------------------------------------

def worker_raw_read(thread_id, num_ops=50, timeout=0.1):
    """Le diretamente via sqlite3 com timeout curto para detectar locks de leitura."""
    tname = f"rawread-{thread_id}"
    for i in range(num_ops):
        inc_counter("reads_attempted")
        conn = sqlite3.connect(db_module.DB_PATH, timeout=timeout)
        try:
            conn.execute("SELECT COUNT(*) FROM entradas").fetchone()
            conn.execute("SELECT COUNT(*) FROM despachos").fetchone()
            conn.execute("SELECT COUNT(*) FROM itens").fetchone()
            inc_counter("reads_succeeded")
        except sqlite3.OperationalError as e:
            record_failure(
                "raw_read_locked", tname,
                traceback.format_exc(), str(e),
            )
        except Exception as e:
            record_failure(
                "raw_read_other", tname,
                traceback.format_exc(), str(e),
            )
        finally:
            conn.close()


# ===========================================================================
# Execucao dos testes
# ===========================================================================

def main():
    print("=" * 80)
    print("TESTE DE CONCORRENCIA SQLite EM db.py")
    print("=" * 80)
    print(f"Banco de teste: {TEST_DB}")

    # Verifica modo de journal (esperado: rollback journal = "delete")
    conn = db_module.get_conn()
    jmode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    print(f"PRAGMA journal_mode: {jmode} (nao-WAL = sujeito a locks de escrita)")
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    print(f"PRAGMA foreign_keys: {fk}")
    conn.close()

    # -----------------------------------------------------------------------
    # Teste 1: Escrita concorrente pesada
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Teste 1: Escrita concorrente pesada (entradas + despachos + itens + filiais)")
    print("-" * 80)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = []
        for tid in range(5):
            futures.append(pool.submit(worker_inserir_entrada, tid, 50))
        for tid in range(5):
            futures.append(pool.submit(worker_inserir_despacho, tid, 50))
        for tid in range(3):
            futures.append(pool.submit(worker_inserir_item, tid, 20))
        for tid in range(2):
            futures.append(pool.submit(worker_inserir_filial, tid, 20))
        for f in as_completed(futures):
            f.result()
    t1 = time.time()
    print(f"  Duracao: {t1 - t0:.2f}s")
    print(f"  Escritas: tentadas={counters['writes_attempted']}, "
          f"bem-sucedidas={counters['writes_succeeded']}")

    # Conta registros reais apos Teste 1
    conn = db_module.get_conn()
    entradas_t1 = conn.execute("SELECT COUNT(*) FROM entradas").fetchone()[0]
    despachos_t1 = conn.execute("SELECT COUNT(*) FROM despachos").fetchone()[0]
    conn.close()
    expected_ent_t1 = 5 * 50  # 250
    expected_desp_t1 = 5 * 50  # 250
    lost_ent_t1 = expected_ent_t1 - entradas_t1
    lost_desp_t1 = expected_desp_t1 - despachos_t1
    print(f"  Entradas: esperadas={expected_ent_t1}, reais={entradas_t1}, "
          f"perda silenciosa={lost_ent_t1}")
    print(f"  Despachos: esperados={expected_desp_t1}, reais={despachos_t1}, "
          f"perda silenciosa={lost_desp_t1}")
    if lost_ent_t1 > 0:
        print(f"  >>> {lost_ent_t1} entradas PERDIDAS SILÊNCIOSAMENTE "
              f"(db.inserir_entrada engola sqlite3.OperationalError)")
    if lost_desp_t1 > 0:
        print(f"  >>> {lost_desp_t1} despachos PERDIDOS SILÊNCIOSAMENTE "
              f"(db.inserir_despacho engola sqlite3.OperationalError)")

    # -----------------------------------------------------------------------
    # Teste 2: Leitura + Escrita simultaneas
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Teste 2: Leitura + Escrita simultaneas (readers + writers concorrentes)")
    print("-" * 80)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = []
        for tid in range(10):
            futures.append(pool.submit(worker_leitura, tid, 100))
        for tid in range(5):
            futures.append(pool.submit(worker_relatorio, tid, 50))
        for tid in range(5):
            futures.append(pool.submit(worker_inserir_entrada, tid, 50))
        for tid in range(5):
            futures.append(pool.submit(worker_inserir_despacho, tid, 50))
        for f in as_completed(futures):
            f.result()
    t1 = time.time()
    print(f"  Duracao: {t1 - t0:.2f}s")
    print(f"  Escritas totais: tentadas={counters['writes_attempted']}, "
          f"bem-sucedidas={counters['writes_succeeded']}")
    print(f"  Leituras totais: tentadas={counters['reads_attempted']}, "
          f"bem-sucedidas={counters['reads_succeeded']}")

    # -----------------------------------------------------------------------
    # Teste 3: Escrita + Exclusao concorrente
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Teste 3: Escrita + Exclusao concorrente")
    print("-" * 80)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = []
        for tid in range(5):
            futures.append(pool.submit(worker_excluir_reinserir, tid, 20))
        for tid in range(5):
            futures.append(pool.submit(worker_inserir_entrada, tid, 30))
        for f in as_completed(futures):
            f.result()
    t1 = time.time()
    print(f"  Duracao: {t1 - t0:.2f}s")

    # -----------------------------------------------------------------------
    # Teste 4: Transacao longa + escrita concorrente
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Teste 4: Transacao longa (segura lock 2s) + escrita concorrente")
    print("-" * 80)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = []
        for tid in range(3):
            futures.append(pool.submit(worker_long_transaction, tid, 2.0))
        for tid in range(6):
            futures.append(pool.submit(worker_inserir_entrada, tid, 30))
        for tid in range(6):
            futures.append(pool.submit(worker_inserir_despacho, tid, 30))
        for f in as_completed(futures):
            f.result()
    t1 = time.time()
    print(f"  Duracao: {t1 - t0:.2f}s")

    # -----------------------------------------------------------------------
    # Teste 5: Escrita crua (timeout=0.1s — detecta locks que db.py engole)
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Teste 5: Escrita crua via sqlite3 direto (timeout=0.1s)")
    print("         Detecta 'database is locked' que db.py engola silenciosamente")
    print("-" * 80)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = []
        for tid in range(10):
            futures.append(pool.submit(worker_raw_write, tid, 30, 0.1))
        for tid in range(5):
            futures.append(pool.submit(worker_inserir_entrada, tid, 30))
        for tid in range(5):
            futures.append(pool.submit(worker_leitura, tid, 50))
        for f in as_completed(futures):
            f.result()
    t1 = time.time()
    print(f"  Duracao: {t1 - t0:.2f}s")

    # -----------------------------------------------------------------------
    # Teste 6: Leitura crua + escrita concorrente (timeout curto)
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Teste 6: Leitura crua (timeout=0.1s) + escrita concorrente")
    print("-" * 80)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = []
        for tid in range(10):
            futures.append(pool.submit(worker_raw_read, tid, 50, 0.1))
        for tid in range(5):
            futures.append(pool.submit(worker_inserir_entrada, tid, 30))
        for tid in range(5):
            futures.append(pool.submit(worker_inserir_despacho, tid, 30))
        for f in as_completed(futures):
            f.result()
    t1 = time.time()
    print(f"  Duracao: {t1 - t0:.2f}s")

    # -----------------------------------------------------------------------
    # Teste 7: Stress maximo (50 threads, leitura + escrita mista)
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("Teste 7: Stress maximo (50 threads, leitura + escrita mista)")
    print("-" * 80)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = []
        for tid in range(20):
            futures.append(pool.submit(worker_inserir_entrada, tid, 30))
        for tid in range(20):
            futures.append(pool.submit(worker_inserir_despacho, tid, 30))
        for tid in range(10):
            futures.append(pool.submit(worker_leitura, tid, 50))
        for f in as_completed(futures):
            f.result()
    t1 = time.time()
    print(f"  Duracao: {t1 - t0:.2f}s")
    print(f"  Escritas totais: tentadas={counters['writes_attempted']}, "
          f"bem-sucedidas={counters['writes_succeeded']}")
    print(f"  Leituras totais: tentadas={counters['reads_attempted']}, "
          f"bem-sucedidas={counters['reads_succeeded']}")

    # ===================================================================
    # Verificacao de integridade e perda de dados
    # ===================================================================
    print("\n" + "=" * 80)
    print("VERIFICACAO DE INTEGRIDADE E PERDA DE DADOS")
    print("=" * 80)

    conn = db_module.get_conn()
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"PRAGMA integrity_check: {integrity}")
    quick = conn.execute("PRAGMA quick_check").fetchone()[0]
    print(f"PRAGMA quick_check: {quick}")

    filiais_count = conn.execute("SELECT COUNT(*) FROM filiais").fetchone()[0]
    deptos_count = conn.execute("SELECT COUNT(*) FROM departamentos").fetchone()[0]
    itens_count = conn.execute("SELECT COUNT(*) FROM itens").fetchone()[0]
    entradas_count = conn.execute("SELECT COUNT(*) FROM entradas").fetchone()[0]
    despachos_count = conn.execute("SELECT COUNT(*) FROM despachos").fetchone()[0]
    conn.close()

    print(f"\nContagem de registros no banco:")
    print(f"  Filiais:       {filiais_count}")
    print(f"  Departamentos: {deptos_count}")
    print(f"  Itens:         {itens_count}")
    print(f"  Entradas:      {entradas_count}")
    print(f"  Despachos:     {despachos_count}")

    # Calculo esperado de entradas via db.inserir_entrada:
    #   T1: 5 x 50 = 250
    #   T2: 5 x 50 = 250
    #   T3: 5 x 30 = 150
    #   T4: 6 x 30 = 180
    #   T5: 5 x 30 = 150  (db.inserir_entrada; raw_write vai pra entradas tb)
    #   T5 raw: 10 x 30 = 300 (raw writes com timeout=0.1)
    #   T7: 20 x 30 = 600
    #   Total esperado (sem perdas): 250 + 250 + 150 + 180 + 150 + 300 + 600 = 1880
    expected_entradas = 250 + 250 + 150 + 180 + 150 + 300 + 600
    lost_entradas = expected_entradas - entradas_count
    print(f"\nAnalise de perda de dados (entradas):")
    print(f"  Esperado: {expected_entradas}")
    print(f"  Real:     {entradas_count}")
    print(f"  Perda:    {lost_entradas}")
    if lost_entradas > 0:
        print(f"  >>> {lost_entradas} entradas PERDIDAS — db.inserir_entrada e "
              f"raw writes falharam por concorrencia")
        print(f"      db.inserir_entrada engola a excecao (catch Exception, log, "
              f"nao relanca) — caller NUNCA sabe que falhou")

    # Calculo esperado de despachos via db.inserir_despacho:
    #   T1: 5 x 50 = 250
    #   T2: 5 x 50 = 250
    #   T4: 6 x 30 = 180
    #   T6: 5 x 30 = 150
    #   T7: 20 x 30 = 600
    #   Total esperado: 250 + 250 + 180 + 150 + 600 = 1430
    expected_despachos = 250 + 250 + 180 + 150 + 600
    lost_despachos = expected_despachos - despachos_count
    print(f"\nAnalise de perda de dados (despachos):")
    print(f"  Esperado: {expected_despachos}")
    print(f"  Real:     {despachos_count}")
    print(f"  Perda:    {lost_despachos}")
    if lost_despachos > 0:
        print(f"  >>> {lost_despachos} despachos PERDIDOS — db.inserir_despacho "
              f"engola a excecao de concorrencia")

    # ===================================================================
    # Relatorio de falhas
    # ===================================================================
    print("\n" + "=" * 80)
    print("RELATORIO DE FALHAS DE CONCORRENCIA")
    print("=" * 80)

    if not failures:
        print("Nenhuma excecao de concorrencia explicita detectada nos workers raw.")
        print("(Mas verifique a secao de perda de dados acima — perdas silenciosas "
              "na contam como 'falhas' aqui)")
    else:
        print(f"{len(failures)} falha(s) detectada(s):\n")
        by_category = {}
        for f in failures:
            by_category.setdefault(f["category"], []).append(f)

        for cat, items in sorted(by_category.items()):
            print(f"--- Categoria: {cat} ({len(items)} ocorrencia(s)) ---")
            for item in items[:3]:
                print(f"  Thread: {item['thread']}")
                if item["extra"]:
                    print(f"  Erro: {item['extra']}")
                print(f"  Trace:")
                for line in item["trace"].strip().split("\n"):
                    print(f"    {line}")
                print()
            if len(items) > 3:
                print(f"  ... e mais {len(items) - 3} ocorrencia(s) nesta categoria\n")

    # ===================================================================
    # Limpeza
    # ===================================================================
    print("=" * 80)
    print("LIMPEZA")
    print("=" * 80)
    try:
        shutil.rmtree(TEST_DIR)
        print(f"Diretorio de teste removido: {TEST_DIR}")
    except Exception as e:
        print(f"Nao foi possivel remover {TEST_DIR}: {e}")

    print("\n" + "=" * 80)
    print("FIM DO TESTE")
    print("=" * 80)


if __name__ == "__main__":
    main()
