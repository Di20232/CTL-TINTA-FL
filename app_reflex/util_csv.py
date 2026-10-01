#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Geracao de CSV para exportacao no app Reflex.
Mesmo formato do antigo endpoint Flask: BOM UTF-8 + separador ; ,
com datas no formato brasileiro (dd/mm/aaaa) para abrir corretamente no Excel.
"""

import csv
import io

import db

from app_reflex.util_unidade import (
    numero_br, tipo_por_nome,
    litros_para_ml, unidade_despacho_do_tipo,
)


def gerar_csv_relatorio(filtro):
    """Gera o conteudo CSV (str com BOM) dos despachos filtrados.

    filtro: dict com chaves opcionais: de, ate, filial, departamento, item
    (datas em ISO aaaa-mm-dd).
    Retorna a string completa do CSV, ja com o BOM no inicio.

    A coluna 'Quantidade' sai na unidade de despacho por tipo:
    Tinta em mililitros (ex: '500' com Unidade 'ml' — garrafinhas),
    Toner/Cartucho em unidades (ex: '3' com Unidade 'un').
    Numeros em formato brasileiro para abrir corretamente no Excel.
    """
    rows = db.relatorio_despachos(filtro)
    mapa = tipo_por_nome(db.listar_itens())

    output = io.StringIO()
    w = csv.writer(output, delimiter=";")
    w.writerow([
        "Data", "Filial", "Departamento", "Item", "Quantidade", "Unidade",
        "No Chamado", "Recebido por",
    ])
    for r in rows:
        tipo = mapa.get(str(r["item"]).lower(), "Toner")
        if unidade_despacho_do_tipo(tipo) == "ml":
            # Tinta despachada sai em ml no CSV (garrafinhas)
            quantidade_csv = numero_br(litros_para_ml(r["quantidade"]))
            unidade_csv = "ml"
        else:
            quantidade_csv = numero_br(r["quantidade"])
            unidade_csv = "un"
        w.writerow([
            db.to_display(r["data"]), r["filial"], r["departamento"],
            r["item"], quantidade_csv, unidade_csv,
            r["numero_chamado"] or "", r["recebido_por"] or "",
        ])

    conteudo = output.getvalue()
    output.close()

    return "﻿" + conteudo