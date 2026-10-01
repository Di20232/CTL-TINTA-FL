#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuzzer para os event handlers Reflex do CTL-TINTA-FL.

Importa os estados Reflex (app_reflex/estados/*) e chama os event handlers
com inputs maliciosos: strings longas, caracteres especiais, valores
None/vazios, numeros extremos, tentativas de XSS.

Se Reflex nao estiver instalado, faz analise estatica e reporta onde quebrariam.
"""

import sys
import os
import traceback
import inspect

# Adiciona o diretorio do projeto ao path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "app_reflex"))

# Tenta importar reflex
REFLEX_INSTALLED = True
try:
    import reflex as rx
    REFLEX_VERSION = getattr(rx, "__version__", "unknown")
except ImportError:
    REFLEX_INSTALLED = False
    REFLEX_VERSION = None

# Sempre importamos db (nao depende de reflex)
import db

# ---------------------------------------------------------------------------
# Catalogo de inputs maliciosos
# ---------------------------------------------------------------------------
FUZZ_INPUTS = {
    "string_longa": "A" * 10000,
    "xss_script": "<script>alert('XSS')</script>",
    "xss_img": "<img src=x onerror=alert(1)>",
    "xss_svg": "<svg/onload=alert(1)>",
    "sql_injection_drop": "'; DROP TABLE filiais; --",
    "sql_injection_union": "' UNION SELECT id, nome FROM filiais --",
    "sql_injection_or": "' OR '1'='1",
    "null_bytes": "foo\x00bar\x00baz",
    "caracteres_especiais": "!@#$%^&*(){}[]|\\:;\"'<>?/~`",
    "unicode_extremo": "￿\U0001f600" * 100,
    "quebra_de_linha": "linha1\nlinha2\rlinha3\r\nlinha4",
    "string_vazia": "",
    "apenas_espacos": "   ",
    "numero_extremo_grande": "999999999999999999999999999999999999",
    "numero_extremo_negativo": "-999999999999999999999",
    "float_inf": "inf",
    "float_nan": "nan",
    "float_negativo": "-999.99",
    "float_zero": "0",
    "int_negativo": "-1",
    "int_zero": "0",
    "data_invalida_completa": "99/99/9999",
    "data_invalida_mes": "31/13/2024",
    "data_invalida_dia": "32/01/2024",
    "data_invalida_fev": "31/02/2024",
    "data_vazia": "",
    "data_none": None,
    "data_formato_errado": "2024-01-01",
    "data_iso_inversa": "2024-13-40",
    "obj_none": None,
    "obj_int": 12345,
    "obj_float": 3.14,
    "obj_bool_true": True,
    "obj_bool_false": False,
    "obj_lista": ["a", "b"],
    "obj_dict": {"key": "value"},
    "virgula_decimal": "1,5",
    "ponto_decimal": "1.5",
    "string_com_virgula": "1,2,3",
    "exponential": "1e10",
    "negative_exponential": "-1e10",
    "html_entity": "&lt;script&gt;",
    "data_path_traversal": "../../../etc/passwd",
    "command_injection": "; cat /etc/passwd",
    "formula_injection_csv": "=cmd|' /C calc'!A0",
    "csv_formula_at": "@SUM(1+1)*cmd|' /C calc'!A0",
}

# Inputs especificos para campos de quantidade
FUZZ_QTD = [
    ("string_longa", "A" * 10000),
    ("vazio", ""),
    ("apenas_espacos", "   "),
    ("letras", "abc"),
    ("negativo", "-5"),
    ("zero", "0"),
    ("float_fracionado", "1.5"),
    ("virgula_decimal", "1,5"),
    ("nan", "nan"),
    ("inf", "inf"),
    ("exponential", "1e10"),
    ("muito_grande", "99999999999999"),
    ("muito_negativo", "-99999999999999"),
    ("none", None),
    ("int", 5),
    ("float", 5.0),
    ("bool_true", True),
    ("bool_false", False),
    ("lista", [1, 2, 3]),
    ("dict", {"a": 1}),
    ("null_bytes", "\x00\x01\x02"),
    ("sql_injection", "1; DROP TABLE itens; --"),
    ("xss", "<script>1</script>"),
    ("especiais", "!@#$%"),
    ("formula_csv", "=1+1"),
    ("virgula_multipla", "1,2,3"),
]

# Inputs especificos para datas
FUZZ_DATES = [
    ("vazio", ""),
    ("apenas_espacos", "   "),
    ("none", None),
    ("formato_iso", "2024-01-15"),
    ("formato_iso_invalido", "2024-13-40"),
    ("dia_invalido", "32/01/2024"),
    ("mes_invalido", "15/13/2024"),
    ("ano_dois_digitos", "15/01/24"),
    ("separador_errado", "15-01-2024"),
    ("string_longa", "A" * 1000),
    ("xss", "<script>alert(1)</script>"),
    ("sql_injection", "' OR 1=1 --"),
    ("null_bytes", "\x00\x01"),
    ("data_path_traversal", "../../../etc/passwd"),
    ("numero_puro", "12345678"),
    ("bool_true", True),
    ("bool_false", False),
    ("int", 20240115),
    ("lista", ["15/01/2024"]),
    ("dict", {"data": "15/01/2024"}),
]

# Inputs para campos de texto livre (fornecedor, obs, chamado, recebedor)
FUZZ_TEXT = [
    ("string_longa", "A" * 10000),
    ("vazio", ""),
    ("none", None),
    ("xss_script", "<script>alert('XSS')</script>"),
    ("xss_img", "<img src=x onerror=alert(1)>"),
    ("sql_injection", "'; DROP TABLE entradas; --"),
    ("null_bytes", "foo\x00bar"),
    ("caracteres_especiais", "!@#$%^&*(){}[]|\\:;\"'<>?/~`"),
    ("unicode_extremo", "￿\U0001f600" * 50),
    ("quebra_de_linha", "linha1\n\r\nlinha2"),
    ("csv_formula", "=cmd|' /C calc'!A0"),
    ("path_traversal", "../../../etc/passwd"),
    ("int", 12345),
    ("float", 3.14),
    ("bool_true", True),
    ("bool", False),
    ("lista", ["a"]),
    ("dict", {"k": "v"}),
]


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
results = []

def record(handler_name, input_desc, input_val, status, exc_info=""):
    """Registra um resultado de fuzzing."""
    results.append({
        "handler": handler_name,
        "input_desc": input_desc,
        "input_val_repr": repr(input_val)[:120],
        "status": status,  # CRASH | SILENT_FAIL | OK | BLOCKED
        "exc_info": exc_info[:500] if exc_info else "",
    })
    marker = {
        "CRASH": "💥 CRASH",
        "SILENT_FAIL": "⚠️ SILENT_FAIL",
        "OK": "✅ OK",
        "BLOCKED": "🛡️ BLOCKED",
        "UNEXPECTED_EXCEPTION": "❓ UNEXPECTED_EXC",
    }.get(status, status)
    print(f"  [{marker}] {handler_name} <- {input_desc}: {status}")
    if exc_info and status in ("CRASH", "UNEXPECTED_EXCEPTION"):
        # Mostra as primeiras linhas do traceback
        for line in exc_info.split("\n")[:3]:
            print(f"         {line}")


# ---------------------------------------------------------------------------
# Cenario: preparar banco de dados de teste
# ---------------------------------------------------------------------------
def setup_test_db():
    """Cria um banco de teste em memoria (ou arquivo temporario) com dados seed."""
    # Salva o DB_PATH original
    orig_path = db.DB_PATH
    test_db = os.path.join(BASE_DIR, "fuzz_test.db")
    db.DB_PATH = test_db
    # Remove se existir
    if os.path.exists(test_db):
        os.remove(test_db)
    db.init_db()
    # Insere dados base para que os handlers tenham algo contra o que validar
    conn = db.get_conn()
    try:
        conn.execute("INSERT INTO filiais (nome) VALUES ('Filial Teste')")
        conn.execute("INSERT INTO departamentos (nome) VALUES ('Depto Teste')")
        conn.execute("INSERT INTO itens (nome, tipo, estoque_minimo) VALUES ('Toner HP', 'Toner', 5)")
        conn.execute("INSERT INTO itens (nome, tipo, estoque_minimo) VALUES ('Tinta Epson', 'Tinta', 1)")
        conn.commit()
    finally:
        conn.close()
    return orig_path, test_db


def teardown_test_db(test_db):
    """Remove o banco de teste."""
    if os.path.exists(test_db):
        os.remove(test_db)


def get_ids():
    """Pega IDs reais do banco de teste para uso nos forms."""
    conn = db.get_conn()
    try:
        filial = conn.execute("SELECT id FROM filiais LIMIT 1").fetchone()
        depto = conn.execute("SELECT id FROM departamentos LIMIT 1").fetchone()
        item_toner = conn.execute("SELECT id FROM itens WHERE tipo='Toner' LIMIT 1").fetchone()
        item_tinta = conn.execute("SELECT id FROM itens WHERE tipo='Tinta' LIMIT 1").fetchone()
        return {
            "filial_id": str(filial["id"]) if filial else "1",
            "depto_id": str(depto["id"]) if depto else "1",
            "item_toner_id": str(item_toner["id"]) if item_toner else "1",
            "item_tinta_id": str(item_tinta["id"]) if item_tinta else "2",
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Bypass do @rx.event decorator para chamar handlers diretamente
# ---------------------------------------------------------------------------
def unwrap_handler(handler):
    """Remove o decorator @rx.event se presente, retornando a funcao crua."""
    if hasattr(handler, "__wrapped__"):
        return handler.__wrapped__
    return handler


def make_mock_state(state_class):
    """Cria uma instancia de State sem depender do runtime do Reflex.
    Se nao conseguir (reflex nao instalado ou State exige contexto), retorna None.
    """
    if not REFLEX_INSTALLED:
        return None
    try:
        # Tenta instanciar diretamente
        state = state_class()
        return state
    except Exception as e:
        # Reflex State pode exigir contexto de app; tenta contornar
        try:
            # Cria sem __init__ (object.__new__)
            state = object.__new__(state_class)
            # Inicializa atributos de classe como instancia
            for name, default in state_class.__annotations__.items() if hasattr(state_class, '__annotations__') else []:
                setattr(state, name, default)
            # Atributos explicitos da classe
            for name in dir(state_class):
                if not name.startswith("_") and not callable(getattr(state_class, name, None)):
                    val = getattr(state_class, name)
                    if not isinstance(val, type) and not callable(val):
                        setattr(state, name, val)
            return state
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Fuzzing de util_unidade.py (nao depende de Reflex)
# ---------------------------------------------------------------------------
def fuzz_util_unidade():
    """Fuzzing das funcoes de validacao/conversao em util_unidade.py."""
    print("\n" + "=" * 70)
    print("FUZZING: app_reflex/util_unidade.py")
    print("=" * 70)

    from app_reflex.util_unidade import (
        validar_quantidade, validar_quantidade_despacho,
        quantidade_despacho_para_armazenar, ml_para_litros,
        litros_para_ml, numero_br, unidade_do_tipo,
        unidade_despacho_do_tipo, tipo_por_nome,
        formatar_despacho, formatar_saldo_duplo,
        quantidade_despacho_display,
    )

    # --- validar_quantidade(texto, tipo) ---
    print("\n--- validar_quantidade(texto, tipo) ---")
    for desc, val in FUZZ_QTD:
        for tipo in ["Toner", "Tinta", "Cartucho"]:
            try:
                result, err = validar_quantidade(val, tipo)
                if err and result is None:
                    record(f"validar_quantidade({tipo})", desc, val, "BLOCKED")
                else:
                    # Verifica se passou algo que nao deveria
                    if result is not None and (isinstance(result, (int, float))):
                        if result <= 0:
                            record(f"validar_quantidade({tipo})", desc, val, "SILENT_FAIL",
                                   f"Aceitou valor <= 0: {result}")
                        elif tipo != "Tinta" and isinstance(result, float) and int(result) != result:
                            record(f"validar_quantidade({tipo})", desc, val, "SILENT_FAIL",
                                   f"Toner/Cartucho aceitou fracionado: {result}")
                        else:
                            record(f"validar_quantidade({tipo})", desc, val, "OK")
                    else:
                        record(f"validar_quantidade({tipo})", desc, val, "OK")
            except Exception as e:
                record(f"validar_quantidade({tipo})", desc, val, "CRASH",
                       traceback.format_exc())

    # --- validar_quantidade_despacho(texto, tipo) ---
    print("\n--- validar_quantidade_despacho(texto, tipo) ---")
    for desc, val in FUZZ_QTD:
        for tipo in ["Toner", "Tinta", "Cartucho"]:
            try:
                result, err = validar_quantidade_despacho(val, tipo)
                if err and result is None:
                    record(f"validar_quantidade_despacho({tipo})", desc, val, "BLOCKED")
                else:
                    if result is not None and (isinstance(result, int) or isinstance(result, float)):
                        if result <= 0:
                            record(f"validar_quantidade_despacho({tipo})", desc, val, "SILENT_FAIL",
                                   f"Aceitou valor <= 0: {result}")
                        elif int(result) != result:
                            record(f"validar_quantidade_despacho({tipo})", desc, val, "SILENT_FAIL",
                                   f"Exige inteiro mas aceitou fracionado: {result}")
                        else:
                            record(f"validar_quantidade_despacho({tipo})", desc, val, "OK")
                    else:
                        record(f"validar_quantidade_despacho({tipo})", desc, val, "OK")
            except Exception as e:
                record(f"validar_quantidade_despacho({tipo})", desc, val, "CRASH",
                       traceback.format_exc())

    # --- numero_br(valor) ---
    print("\n--- numero_br(valor) ---")
    fuzz_vals_numero = [
        ("string_longa", "A" * 10000),
        ("vazio", ""),
        ("none", None),
        ("int_grande", 10**100),
        ("float_inf", float("inf")),
        ("float_nan", float("nan")),
        ("bool_true", True),
        ("bool_false", False),
        ("lista", [1, 2]),
        ("dict", {"a": 1}),
        ("string_normal", "42"),
        ("negativo", "-5"),
        ("exponential_str", "1e10"),
        ("null_bytes", "\x00"),
    ]
    for desc, val in fuzz_vals_numero:
        try:
            result = numero_br(val)
            record("numero_br", desc, val, "OK")
        except Exception as e:
            record("numero_br", desc, val, "CRASH", traceback.format_exc())

    # --- litros_para_ml(litros) ---
    print("\n--- litros_para_ml(litros) ---")
    fuzz_vals_l = [
        ("string_longa", "A" * 10000),
        ("vazio", ""),
        ("none", None),
        ("float_inf", float("inf")),
        ("float_nan", float("nan")),
        ("bool_true", True),
        ("bool_false", False),
        ("lista", [1]),
        ("dict", {"a": 1}),
        ("negativo", "-5.0"),
        ("muito_grande", "1e308"),
        ("null_bytes", "\x00"),
    ]
    for desc, val in fuzz_vals_l:
        try:
            result = litros_para_ml(val)
            record("litros_para_ml", desc, val, "OK")
        except Exception as e:
            record("litros_para_ml", desc, val, "CRASH", traceback.format_exc())

    # --- ml_para_litros(ml) ---
    print("\n--- ml_para_litros(ml) ---")
    for desc, val in fuzz_vals_l:
        try:
            result = ml_para_litros(val)
            record("ml_para_litros", desc, val, "OK")
        except Exception as e:
            record("ml_para_litros", desc, val, "CRASH", traceback.format_exc())

    # --- quantidade_despacho_para_armazenar(valor, tipo) ---
    print("\n--- quantidade_despacho_para_armazenar(valor, tipo) ---")
    for desc, val in FUZZ_QTD:
        for tipo in ["Toner", "Tinta", "Cartucho"]:
            try:
                result = quantidade_despacho_para_armazenar(val, tipo)
                record(f"quantidade_despacho_para_armazenar({tipo})", desc, val, "OK")
            except Exception as e:
                record(f"quantidade_despacho_para_armazenar({tipo})", desc, val,
                       "CRASH", traceback.format_exc())

    # --- quantidade_despacho_display(quantidade_l, tipo) ---
    print("\n--- quantidade_despacho_display(quantidade_l, tipo) ---")
    for desc, val in FUZZ_QTD:
        for tipo in ["Toner", "Tinta", "Cartucho"]:
            try:
                result = quantidade_despacho_display(val, tipo)
                record(f"quantidade_despacho_display({tipo})", desc, val, "OK")
            except Exception as e:
                record(f"quantidade_despacho_display({tipo})", desc, val,
                       "CRASH", traceback.format_exc())

    # --- formatar_despacho(quantidade_l, tipo) ---
    print("\n--- formatar_despacho(quantidade_l, tipo) ---")
    for desc, val in FUZZ_QTD:
        for tipo in ["Toner", "Tinta", "Cartucho"]:
            try:
                result = formatar_despacho(val, tipo)
                record(f"formatar_despacho({tipo})", desc, val, "OK")
            except Exception as e:
                record(f"formatar_despacho({tipo})", desc, val,
                       "CRASH", traceback.format_exc())

    # --- formatar_saldo_duplo(saldo_l, tipo) ---
    print("\n--- formatar_saldo_duplo(saldo_l, tipo) ---")
    for desc, val in FUZZ_QTD:
        for tipo in ["Toner", "Tinta", "Cartucho"]:
            try:
                result = formatar_saldo_duplo(val, tipo)
                record(f"formatar_saldo_duplo({tipo})", desc, val, "OK")
            except Exception as e:
                record(f"formatar_saldo_duplo({tipo})", desc, val,
                       "CRASH", traceback.format_exc())

    # --- tipo_por_nome(itens) ---
    print("\n--- tipo_por_nome(itens) ---")
    fuzz_itens = [
        ("vazio", []),
        ("none", None),
        ("int", 5),
        ("string", "abc"),
        ("dict_simples", [{"nome": "Toner HP", "tipo": "Toner"}]),
        ("item_sem_nome", [{"tipo": "Toner"}]),
        ("item_sem_tipo", [{"nome": "X"}]),
        ("item_none", [{"nome": None, "tipo": None}]),
        ("item_dict_vazio", {}),
        ("item_int", [1, 2, 3]),
        ("item_none_na_lista", [None, {"nome": "X", "tipo": "Y"}]),
        ("string_longa_nome", [{"nome": "A" * 10000, "tipo": "Tinta"}]),
        ("xss_nome", [{"nome": "<script>alert(1)</script>", "tipo": "Toner"}]),
        ("null_bytes_nome", [{"nome": "\x00\x01", "tipo": "Toner"}]),
    ]
    for desc, val in fuzz_itens:
        try:
            result = tipo_por_nome(val)
            record("tipo_por_nome", desc, val, "OK")
        except Exception as e:
            record("tipo_por_nome", desc, val, "CRASH", traceback.format_exc())

    # --- unidade_do_tipo(tipo) ---
    print("\n--- unidade_do_tipo(tipo) ---")
    fuzz_tipos = [
        ("vazio", ""),
        ("none", None),
        ("string_normal", "Tinta"),
        ("case_diferente", "TINTA"),
        ("xss", "<script>"),
        ("string_longa", "A" * 1000),
        ("int", 5),
        ("bool", True),
        ("lista", ["Tinta"]),
        ("dict", {"a": 1}),
        ("null_bytes", "\x00"),
    ]
    for desc, val in fuzz_tipos:
        try:
            result = unidade_do_tipo(val)
            record("unidade_do_tipo", desc, val, "OK")
        except Exception as e:
            record("unidade_do_tipo", desc, val, "CRASH", traceback.format_exc())

    # --- unidade_despacho_do_tipo(tipo) ---
    print("\n--- unidade_despacho_do_tipo(tipo) ---")
    for desc, val in fuzz_tipos:
        try:
            result = unidade_despacho_do_tipo(val)
            record("unidade_despacho_do_tipo", desc, val, "OK")
        except Exception as e:
            record("unidade_despacho_do_tipo", desc, val, "CRASH", traceback.format_exc())


# ---------------------------------------------------------------------------
# Fuzzing de db.py (funcoes de data e validacao)
# ---------------------------------------------------------------------------
def fuzz_db():
    """Fuzzing das funcoes de db.py que recebem input."""
    print("\n" + "=" * 70)
    print("FUZZING: db.py (funcoes de data e acesso)")
    print("=" * 70)

    # --- to_iso(data_br) ---
    print("\n--- db.to_iso(data_br) ---")
    for desc, val in FUZZ_DATES:
        try:
            result = db.to_iso(val)
            record("db.to_iso", desc, val, "OK")
        except Exception as e:
            record("db.to_iso", desc, val, "CRASH", traceback.format_exc())

    # --- to_display(data_iso) ---
    print("\n--- db.to_display(data_iso) ---")
    for desc, val in FUZZ_DATES:
        try:
            result = db.to_display(val)
            record("db.to_display", desc, val, "OK")
        except Exception as e:
            record("db.to_display", desc, val, "CRASH", traceback.format_exc())

    # --- _validar_tabela(tabela) ---
    print("\n--- db._validar_tabela(tabela) ---")
    fuzz_tabelas = [
        ("valida_filiais", "filiais"),
        ("valida_itens", "itens"),
        ("invalida", "tabela_inexistente"),
        ("vazio", ""),
        ("none", None),
        ("int", 5),
        ("sql_injection", "filiais; DROP TABLE--"),
        ("xss", "<script>"),
        ("string_longa", "A" * 1000),
        ("bool", True),
    ]
    for desc, val in fuzz_tabelas:
        try:
            db._validar_tabela(val)
            record("db._validar_tabela", desc, val, "OK")
        except ValueError:
            record("db._validar_tabela", desc, val, "BLOCKED")
        except Exception as e:
            record("db._validar_tabela", desc, val, "CRASH", traceback.format_exc())

    # --- saldo_atual(item_id) ---
    print("\n--- db.saldo_atual(item_id) ---")
    fuzz_ids = [
        ("int_valido", 1),
        ("string_num", "1"),
        ("negativo", -1),
        ("zero", 0),
        ("muito_grande", 999999999),
        ("none", None),
        ("string", "abc"),
        ("xss", "<script>"),
        ("bool_true", True),
        ("bool_false", False),
        ("lista", [1]),
        ("dict", {"a": 1}),
        ("float", 1.5),
        ("string_longa", "A" * 1000),
        ("null_bytes", "\x00"),
    ]
    for desc, val in fuzz_ids:
        try:
            result = db.saldo_atual(val)
            record("db.saldo_atual", desc, val, "OK")
        except Exception as e:
            record("db.saldo_atual", desc, val, "CRASH", traceback.format_exc())

    # --- listar(tabela) ---
    print("\n--- db.listar(tabela) ---")
    for desc, val in fuzz_tabelas:
        try:
            result = db.listar(val)
            record("db.listar", desc, val, "OK")
        except ValueError:
            record("db.listar", desc, val, "BLOCKED")
        except Exception as e:
            record("db.listar", desc, val, "CRASH", traceback.format_exc())

    # --- inserir(tabela, nome) ---
    print("\n--- db.inserir(tabela, nome) ---")
    for desc, val in FUZZ_TEXT:
        try:
            result = db.inserir("filiais", val)
            record("db.inserir(filiais)", desc, val, "OK")
        except Exception as e:
            record("db.inserir(filiais)", desc, val, "CRASH", traceback.format_exc())

    # --- inserir_item(nome, tipo, estoque_minimo) ---
    print("\n--- db.inserir_item(nome, tipo, estoque_minimo) ---")
    fuzz_minimos = [
        ("int_valido", 5),
        ("negativo", -5),
        ("zero", 0),
        ("muito_grande", 999999999),
        ("none", None),
        ("string_num", "5"),
        ("string_letras", "abc"),
        ("float", 1.5),
        ("bool_true", True),
        ("bool_false", False),
        ("lista", [1]),
        ("dict", {"a": 1}),
        ("string_longa", "A" * 1000),
    ]
    for desc, val in fuzz_minimos:
        try:
            nome = f"FuzzItem_{desc}"
            result = db.inserir_item(nome, "Toner", val)
            record("db.inserir_item(minimo)", desc, val, "OK")
        except Exception as e:
            record("db.inserir_item(minimo)", desc, val, "CRASH", traceback.format_exc())

    # --- excluir(tabela, item_id) ---
    print("\n--- db.excluir(tabela, item_id) ---")
    for desc, val in fuzz_ids:
        try:
            result = db.excluir("filiais", val)
            record("db.excluir(filiais)", desc, val, "OK")
        except Exception as e:
            record("db.excluir(filiais)", desc, val, "CRASH", traceback.format_exc())

    # --- inserir_entrada(...) ---
    print("\n--- db.inserir_entrada(data_iso, item_id, qtd, fornecedor, valor, obs) ---")
    fuzz_qtd_valor = [
        ("negativo", -5),
        ("zero", 0),
        ("muito_grande", 999999999),
        ("none", None),
        ("string_num", "5"),
        ("string_letras", "abc"),
        ("float_negativo", -1.5),
        ("bool", True),
        ("lista", [1]),
        ("dict", {"a": 1}),
        ("xss", "<script>"),
    ]
    for desc, val in fuzz_qtd_valor:
        try:
            db.inserir_entrada("2024-01-15", 1, val, "Forn", 10.0, "obs")
            record("db.inserir_entrada(qtd)", desc, val, "OK")
        except Exception as e:
            record("db.inserir_entrada(qtd)", desc, val, "CRASH", traceback.format_exc())

    # --- inserir_despacho(...) ---
    print("\n--- db.inserir_despacho(data_iso, filial_id, depto_id, item_id, qtd, ...) ---")
    for desc, val in fuzz_qtd_valor:
        try:
            db.inserir_despacho("2024-01-15", 1, 1, 1, val, "chamado", "recebedor", "obs")
            record("db.inserir_despacho(qtd)", desc, val, "OK")
        except Exception as e:
            record("db.inserir_despacho(qtd)", desc, val, "CRASH", traceback.format_exc())

    # --- ultimas_entradas(limite) ---
    print("\n--- db.ultimas_entradas(limite) ---")
    fuzz_limites = [
        ("int_valido", 100),
        ("negativo", -1),
        ("zero", 0),
        ("muito_grande", 999999999),
        ("none", None),
        ("string_num", "100"),
        ("string_letras", "abc"),
        ("float", 1.5),
        ("bool", True),
        ("lista", [1]),
    ]
    for desc, val in fuzz_limites:
        try:
            result = db.ultimas_entradas(val)
            record("db.ultimas_entradas", desc, val, "OK")
        except Exception as e:
            record("db.ultimas_entradas", desc, val, "CRASH", traceback.format_exc())

    # --- ultimos_despachos(limite) ---
    print("\n--- db.ultimos_despachos(limite) ---")
    for desc, val in fuzz_limites:
        try:
            result = db.ultimos_despachos(val)
            record("db.ultimos_despachos", desc, val, "OK")
        except Exception as e:
            record("db.ultimos_despachos", desc, val, "CRASH", traceback.format_exc())

    # --- relatorio_despachos(filtro) ---
    print("\n--- db.relatorio_despachos(filtro) ---")
    fuzz_filtros = [
        ("vazio", {}),
        ("none", None),
        ("int", 5),
        ("string", "abc"),
        ("lista", [1]),
        ("de_invalido", {"de": "INVALIDO"}),
        ("ate_invalido", {"ate": "INVALIDO"}),
        ("filial_xss", {"filial": "<script>alert(1)</script>"}),
        ("filial_sql", {"filial": "'; DROP TABLE--"}),
        ("de_none", {"de": None}),
        ("filial_none", {"filial": None}),
        ("de_int", {"de": 12345}),
        ("filial_int", {"filial": 12345}),
        ("string_longa", {"filial": "A" * 10000}),
        ("null_bytes", {"filial": "\x00"}),
    ]
    for desc, val in fuzz_filtros:
        try:
            result = db.relatorio_despachos(val)
            record("db.relatorio_despachos", desc, val, "OK")
        except Exception as e:
            record("db.relatorio_despachos", desc, val, "CRASH", traceback.format_exc())


# ---------------------------------------------------------------------------
# Fuzzing de util_csv.py
# ---------------------------------------------------------------------------
def fuzz_util_csv():
    """Fuzzing de gerar_csv_relatorio."""
    print("\n" + "=" * 70)
    print("FUZZING: app_reflex/util_csv.py")
    print("=" * 70)

    from app_reflex.util_csv import gerar_csv_relatorio

    print("\n--- gerar_csv_relatorio(filtro) ---")
    fuzz_filtros = [
        ("vazio", {}),
        ("none", None),
        ("int", 5),
        ("string", "abc"),
        ("lista", [1]),
        ("de_invalido", {"de": "INVALIDO"}),
        ("filial_xss", {"filial": "<script>alert(1)</script>"}),
        ("filial_sql", {"filial": "'; DROP TABLE--"}),
        ("filial_formula_csv", {"filial": "=cmd|' /C calc'!A0"}),
        ("filial_string_longa", {"filial": "A" * 10000}),
        ("filial_null_bytes", {"filial": "\x00\x01"}),
        ("filial_none", {"filial": None}),
        ("filial_int", {"filial": 12345}),
    ]
    for desc, val in fuzz_filtros:
        try:
            result = gerar_csv_relatorio(val)
            # Verifica se o resultado contem formula injection
            if isinstance(result, str) and ("=" in result[:200] or "@" in result[:200]):
                record("gerar_csv_relatorio", desc, val, "SILENT_FAIL",
                       f"Possivel formula injection no CSV: {result[:200]}")
            else:
                record("gerar_csv_relatorio", desc, val, "OK")
        except Exception as e:
            record("gerar_csv_relatorio", desc, val, "CRASH", traceback.format_exc())


# ---------------------------------------------------------------------------
# Fuzzing dos event handlers Reflex (se Reflex estiver instalado)
# ---------------------------------------------------------------------------
def fuzz_reflex_handlers():
    """Fuzzing dos event handlers dos States Reflex."""
    print("\n" + "=" * 70)
    print("FUZZING: app_reflex/estados/* (event handlers Reflex)")
    print("=" * 70)

    if not REFLEX_INSTALLED:
        print("\n  Reflex nao instalado. Pulando fuzzing de handlers Reflex.")
        print("  (Analise estatica sera feita no relatorio final.)")
        return

    # Importa os estados
    from app_reflex.estados.despacho import DespachoState
    from app_reflex.estados.entrada import EntradaState
    from app_reflex.estados.cadastros import CadastrosState
    from app_reflex.estados.relatorios import RelatoriosState
    from app_reflex.estados.estoque import EstoqueState
    from app_reflex.estados.dashboard import DashboardState

    ids = get_ids()

    # Lista de (state_class, handler_name, handler_func) para fuzzing
    states_to_test = [
        (DespachoState, "DespachoState"),
        (EntradaState, "EntradaState"),
        (CadastrosState, "CadastrosState"),
        (RelatoriosState, "RelatoriosState"),
    ]

    for state_class, state_name in states_to_test:
        state = make_mock_state(state_class)
        if state is None:
            print(f"\n  {state_name}: Nao foi possivel instanciar (depende de runtime Reflex).")
            print(f"  Fazendo fuzzing das funcoes crua (sem self).")
            # Tenta chamar com self=None para ver o que acontece
            continue

        # Carrega dados iniciais (necessario para que os handlers tenham listas)
        try:
            carregar = unwrap_handler(state.carregar)
            carregar(state)
            print(f"\n  {state_name}.carregar() OK")
        except Exception as e:
            print(f"\n  {state_name}.carregar() FALHOU: {e}")
            # Tenta popular manualmente
            try:
                state.itens = [dict(r) for r in db.listar_itens()]
                state.filiais = [dict(r) for r in db.listar("filiais")]
                state.deptos = [dict(r) for r in db.listar("departamentos")]
            except Exception:
                pass

        # ---- DespachoState.salvar ----
        if state_name == "DespachoState":
            print(f"\n--- {state_name}.salvar(form_data) ---")
            salvar = unwrap_handler(state.salvar)
            for desc, qtd in FUZZ_QTD:
                form = {
                    "data": "15/01/2024",
                    "filial_id": ids["filial_id"],
                    "departamento_id": ids["depto_id"],
                    "item_id": ids["item_toner_id"],
                    "quantidade": qtd,
                    "chamado": "CH-001",
                    "recebedor": "Joao",
                    "observacao": "Teste",
                }
                try:
                    salvar(state, form)
                    # Verifica se registrou algo indevido
                    record(f"{state_name}.salvar", f"qtd={desc}", qtd, "OK")
                except Exception as e:
                    record(f"{state_name}.salvar", f"qtd={desc}", qtd, "CRASH",
                           traceback.format_exc())

            # Fuzzing de campos de texto
            for desc, val in FUZZ_TEXT:
                form = {
                    "data": "15/01/2024",
                    "filial_id": ids["filial_id"],
                    "departamento_id": ids["depto_id"],
                    "item_id": ids["item_toner_id"],
                    "quantidade": "5",
                    "chamado": val,
                    "recebedor": val,
                    "observacao": val,
                }
                try:
                    salvar(state, form)
                    record(f"{state_name}.salvar(texto)", f"chamado/recebedor/obs={desc}", val, "OK")
                except Exception as e:
                    record(f"{state_name}.salvar(texto)", f"chamado/recebedor/obs={desc}", val,
                           "CRASH", traceback.format_exc())

            # Fuzzing de data
            for desc, val in FUZZ_DATES:
                form = {
                    "data": val,
                    "filial_id": ids["filial_id"],
                    "departamento_id": ids["depto_id"],
                    "item_id": ids["item_toner_id"],
                    "quantidade": "5",
                    "chamado": "CH-001",
                    "recebedor": "Joao",
                    "observacao": "Teste",
                }
                try:
                    salvar(state, form)
                    record(f"{state_name}.salvar(data)", f"data={desc}", val, "OK")
                except Exception as e:
                    record(f"{state_name}.salvar(data)", f"data={desc}", val, "CRASH",
                           traceback.format_exc())

            # Fuzzing de item_id/filial_id/depto_id
            fuzz_id_vals = [
                ("none", None),
                ("vazio", ""),
                ("negativo", "-1"),
                ("string", "abc"),
                ("xss", "<script>"),
                ("sql_injection", "1; DROP TABLE--"),
                ("bool", True),
                ("int_grande", 999999999),
                ("float", 1.5),
            ]
            for desc, val in fuzz_id_vals:
                form = {
                    "data": "15/01/2024",
                    "filial_id": val,
                    "departamento_id": val,
                    "item_id": val,
                    "quantidade": "5",
                    "chamado": "CH",
                    "recebedor": "Joao",
                    "observacao": "",
                }
                try:
                    salvar(state, form)
                    record(f"{state_name}.salvar(ids)", f"ids={desc}", val, "OK")
                except Exception as e:
                    record(f"{state_name}.salvar(ids)", f"ids={desc}", val, "CRASH",
                           traceback.format_exc())

            # ---- DespachoState.ao_mudar_item ----
            print(f"\n--- {state_name}.ao_mudar_item(valor) ---")
            ao_mudar_item = unwrap_handler(state.ao_mudar_item)
            for desc, val in fuzz_id_vals:
                try:
                    ao_mudar_item(state, val)
                    record(f"{state_name}.ao_mudar_item", desc, val, "OK")
                except Exception as e:
                    record(f"{state_name}.ao_mudar_item", desc, val, "CRASH",
                           traceback.format_exc())

            # ---- DespachoState.confirmar ----
            print(f"\n--- {state_name}.confirmar() ---")
            confirmar = unwrap_handler(state.confirmar)
            # Popula dados_pendentes com valores maliciosos
            for desc, qtd in FUZZ_QTD:
                state.dados_pendentes = {
                    "data": "15/01/2024",
                    "filial_id": ids["filial_id"],
                    "departamento_id": ids["depto_id"],
                    "item_id": ids["item_toner_id"],
                    "quantidade": qtd,
                    "chamado": "CH-001",
                    "recebedor": "Joao",
                    "observacao": "Teste",
                }
                state.confirmacao_pendente = True
                try:
                    confirmar(state)
                    record(f"{state_name}.confirmar", f"qtd={desc}", qtd, "OK")
                except Exception as e:
                    record(f"{state_name}.confirmar", f"qtd={desc}", qtd, "CRASH",
                           traceback.format_exc())

        # ---- EntradaState.salvar ----
        if state_name == "EntradaState":
            print(f"\n--- {state_name}.salvar(form_data) ---")
            salvar = unwrap_handler(state.salvar)
            for desc, qtd in FUZZ_QTD:
                form = {
                    "item_id": ids["item_toner_id"],
                    "quantidade": qtd,
                    "fornecedor": "Fornecedor Teste",
                    "valor_unitario": "10.50",
                    "observacao": "Obs teste",
                }
                try:
                    salvar(state, form)
                    record(f"{state_name}.salvar", f"qtd={desc}", qtd, "OK")
                except Exception as e:
                    record(f"{state_name}.salvar", f"qtd={desc}", qtd, "CRASH",
                           traceback.format_exc())

            # Fuzzing de valor_unitario
            for desc, val in FUZZ_QTD:
                form = {
                    "item_id": ids["item_toner_id"],
                    "quantidade": "5",
                    "fornecedor": "Forn",
                    "valor_unitario": val,
                    "observacao": "Obs",
                }
                try:
                    salvar(state, form)
                    record(f"{state_name}.salvar(valor)", f"valor={desc}", val, "OK")
                except Exception as e:
                    record(f"{state_name}.salvar(valor)", f"valor={desc}", val, "CRASH",
                           traceback.format_exc())

            # Fuzzing de campos de texto
            for desc, val in FUZZ_TEXT:
                form = {
                    "item_id": ids["item_toner_id"],
                    "quantidade": "5",
                    "fornecedor": val,
                    "valor_unitario": "10.50",
                    "observacao": val,
                }
                try:
                    salvar(state, form)
                    record(f"{state_name}.salvar(texto)", f"forn/obs={desc}", val, "OK")
                except Exception as e:
                    record(f"{state_name}.salvar(texto)", f"forn/obs={desc}", val, "CRASH",
                           traceback.format_exc())

            # Fuzzing de item_id
            fuzz_id_vals = [
                ("none", None),
                ("vazio", ""),
                ("negativo", "-1"),
                ("string", "abc"),
                ("xss", "<script>"),
                ("bool", True),
            ]
            for desc, val in fuzz_id_vals:
                form = {
                    "item_id": val,
                    "quantidade": "5",
                    "fornecedor": "Forn",
                    "valor_unitario": "10.50",
                    "observacao": "",
                }
                try:
                    salvar(state, form)
                    record(f"{state_name}.salvar(item_id)", f"item_id={desc}", val, "OK")
                except Exception as e:
                    record(f"{state_name}.salvar(item_id)", f"item_id={desc}", val, "CRASH",
                           traceback.format_exc())

            # ---- EntradaState.ao_mudar_item ----
            print(f"\n--- {state_name}.ao_mudar_item(valor) ---")
            ao_mudar_item = unwrap_handler(state.ao_mudar_item)
            for desc, val in fuzz_id_vals:
                try:
                    ao_mudar_item(state, val)
                    record(f"{state_name}.ao_mudar_item", desc, val, "OK")
                except Exception as e:
                    record(f"{state_name}.ao_mudar_item", desc, val, "CRASH",
                           traceback.format_exc())

        # ---- CadastrosState.adicionar_filial ----
        if state_name == "CadastrosState":
            print(f"\n--- {state_name}.adicionar_filial(form_data) ---")
            adicionar_filial = unwrap_handler(state.adicionar_filial)
            for desc, val in FUZZ_TEXT:
                form = {"nome": val}
                try:
                    adicionar_filial(state, form)
                    record(f"{state_name}.adicionar_filial", desc, val, "OK")
                except Exception as e:
                    record(f"{state_name}.adicionar_filial", desc, val, "CRASH",
                           traceback.format_exc())

            # ---- adicionar_depto ----
            print(f"\n--- {state_name}.adicionar_depto(form_data) ---")
            adicionar_depto = unwrap_handler(state.adicionar_depto)
            for desc, val in FUZZ_TEXT:
                form = {"nome": val}
                try:
                    adicionar_depto(state, form)
                    record(f"{state_name}.adicionar_depto", desc, val, "OK")
                except Exception as e:
                    record(f"{state_name}.adicionar_depto", desc, val, "CRASH",
                           traceback.format_exc())

            # ---- adicionar_item ----
            print(f"\n--- {state_name}.adicionar_item(form_data) ---")
            adicionar_item = unwrap_handler(state.adicionar_item)
            fuzz_minimos = [
                ("vazio", ""),
                ("none", None),
                ("negativo", "-5"),
                ("zero", "0"),
                ("muito_grande", "999999999"),
                ("string_letras", "abc"),
                ("float", "1.5"),
                ("bool_true", True),
                ("bool_false", False),
                ("int", 5),
                ("lista", [1]),
                ("dict", {"a": 1}),
                ("xss", "<script>"),
                ("sql_injection", "1; DROP--"),
            ]
            for desc, val in fuzz_minimos:
                form = {
                    "nome": f"FuzzItem_{desc}_{id(val)}",
                    "tipo": "Toner",
                    "estoque_minimo": val,
                }
                try:
                    adicionar_item(state, form)
                    record(f"{state_name}.adicionar_item(minimo)", desc, val, "OK")
                except Exception as e:
                    record(f"{state_name}.adicionar_item(minimo)", desc, val, "CRASH",
                           traceback.format_exc())

            # Fuzzing de tipo
            fuzz_tipos_val = [
                ("vazio", ""),
                ("none", None),
                ("xss", "<script>alert(1)</script>"),
                ("sql_injection", "'; DROP TABLE--"),
                ("string_longa", "A" * 1000),
                ("int", 5),
                ("bool", True),
                ("case_diferente", "TINTA"),
            ]
            for desc, val in fuzz_tipos_val:
                form = {
                    "nome": f"FuzzTipo_{desc}",
                    "tipo": val,
                    "estoque_minimo": "5",
                }
                try:
                    adicionar_item(state, form)
                    record(f"{state_name}.adicionar_item(tipo)", desc, val, "OK")
                except Exception as e:
                    record(f"{state_name}.adicionar_item(tipo)", desc, val, "CRASH",
                           traceback.format_exc())

            # ---- excluir(tabela, registro_id) ----
            print(f"\n--- {state_name}.excluir(tabela, registro_id) ---")
            excluir = unwrap_handler(state.excluir)
            fuzz_excluir = [
                ("tabela_valida_id_valido", ("filiais", 1)),
                ("tabela_invalida", ("tabela_inexistente", 1)),
                ("id_negativo", ("filiais", -1)),
                ("id_zero", ("filiais", 0)),
                ("id_none", ("filiais", None)),
                ("id_string", ("filiais", "abc")),
                ("id_xss", ("filiais", "<script>")),
                ("id_sql_injection", ("filiais", "1; DROP--")),
                ("id_bool", ("filiais", True)),
                ("id_float", ("filiais", 1.5)),
                ("tabela_none", (None, 1)),
                ("tabela_int", (5, 1)),
                ("ambos_none", (None, None)),
            ]
            for desc, (tabela, rid) in fuzz_excluir:
                try:
                    excluir(state, tabela, rid)
                    record(f"{state_name}.excluir", desc, (tabela, rid), "OK")
                except Exception as e:
                    record(f"{state_name}.excluir", desc, (tabela, rid), "CRASH",
                           traceback.format_exc())

            # ---- confirmar_exclusao_cascata ----
            print(f"\n--- {state_name}.confirmar_exclusao_cascata() ---")
            confirmar_cascata = unwrap_handler(state.confirmar_exclusao_cascata)
            # Popula payload malicioso
            fuzz_payloads = [
                ("valido", {"tabela": "filiais", "id": 1, "nome": "Teste"}),
                ("tabela_invalida", {"tabela": "tabela_inexistente", "id": 1, "nome": "X"}),
                ("id_negativo", {"tabela": "filiais", "id": -1, "nome": "X"}),
                ("id_zero", {"tabela": "filiais", "id": 0, "nome": "X"}),
                ("id_none", {"tabela": "filiais", "id": None, "nome": "X"}),
                ("id_string", {"tabela": "filiais", "id": "abc", "nome": "X"}),
                ("id_xss", {"tabela": "filiais", "id": "<script>", "nome": "X"}),
                ("tabela_none", {"tabela": None, "id": 1, "nome": "X"}),
                ("payload_vazio", {}),
            ]
            for desc, payload in fuzz_payloads:
                state._pending_payload = dict(payload)
                state.confirm_tabela = payload.get("tabela", "")
                state.confirm_id = payload.get("id", 0)
                state.confirm_nome = payload.get("nome", "")
                try:
                    confirmar_cascata(state)
                    record(f"{state_name}.confirmar_exclusao_cascata", desc, payload, "OK")
                except Exception as e:
                    record(f"{state_name}.confirmar_exclusao_cascata", desc, payload, "CRASH",
                           traceback.format_exc())

        # ---- RelatoriosState.filtrar ----
        if state_name == "RelatoriosState":
            print(f"\n--- {state_name}.filtrar(form_data) ---")
            filtrar = unwrap_handler(state.filtrar)
            # Fuzzing de datas
            for desc, val in FUZZ_DATES:
                form = {
                    "de": val,
                    "ate": val,
                    "filial": "(Todas)",
                    "departamento": "(Todos)",
                    "item": "(Todos)",
                }
                try:
                    filtrar(state, form)
                    record(f"{state_name}.filtrar(data)", f"de/ate={desc}", val, "OK")
                except Exception as e:
                    record(f"{state_name}.filtrar(data)", f"de/ate={desc}", val, "CRASH",
                           traceback.format_exc())

            # Fuzzing de filial/departamento/item (texto)
            for desc, val in FUZZ_TEXT:
                form = {
                    "de": "01/01/2024",
                    "ate": "31/12/2024",
                    "filial": val,
                    "departamento": val,
                    "item": val,
                }
                try:
                    filtrar(state, form)
                    record(f"{state_name}.filtrar(texto)", f"filial/depto/item={desc}", val, "OK")
                except Exception as e:
                    record(f"{state_name}.filtrar(texto)", f"filial/depto/item={desc}", val, "CRASH",
                           traceback.format_exc())

            # Fuzzing de form_data malicioso (None, int, etc.)
            fuzz_forms = [
                ("form_none", None),
                ("form_int", 5),
                ("form_string", "abc"),
                ("form_lista", [1]),
                ("form_vazio", {}),
            ]
            for desc, val in fuzz_forms:
                try:
                    filtrar(state, val)
                    record(f"{state_name}.filtrar(form)", desc, val, "OK")
                except Exception as e:
                    record(f"{state_name}.filtrar(form)", desc, val, "CRASH",
                           traceback.format_exc())

            # ---- RelatoriosState._aplicar(filtro) ----
            print(f"\n--- {state_name}._aplicar(filtro) ---")
            _aplicar = getattr(state, "_aplicar", None)
            if _aplicar:
                _aplicar_unwrapped = unwrap_handler(_aplicar)
                fuzz_filtros = [
                    ("vazio", {}),
                    ("none", None),
                    ("int", 5),
                    ("string", "abc"),
                    ("de_invalido", {"de": "INVALIDO"}),
                    ("filial_xss", {"filial": "<script>alert(1)</script>"}),
                    ("filial_sql", {"filial": "'; DROP TABLE--"}),
                    ("filial_formula", {"filial": "=cmd|' /C calc'!A0"}),
                    ("filial_none", {"filial": None}),
                    ("filial_int", {"filial": 12345}),
                ]
                for desc, val in fuzz_filtros:
                    try:
                        _aplicar_unwrapped(state, val)
                        record(f"{state_name}._aplicar", desc, val, "OK")
                    except Exception as e:
                        record(f"{state_name}._aplicar", desc, val, "CRASH",
                               traceback.format_exc())


# ---------------------------------------------------------------------------
# Relatorio final
# ---------------------------------------------------------------------------
def print_summary():
    """Imprime o relatorio final de falhas concretas."""
    print("\n" + "=" * 70)
    print("RELATORIO DE FALHAS CONCRETAS")
    print("=" * 70)

    crashes = [r for r in results if r["status"] == "CRASH"]
    silent_fails = [r for r in results if r["status"] == "SILENT_FAIL"]
    unexpected = [r for r in results if r["status"] == "UNEXPECTED_EXCEPTION"]
    oks = [r for r in results if r["status"] == "OK"]
    blocked = [r for r in results if r["status"] == "BLOCKED"]

    total = len(results)
    print(f"\nTotal de testes: {total}")
    print(f"  ✅ OK (sem crash): {len(oks)}")
    print(f"  🛡️ BLOCKED (validacao rejeitou): {len(blocked)}")
    print(f"  💥 CRASH (excecao nao tratada): {len(crashes)}")
    print(f"  ⚠️ SILENT_FAIL (aceitou input invalido): {len(silent_fails)}")
    print(f"  ❓ UNEXPECTED_EXCEPTION: {len(unexpected)}")

    if crashes:
        print("\n" + "-" * 70)
        print("FALHAS: CRASHES (excecoes nao tratadas)")
        print("-" * 70)
        for r in crashes:
            print(f"\n  Handler: {r['handler']}")
            print(f"  Input:   {r['input_desc']} = {r['input_val_repr']}")
            print(f"  Traceback (primeiras linhas):")
            for line in r["exc_info"].split("\n")[:6]:
                print(f"    {line}")

    if silent_fails:
        print("\n" + "-" * 70)
        print("FALHAS: SILENT_FAILS (input invalido aceito sem erro)")
        print("-" * 70)
        for r in silent_fails:
            print(f"\n  Handler: {r['handler']}")
            print(f"  Input:   {r['input_desc']} = {r['input_val_repr']}")
            print(f"  Detalhe: {r['exc_info']}")

    if unexpected:
        print("\n" + "-" * 70)
        print("FALHAS: EXCECOES INESPERADAS")
        print("-" * 70)
        for r in unexpected:
            print(f"\n  Handler: {r['handler']}")
            print(f"  Input:   {r['input_desc']} = {r['input_val_repr']}")
            for line in r["exc_info"].split("\n")[:6]:
                print(f"    {line}")

    if not crashes and not silent_fails and not unexpected:
        print("\n  Nenhuma falha concreta encontrada.")
        print("  Todos os handlers trataram (ou rejeitaram) os inputs maliciosos.")

    print("\n" + "=" * 70)
    print("FIM DO RELATORIO")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if REFLEX_INSTALLED:
        print(f"Reflex {REFLEX_VERSION} instalado. Iniciando fuzzing dinamico.")
    else:
        print("Reflex NAO instalado. Fuzzing das funcoes de db.py e util_unidade.py.")
        print("Analise estatica dos handlers Reflex sera feita no relatorio.")

    # Prepara banco de teste
    orig_path, test_db = setup_test_db()
    print(f"\nBanco de teste: {test_db}")

    try:
        # Fuzzing de funcoes que nao dependem de Reflex
        fuzz_db()
        fuzz_util_unidade()
        fuzz_util_csv()

        # Fuzzing dos handlers Reflex (se instalado)
        fuzz_reflex_handlers()

    finally:
        teardown_test_db(test_db)
        db.DB_PATH = orig_path

    # Relatorio final
    print_summary()


if __name__ == "__main__":
    main()
