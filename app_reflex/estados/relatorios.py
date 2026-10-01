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

    @staticmethod
    def _mascara_data(valor: str) -> str:
        """Aplica mascara dd/mm/aaaa: insere barras automaticamente."""
        digitos = "".join(c for c in valor if c.isdigit())
        digitos = digitos[:8]
        if len(digitos) > 4:
            return f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"
        if len(digitos) > 2:
            return f"{digitos[:2]}/{digitos[2:]}"
        return digitos

    @rx.event
    def set_filtro_de(self, valor: str):
        self.filtro_de = self._mascara_data(valor)

    @rx.event
    def set_filtro_ate(self, valor: str):
        self.filtro_ate = self._mascara_data(valor)

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

        try:
            self._aplicar(filtro)
        except Exception:
            logger.exception("Erro ao filtrar relatorio")
            self.notificar("Erro ao consultar o relatorio. Tente novamente.", "error")

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
        # Nunca soma ml com un: cada (filial, depto) guarda um total por unidade.
        by = {}
        for r in self.rows:
            chave = (r["filial"], r["departamento"])
            u = "ml" if unidade_despacho_do_tipo(r["tipo"]) == "ml" else "un"
            totais = by.setdefault(chave, {"ml": 0, "un": 0})
            totais[u] += r["qtd_display"]
        agreg = []
        for (filial, depto), totais in by.items():
            partes = [
                f"{numero_br(totais[u])} {u}" for u in ("un", "ml") if totais[u]
            ]
            agreg.append({
                "filial": filial,
                "departamento": depto,
                "total": totais["un"] + totais["ml"],  # so para ordenar
                "total_txt": " + ".join(partes),
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
                if not iso:
                    self.notificar("Data 'De' invalida. Corrija antes de exportar.", "error")
                    return
                filtro["de"] = iso
            if self.filtro_ate:
                iso = db.to_iso(self.filtro_ate)
                if not iso:
                    self.notificar("Data 'Ate' invalida. Corrija antes de exportar.", "error")
                    return
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