#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado da pagina Dashboard (resumo, alertas, ultimos movimentos)."""

import reflex as rx
import logging
import db
from app_reflex.estados._helpers import _row_to_dict, _rows_to_dicts
from app_reflex.estados.estado_base import EstadoBase
from app_reflex.util_unidade import (
    unidade_do_tipo, numero_br, tipo_por_nome,
    unidade_despacho_do_tipo, formatar_despacho,
)

logger = logging.getLogger(__name__)

class DashboardState(EstadoBase):
    """Estado do painel de resumo."""

    stats: dict = {}
    alertas: list[dict] = []
    ult_despachos: list[dict] = []
    ult_entradas: list[dict] = []

    @rx.event
    def carregar(self):
        try:
            dados = db.dashboard_stats()
            # Formata valores para exibição
            self.stats = {
                "total_filiais": dados["total_filiais"],
                "total_deptos": dados["total_deptos"],
                "total_itens": dados["total_itens"],
                "saldo_litros": numero_br(dados["saldo_litros"]),
                "saldo_unidades": numero_br(dados["saldo_unidades"]),
            }
            self.alertas = _rows_to_dicts(dados["alertas"])
            mapa = tipo_por_nome(_rows_to_dicts(db.listar_itens()))
            self.ult_despachos = _rows_to_dicts(dados["ult_despachos"])
            for d in self.ult_despachos:
                d["tipo"] = mapa.get(str(d["item"]).lower(), "Toner")
                # Historico de despacho em ml para Tinta / un para demais
                d["qtd_txt"] = formatar_despacho(d["quantidade"], d["tipo"])
                d["unidade"] = unidade_despacho_do_tipo(d["tipo"])
            self.ult_entradas = _rows_to_dicts(dados["ult_entradas"])
            for e in self.ult_entradas:
                e["tipo"] = mapa.get(str(e["nome"]).lower(), "Toner")
                e["qtd_txt"] = f"{numero_br(e['quantidade'])} {unidade_do_tipo(e['tipo'])}"
                e["unidade"] = unidade_do_tipo(e["tipo"])
        except Exception:
            logger.exception("Erro ao carregar dados do dashboard")
            self.notificar("Erro ao carregar dados do dashboard.", "error")