#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado da pagina de Despacho (com confirmacao de estoque negativo)."""

import reflex as rx
import logging
import db
from app_reflex.estados._helpers import _rows_to_dicts
from app_reflex.estados.estado_base import EstadoBase
from app_reflex.util_unidade import (
    tipo_por_nome,
    validar_quantidade_despacho, quantidade_despacho_para_armazenar,
    unidade_despacho_do_tipo, formatar_despacho, formatar_saldo_duplo,
)

logger = logging.getLogger(__name__)

class DespachoState(EstadoBase):
    """Estado da pagina de despacho para filial."""

    filiais: list[dict] = []
    deptos: list[dict] = []
    itens: list[dict] = []
    despachos: list[dict] = []
    saldo_item: float = 0
    saldo_txt: str = ""
    unidade: str = "un"  # unidade do campo de quantidade: "ml" (Tinta) ou "un"

    # Form em andamento
    data: str = ""
    filial_id: str = ""
    departamento_id: str = ""
    item_id: str = ""
    quantidade: str = ""
    chamado: str = ""
    recebedor: str = ""
    observacao: str = ""

    confirmacao_pendente: bool = False
    dados_pendentes: dict = {}

    def _item_por_id(self, item_id: str):
        """Retorna o dict do item pelo id (string). None se nao achar."""
        return next((i for i in self.itens if str(i["id"]) == item_id), None)

    @rx.event
    def carregar(self):
        try:
            self.filiais = _rows_to_dicts(db.listar("filiais"))
            self.deptos = _rows_to_dicts(db.listar("departamentos"))
            self.itens = _rows_to_dicts(db.listar_itens())
            mapa = tipo_por_nome(self.itens)
            self.despachos = _rows_to_dicts(db.ultimos_despachos(100))
            for d in self.despachos:
                d["tipo"] = mapa.get(str(d["item"]).lower(), "Toner")
                # Historico de despacho em ml para Tinta / un para demais
                d["qtd_txt"] = formatar_despacho(d["quantidade"], d["tipo"])
                d["unidade"] = unidade_despacho_do_tipo(d["tipo"])
            self.data = db.hoje()
            self.saldo_item = 0
            self.saldo_txt = ""
            self.unidade = unidade_despacho_do_tipo(
                self.itens[0]["tipo"] if self.itens else "Toner"
            )
            self.confirmacao_pendente = False
            self.dados_pendentes = {}
        except Exception:
            logger.exception("Erro ao carregar dados para despacho")
            self.notificar("Erro ao carregar dados para despacho.", "error")

    @rx.event
    def ao_mudar_item(self, valor: str):
        """Atualiza o saldo (dual L · ml) e a unidade do campo ao trocar item."""
        self.item_id = str(valor or "")
        item = self._item_por_id(self.item_id)
        self.saldo_item = db.saldo_atual(item["id"]) if item else 0
        self.unidade = unidade_despacho_do_tipo(item["tipo"]) if item else self.unidade
        self.saldo_txt = (
            formatar_saldo_duplo(self.saldo_item, item["tipo"]) if item else ""
        )

    @rx.event
    def salvar(self, form_data: dict):
        """Valida e registra ou solicita confirmacao de saldo negativo."""
        try:
            data_br = (form_data.get("data") or "").strip()
            filial_id = (form_data.get("filial_id") or "").strip()
            depto_id = (form_data.get("departamento_id") or "").strip()
            item_id = (form_data.get("item_id") or "").strip()
            qtd_str = (form_data.get("quantidade") or "").strip()
            chamado = (form_data.get("chamado") or "").strip()
            recebedor = (form_data.get("recebedor") or "").strip()
            observacao = (form_data.get("observacao") or "").strip()

            data_iso = db.to_iso(data_br)
            if not data_iso:
                self.notificar("Data invalida. Use o formato dd/mm/aaaa.", "error")
                return

            filial = next((f for f in self.filiais if str(f["id"]) == filial_id), None)
            if filial is None:
                self.notificar("Selecione a filial.", "error")
                return

            depto = next((d for d in self.deptos if str(d["id"]) == depto_id), None)
            if depto is None:
                self.notificar("Selecione o departamento.", "error")
                return

            item = self._item_por_id(item_id)
            if item is None:
                self.notificar("Selecione o item.", "error")
                return

            qtd, err = validar_quantidade_despacho(qtd_str, item["tipo"])
            if err:
                self.notificar(err, "error")
                return
            # Tinta: digitou em ml, armazena em L (÷1000). Toner/Cartucho: 'un'.
            qtd_l = quantidade_despacho_para_armazenar(qtd, item["tipo"])

            saldo = db.saldo_atual(item["id"])
            self.saldo_item = saldo
            self.saldo_txt = formatar_saldo_duplo(saldo, item["tipo"])

            # Estoques negativos exigem confirmacao explicita
            if qtd_l > saldo and not self.confirmacao_pendente:
                self.confirmacao_pendente = True
                self.dados_pendentes = {
                    "data": data_br,
                    "filial_id": filial_id,
                    "departamento_id": depto_id,
                    "item_id": item_id,
                    "quantidade": qtd_str,  # texto digitado (ml/un) p/ revalidar
                    "chamado": chamado,
                    "recebedor": recebedor,
                    "observacao": observacao,
                }
                self.notificar(
                    f"ATENCAO: saldo de '{item['nome']}' e {self.saldo_txt}, "
                    f"despachando {qtd} {self.unidade}. "
                    f"Estoque ficara negativo. Confirme o despacho.",
                    "warning",
                )
                return

            try:
                db.inserir_despacho(
                    data_iso, filial["id"], depto["id"], item["id"], qtd_l,
                    chamado, recebedor, observacao,
                )
            except Exception as e:
                logger.exception("Erro ao salvar despacho")
                self.notificar("Erro ao registrar despacho no banco de dados.", "error")
                return
            self._pos_salvar()
        except Exception as exc:
            logger.exception("Falha inesperada em salvar despacho: %s", exc)
            self.notificar("Erro inesperado ao salvar despacho.", "error")

    @rx.event
    def confirmar(self):
        """Confirma o despacho pendente (estoque negativo)."""
        try:
            pend = dict(self.dados_pendentes)
            if not pend:
                self.confirmacao_pendente = False
                return

            data_iso = db.to_iso(pend["data"])
            if not data_iso:
                self.notificar("Data invalida. Use o formato dd/mm/aaaa.", "error")
                self.confirmacao_pendente = False
                return

            filial = next((f for f in self.filiais if str(f["id"]) == pend["filial_id"]), None)
            depto = next((d for d in self.deptos if str(d["id"]) == pend["departamento_id"]), None)
            item = self._item_por_id(pend["item_id"])
            qtd, err = validar_quantidade_despacho(
                pend["quantidade"], item["tipo"] if item else "Toner"
            )
            if err:
                self.notificar("Quantidade invalida no despacho pendente.", "error")
                self.confirmacao_pendente = False
                return

            if filial is None or depto is None or item is None or qtd <= 0:
                self.notificar("Dados invalidos no despacho pendente.", "error")
                self.confirmacao_pendente = False
                return

            qtd_l = quantidade_despacho_para_armazenar(qtd, item["tipo"])
            try:
                db.inserir_despacho(
                    data_iso, filial["id"], depto["id"], item["id"], qtd_l,
                    pend.get("chamado"), pend.get("recebedor"), pend.get("observacao"),
                )
            except Exception as e:
                logger.exception("Erro ao confirmar despacho negativo no banco")
                self.notificar("Erro ao confirmar despacho no banco de dados.", "error")
                self.confirmacao_pendente = False
                return
            self._pos_salvar()
        except Exception as exc:
            logger.exception("Falha inesperada ao confirmar despacho: %s", exc)
            self.notificar("Erro inesperado ao confirmar despacho.", "error")

    @rx.event
    def cancelar(self):
        self.confirmacao_pendente = False
        self.dados_pendentes = {}
        self.notificar("Despacho cancelado.", "info")
        self._limpar_form()

    def _pos_salvar(self):
        """Apos registrar o despacho: notifica, recarrega tabela, limpa form."""
        self.confirmacao_pendente = False
        self.dados_pendentes = {}
        self.notificar("Despacho registrado com sucesso!", "success")
        mapa = tipo_por_nome(self.itens)
        self.despachos = _rows_to_dicts(db.ultimos_despachos(100))
        for d in self.despachos:
            d["tipo"] = mapa.get(str(d["item"]).lower(), "Toner")
            d["qtd_txt"] = formatar_despacho(d["quantidade"], d["tipo"])
            d["unidade"] = unidade_despacho_do_tipo(d["tipo"])
        self._limpar_form()
        self.saldo_item = 0
        self.saldo_txt = ""

    def _limpar_form(self):
        """Restaura o form para o estado inicial."""
        self.data = db.hoje()
        self.filial_id = ""
        self.departamento_id = ""
        self.item_id = ""
        self.quantidade = ""
        self.chamado = ""
        self.recebedor = ""
        self.observacao = ""