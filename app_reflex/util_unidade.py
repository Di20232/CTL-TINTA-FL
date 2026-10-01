#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unidade de medida por tipo de item (tinta em LITROS, toner/cartucho em UNIDADES).

Regras de negocio:
  - 'Tinta'           -> unidade "L" (litros). Pode ser fracionada (0,5 L).
  - 'Toner'/'Cartucho'-> unidade "un" (unidades). Sempre inteiro.
  - Outros            -> "un" (unidades).

Fica separado aqui para que estados e paginas usem a mesma regra,
evitando divergencia entre telas e no CSV exportado.
"""

import logging

logger = logging.getLogger(__name__)

LITROS = "L"
UNIDADES = "un"

TIPOS_LITROS = {"tinta"}


def unidade_do_tipo(tipo):
    """Retorna o rotulo de unidade conforme o tipo do item."""
    if tipo and str(tipo).strip().lower() in TIPOS_LITROS:
        return LITROS
    return UNIDADES


def numero_br(valor):
    """Formata numero p/ pt-BR, removendo zeros a direita desnecessarios.

    Exemplos:
      numero_br(1)    -> "1"
      numero_br(1.5)  -> "1,5"
      numero_br(0.5)  -> "0,5"
      numero_br(2.0)  -> "2"
    """
    try:
        num = float(valor)
    except (ValueError, TypeError) as exc:
        logger.warning(
            "numero_br: valor nao conversivel para float (%r): %s", valor, exc
        )
        return "0"
    try:
        if num == int(num):
            return str(int(num))
        texto = format(num, ".6g").replace(".", ",")
        return texto
    except (OverflowError, ValueError) as exc:
        logger.error(
            "numero_br: erro inesperado ao formatar numero (%r): %s", valor, exc,
            exc_info=True,
        )
        return str(valor)


def formatar_com_unidade(valor, tipo):
    """Quantidade + unidade para exibicao: '5 un' ou '1,5 L'."""
    return f"{numero_br(valor)} {unidade_do_tipo(tipo)}"


def unidade_item(item):
    """Atalho: dado um dict de item (com chave 'tipo'), retorna a unidade."""
    try:
        if isinstance(item, dict):
            return unidade_do_tipo(item.get("tipo"))
        return UNIDADES
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "unidade_item: erro inesperado ao obter unidade do item (%r): %s",
            item, exc, exc_info=True,
        )
        return UNIDADES


# Normalizacao de entrada: converte virgula decimal em ponto, aceita inteiro.
def _numero_do_form(value):
    """Converte o texto do input (',' decimal) em float. Retorna None se invalido."""
    try:
        return float((value or "").replace(",", ".").strip())
    except ValueError:
        logger.debug(
            "_numero_do_form: valor invalido recebido do formulario (%r)", value
        )
        return None
    except (TypeError, AttributeError) as exc:
        logger.warning(
            "_numero_do_form: tipo inesperado de entrada (%r): %s", value, exc
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "_numero_do_form: erro inesperado ao converter valor do formulario (%r): %s",
            value, exc, exc_info=True,
        )
        return None


def validar_quantidade(texto, tipo):
    """Valida a quantidade digitada.

    Regras:
      - Tinta: aceita fracionado (> 0) em litros.
      - Toner/Cartucho (unidades): exige numero inteiro (> 0).

    Retorna (valor_float, mensagem_de_erro). Se valido, erro e None.
    """
    valor = _numero_do_form(texto)
    if valor is None or valor <= 0:
        return None, "Quantidade deve ser maior que zero."
    if unidade_do_tipo(tipo) != LITROS and int(valor) != valor:
        return None, "Quantidade de toner/cartucho deve ser um numero inteiro."
    return valor, None


def tipo_por_nome(itens):
    """Mapa nome-normalizado -> tipo, a partir de db.listar_itens().

    Usado para enriquecer linhas de movimentos/relatorios (que nao trazem
    'tipo' na consulta) — o tipo do item e necessario para saber a unidade.

    Aceita tanto dicts quanto sqlite3.Row (db.listar_itens retorna Row).
    """
    mapa = {}
    for i in itens:
        try:
            if isinstance(i, dict):
                nome = str(i.get("nome", "")).strip().lower()
                tipo = i.get("tipo") or "Toner"
            else:  # sqlite3.Row
                nome = str(i["nome"] or "").strip().lower()
                tipo = i["tipo"] or "Toner"
            if nome:
                mapa[nome] = tipo
        except (KeyError, TypeError, AttributeError) as exc:
            logger.warning(
                "tipo_por_nome: item invalido ignorado (%r): %s", i, exc
            )
            continue
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "tipo_por_nome: erro inesperado processando item (%r): %s",
                i, exc, exc_info=True,
            )
            continue
    return mapa


# ---------------------------------------------------------------------------
# Conversao ml <-> L para DESPACHO de tinta.
# O operador envia garrafinhas de ml, mas o banco armazena tudo em litros (L),
# pois a pagina de Entrada ja registra em L e o saldo do db.py subtrai direto.
# ---------------------------------------------------------------------------

ML_POR_LITRO = 1000
MILILITROS = "ml"


def ml_para_litros(ml):
    """Converte mililitros para litros (para armazenar no banco)."""
    try:
        return float(ml) / ML_POR_LITRO
    except (ValueError, TypeError) as exc:
        logger.warning(
            "ml_para_litros: valor invalido de ml (%r): %s", ml, exc
        )
        return 0.0
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "ml_para_litros: erro inesperado ao converter %r: %s",
            ml, exc, exc_info=True,
        )
        return 0.0


def litros_para_ml(litros):
    """Converte litros para mililitros (para exibir/historico)."""
    try:
        return round(float(litros) * ML_POR_LITRO)
    except (ValueError, TypeError) as exc:
        logger.warning(
            "litros_para_ml: valor invalido de litros (%r): %s", litros, exc
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "litros_para_ml: erro inesperado ao converter %r: %s",
            litros, exc, exc_info=True,
        )
        return 0


def unidade_despacho_do_tipo(tipo):
    """Unidade do CAMPO de quantidade no despacho:
    Tinta -> 'ml'; Toner/Cartucho -> 'un'."""
    if tipo and str(tipo).strip().lower() in TIPOS_LITROS:
        return MILILITROS
    return UNIDADES


def validar_quantidade_despacho(texto, tipo):
    """Valida a quantidade digitada no despacho.

    Regras:
      - Tinta: inteiro > 0 em mililitros (ml).
      - Toner/Cartucho (unidades): inteiro > 0 em 'un'.

    Retorna (valor_int, mensagem_de_erro). Se valido, erro e None.
    """
    unid = unidade_despacho_do_tipo(tipo)
    valor = _numero_do_form(texto)
    if valor is None or valor <= 0:
        return None, "Quantidade deve ser maior que zero."
    if int(valor) != valor:
        return None, f"Quantidade de tinta em {unid} deve ser um numero inteiro."
    return int(valor), None


def quantidade_despacho_para_armazenar(valor, tipo):
    """Converte a quantidade digitada (ml para Tinta, un para demais)
    para o valor a ser ARMENAZADO no banco (sempre em litros para Tinta)."""
    try:
        if unidade_despacho_do_tipo(tipo) == MILILITROS:
            return ml_para_litros(valor)
        return float(valor)
    except (ValueError, TypeError) as exc:
        logger.warning(
            "quantidade_despacho_para_armazenar: valor invalido (%r, tipo=%r): %s",
            valor, tipo, exc,
        )
        return 0.0
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "quantidade_despacho_para_armazenar: erro inesperado (%r, tipo=%r): %s",
            valor, tipo, exc, exc_info=True,
        )
        return 0.0


def quantidade_despacho_display(quantidade_l, tipo):
    """Retorna a quantidade em unidade de EXIBICAO de historico de despacho:
    ml (int) para Tinta, 'un' (int) para os demais."""
    try:
        if unidade_despacho_do_tipo(tipo) == MILILITROS:
            return litros_para_ml(quantidade_l)
        return int(quantidade_l)
    except (ValueError, TypeError) as exc:
        logger.warning(
            "quantidade_despacho_display: valor invalido (%r, tipo=%r): %s",
            quantidade_l, tipo, exc,
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "quantidade_despacho_display: erro inesperado (%r, tipo=%r): %s",
            quantidade_l, tipo, exc, exc_info=True,
        )
        return 0


def formatar_despacho(quantidade_l, tipo):
    """Texto de quantidade de DESPACHO para tabelas de historico:
    Tinta -> '500 ml'; Toner/Cartucho -> '3 un'."""
    if unidade_despacho_do_tipo(tipo) == MILILITROS:
        return f"{numero_br(litros_para_ml(quantidade_l))} {MILILITROS}"
    return f"{numero_br(quantidade_despacho_display(quantidade_l, tipo))} {UNIDADES}"


def formatar_saldo_duplo(saldo_l, tipo):
    """Texto de saldo no despacho:
    Tinta -> '2,5 L · 2500 ml' (litros + equivalente em ml);
    Toner/Cartucho -> '5 un'."""
    if unidade_despacho_do_tipo(tipo) == MILILITROS:
        return f"{numero_br(saldo_l)} {LITROS} · {numero_br(litros_para_ml(saldo_l))} {MILILITROS}"
    return f"{numero_br(quantidade_despacho_display(saldo_l, tipo))} {UNIDADES}"