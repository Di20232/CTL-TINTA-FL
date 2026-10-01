#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado da pagina de Entrada de estoque."""

import logging

import reflex as rx

import db

from app_reflex.estados._helpers import _rows_to_dicts
from app_reflex.estados.estado_base import EstadoBase
from app_reflex.util_unidade import unidade_do_tipo, numero_br, validar_quantidade, tipo_por_nome

logger = logging.getLogger(__name__)


class EntradaState(EstadoBase):
    """Estado da pagina de entrada de estoque."""

    itens: list[dict] = []
    entradas: list[dict] = []
    data: str = ""
    item_id: str = ""
    quantidade: str = ""
    fornecedor: str = ""
    valor_unitario: str = ""
    observacao: str = ""
    unidade: str = "un"

    @rx.event
    def carregar(self):
        try:
            self.itens = _rows_to_dicts(db.listar_itens())
            mapa = tipo_por_nome(self.itens)
            self.entradas = _rows_to_dicts(db.ultimas_entradas(100))
            for e in self.entradas:
                e["tipo"] = mapa.get(str(e["nome"]).lower(), "Toner")
                e["qtd_txt"] = f"{numero_br(e['quantidade'])} {unidade_do_tipo(e['tipo'])}"
                e["unidade"] = unidade_do_tipo(e["tipo"])
            self.data = db.hoje()
            self.unidade = unidade_do_tipo(
                self.itens[0]["tipo"] if self.itens else "Toner"
            )
        except Exception:
            logger.exception("Falha ao carregar pagina de entrada")
            self.notificar("Erro ao carregar dados. Contate o suporte.", "error")

    @rx.event
    def ao_mudar_item(self, valor: str):
        """Atualiza o rotulo de unidade quando o item selecionado muda."""
        self.item_id = str(valor or "")
        item = next((i for i in self.itens if str(i["id"]) == self.item_id), None)
        self.unidade = unidade_do_tipo(item["tipo"]) if item else self.unidade

    @rx.event
    def salvar(self, form_data: dict):
        # Usa data atual automaticamente (timestamp)
        data_iso = db.hoje_iso()
        item_id = (form_data.get("item_id") or "").strip()
        qtd_str = (form_data.get("quantidade") or "").strip()
        fornecedor = (form_data.get("fornecedor") or "").strip()
        valor_str = (form_data.get("valor_unitario") or "").strip()
        observacao = (form_data.get("observacao") or "").strip()

        # Valida item: deve existir entre os itens reais do banco
        item = next((i for i in self.itens if str(i["id"]) == item_id), None)
        if item is None:
            logger.warning(
                "Tentativa de entrada com item invalido: item_id=%s", item_id
            )
            self.notificar("Selecione um item valido.", "error")
            return

        qtd, err = validar_quantidade(qtd_str, item["tipo"])
        if err:
            logger.warning(
                "Quantidade invalida para item %s (tipo=%s): %s",
                item.get("nome"), item.get("tipo"), err,
            )
            self.notificar(err, "error")
            return

        valor = None
        if valor_str:
            try:
                valor = float(valor_str.replace(",", "."))
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "Valor unitario invalido para item %s: %r (%s)",
                    item.get("nome"), valor_str, exc,
                )
                self.notificar("Valor unitario invalido.", "error")
                return

        try:
            db.inserir_entrada(
                data_iso, item["id"], qtd, fornecedor, valor, observacao
            )
        except Exception:
            logger.exception(
                "Erro ao registrar entrada (item_id=%s, qtd=%s, valor=%s)",
                item["id"], qtd, valor,
            )
            self.notificar("Erro ao registrar entrada. Contate o suporte.", "error")
            return

        logger.info(
            "Entrada registrada: item=%s (id=%s) qtd=%s valor=%s fornecedor=%s",
            item.get("nome"), item["id"], qtd, valor, fornecedor,
        )
        self.notificar("Entrada registrada com sucesso!", "success")
        try:
            # Recarrega tabela (com texto de quantidade ja formatado por unidade)
            mapa = tipo_por_nome(self.itens)
            self.entradas = _rows_to_dicts(db.ultimas_entradas(100))
            for e in self.entradas:
                e["tipo"] = mapa.get(str(e["nome"]).lower(), "Toner")
                e["qtd_txt"] = f"{numero_br(e['quantidade'])} {unidade_do_tipo(e['tipo'])}"
                e["unidade"] = unidade_do_tipo(e["tipo"])
            self.data = db.hoje()
        except Exception:
            logger.exception("Falha ao recarregar tabela de entradas apos registro")
        finally:
            self.item_id = ""
            self.quantidade = ""
            self.fornecedor = ""
            self.valor_unitario = ""
            self.observacao = ""