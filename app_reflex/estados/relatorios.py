#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado da pagina de Relatorios (filtros + export CSV)."""

import reflex as rx
import logging
import db
from app_reflex.estados._helpers import _rows_to_dicts
from app_reflex.estados.estado_base import EstadoBase
from app_reflex.util_unidade import (
    numero_br, tipo_por_nome,
    unidade_despacho_do_tipo, formatar_despacho,
    quantidade_despacho_display,
)

logger = logging.getLogger(__name__)

class RelatoriosState(EstadoBase):
    """Estado da pagina de relatorios."""

    filiais: list[dict] = []
    deptos: list[dict] = []
    itens: list[dict] = []
    rows: list[dict] = []
    total_qtd: int = 0
    total_ml: str = "0"       # soma das tintas DESPACHADAS em ml (exibicao)
    total_unidades: int = 0
    agregados: list[dict] = []  # cada: {filial, departamento, total}

    # Filtros (datas em BR p/ exibicao no input)
    filtro_de: str = ""
    filtro_ate: str = ""
    filtro_filial: str = ""
    filtro_departamento: str = ""
    filtro_item: str = ""
    csv_pronto: str = ""

    @rx.event
    def carregar(self):
        try:
            self.filiais = _rows_to_dicts(db.listar("filiais"))
            self.deptos = _rows_to_dicts(db.listar("departamentos"))
            self.itens = _rows_to_dicts(db.listar_itens())
            self._aplicar({})
        except Exception:
            logger.exception("Erro ao carregar filtros em relatorios")
            self.notificar("Erro ao carregar filtros de relatorio.", "error")

    @rx.event
    def filtrar(self, form_data: dict):
        de_br = (form_data.get("de") or "").strip()
        ate_br = (form_data.get("ate") or "").strip()
        filial = (form_data.get("filial") or "").strip()
        depto = (form_data.get("departamento") or "").strip()
        item = (form_data.get("item") or "").strip()

        # Guarda valores p/ reexibir no form
        self.filtro_de = de_br
        self.filtro_ate = ate_br
        self.filtro_filial = filial
        self.filtro_departamento = depto
        self.filtro_item = item

        filtro = {}
        if de_br:
            de_iso = db.to_iso(de_br)
            if not de_iso:
                self.notificar("Data 'De' invalida.", "error")
                return
            filtro["de"] = de_iso
        if ate_br:
            ate_iso = db.to_iso(ate_br)
            if not ate_iso:
                self.notificar("Data 'Ate' invalida.", "error")
                return
            filtro["ate"] = ate_iso
        if filial and filial != "(Todas)":
            filtro["filial"] = filial
        if depto and depto != "(Todos)":
            filtro["departamento"] = depto
        if item and item != "(Todos)":
            filtro["item"] = item

        self._aplicar(filtro)

    def _aplicar(self, filtro: dict):
        """Consulta e agrega os resultados do relatorio."""
        rows = db.relatorio_despachos(filtro)
        self.rows = _rows_to_dicts(rows)
        mapa = tipo_por_nome(self.itens)
        for r in self.rows:
            r["tipo"] = mapa.get(str(r["item"]).lower(), "Toner")
            # Historico de despacho em ml para Tinta / un para demais
            r["qtd_txt"] = formatar_despacho(r["quantidade"], r["tipo"])
            r["unidade"] = unidade_despacho_do_tipo(r["tipo"])
            # Valor exibivel p/ somar (ml/un), na unidade de exibicao
            r["qtd_display"] = quantidade_despacho_display(r["quantidade"], r["tipo"])
        self.total_qtd = sum(r["quantidade"] for r in self.rows)
        ml = sum(
            r["qtd_display"]
            for r in self.rows if unidade_despacho_do_tipo(r["tipo"]) == "ml"
        )
        self.total_ml = numero_br(ml)
        self.total_unidades = int(
            sum(
                r["qtd_display"]
                for r in self.rows if unidade_despacho_do_tipo(r["tipo"]) == "un"
            )
        )

        # Agrega por (filial, departamento), somando na unidade de exibicao
        by = {}
        unid_by = {}
        for r in self.rows:
            chave = (r["filial"], r["departamento"])
            by[chave] = by.get(chave, 0) + r["qtd_display"]
            u = unidade_despacho_do_tipo(r["tipo"])
            unid_by.setdefault(chave, set()).add("ml" if u == "ml" else "un")
        agreg = []
        for (filial, depto), total in by.items():
            unids = unid_by[(filial, depto)]
            suf = (
                "ml"
                if unids == {"ml"}
                else ("un" if unids == {"un"} else "")
            )
            agreg.append({
                "filial": filial,
                "departamento": depto,
                "total": total,
                "total_txt": f"{numero_br(total)} {suf}".strip(),
            })
        self.agregados = sorted(agreg, key=lambda x: -x["total"])

    @rx.event
    def exportar_csv(self):
        """Gera o CSV filtrado e retorna evento de download."""
        try:
            from app_reflex.util_csv import gerar_csv_relatorio
            filtro = {}
            if self.filtro_de:
                iso = db.to_iso(self.filtro_de)
                if iso:
                    filtro["de"] = iso
            if self.filtro_ate:
                iso = db.to_iso(self.filtro_ate)
                if iso:
                    filtro["ate"] = iso
            if self.filtro_filial and self.filtro_filial != "(Todas)":
                filtro["filial"] = self.filtro_filial
            if self.filtro_departamento and self.filtro_departamento != "(Todos)":
                filtro["departamento"] = self.filtro_departamento
            if self.filtro_item and self.filtro_item != "(Todos)":
                filtro["item"] = self.filtro_item

            try:
                conteudo = gerar_csv_relatorio(filtro)
            except Exception:
                logger.exception("Erro ao gerar CSV de relatorio")
                self.notificar("Erro ao exportar relatorio para CSV.", "error")
                return
            self.csv_pronto = conteudo
            return rx.download(
                data=conteudo,
                filename="relatorio_despachos.csv",
                mime_type="text/csv",
            )
        except Exception:
            logger.exception("Falha inesperada ao exportar relatorio")
            self.notificar("Erro inesperado ao exportar CSV.", "error")