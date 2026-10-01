#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado da pagina de Estoques atuais (leituras com cores por saldo)."""

import reflex as rx
import logging
import db
from app_reflex.estados.estado_base import EstadoBase
from app_reflex.util_unidade import unidade_do_tipo, numero_br

logger = logging.getLogger(__name__)

class EstoqueState(EstadoBase):
    """Estado da pagina de estoque atual."""

    estoque: list[dict] = []
    total_itens: int = 0
    total_unidades: int = 0
    total_litros: str = "0"

    @rx.event
    def carregar(self):
        try:
            estoque = db.estoque_atual()
            # Marca em Python (lado servidor) se o saldo esta abaixo do minimo
            for r in estoque:
                r["baixo"] = bool(r["minimo"] > 0 and r["saldo"] <= r["minimo"])
                # Texto de quantidade pronto p/ exibicao na tabela
                unid = unidade_do_tipo(r["tipo"])
                r["unidade"] = unid
                r["qtd_txt"] = f"{numero_br(r['saldo'])} {unid}"
                r["ent_txt"] = f"+{numero_br(r['entradas'])} {unid}"
                r["sai_txt"] = f"-{numero_br(r['saidas'])} {unid}"
                r["min_txt"] = f"{numero_br(r['minimo'])} {unid}"
            self.estoque = estoque
            self.total_itens = len(estoque)
            litros = sum(r["saldo"] for r in estoque if unidade_do_tipo(r["tipo"]) == "L")
            self.total_litros = numero_br(litros)
            self.total_unidades = int(
                sum(r["saldo"] for r in estoque if unidade_do_tipo(r["tipo"]) != "L")
            )
        except Exception:
            logger.exception("Erro ao carregar estoque atual")
            self.notificar("Erro ao carregar estoque atual.", "error")