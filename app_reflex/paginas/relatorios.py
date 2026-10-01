#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pagina Relatorios — consulta e export dos despachos."""

import reflex as rx

from app_reflex.componentes import (
    menu_lateral, toast, page_header,
)
from app_reflex.estados import RelatoriosState

OPCOES_TODAS = "(Todas)"
OPCOES_TODOS = "(Todos)"


def _linha_relatorio(r: dict) -> rx.Component:
    """Linha da tabela de resultados do relatorio."""
    return rx.table.row(
        rx.table.cell(rx.text(r["data"], font_size="0.813rem", color="#475569"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(r["filial"], font_size="0.813rem", font_weight="500", color="#334155"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(r["departamento"], font_size="0.813rem", color="#475569"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(r["item"], font_size="0.813rem", color="#475569"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(r["qtd_txt"], font_size="0.813rem", font_weight="600"), padding="0.75rem 1rem"),
        rx.table.cell(rx.cond(
            r["numero_chamado"],
            rx.text(r["numero_chamado"], font_size="0.813rem", color="#64748b"),
            rx.text("-", font_size="0.813rem", color="#cbd5e1"),
        ), padding="0.75rem 1rem"),
        rx.table.cell(rx.cond(
            r["recebido_por"],
            rx.text(r["recebido_por"], font_size="0.813rem", color="#64748b"),
            rx.text("-", font_size="0.813rem", color="#cbd5e1"),
        ), padding="0.75rem 1rem"),
        class_name="table-row",
    )


def _linha_agregado(a: dict) -> rx.Component:
    """Linha da tabela de totais por filial/departamento."""
    return rx.table.row(
        rx.table.cell(rx.text(a["filial"], font_size="0.813rem", font_weight="500", color="#334155"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(a["departamento"], font_size="0.813rem", color="#475569"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(a["total_txt"], font_size="0.813rem", font_weight="700", color="#1e293b"), padding="0.75rem 1rem", text_align="center"),
        class_name="table-row",
    )


def _filtro_select(itens: list, name: str, placeholder: str, opcao_tudo: str) -> rx.Component:
    """Select de filtro com opcao 'Todos/Todas' fixa no inicio."""
    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width="100%"),
        rx.select.content(
            rx.select.group(
                rx.select.item(opcao_tudo, value=opcao_tudo),
                rx.foreach(
                    itens,
                    lambda i: rx.select.item(i["nome"], value=i["nome"]),
                ),
            ),
        ),
        name=name,
        width="100%",
    )


def _bloco_filtros() -> rx.Component:
    page = RelatoriosState
    return rx.box(
        rx.form.root(
            rx.grid(
                rx.vstack(
                    rx.text("De (dd/mm/aaaa)", font_size="0.75rem", font_weight="500", color="#64748b"),
                    rx.input(name="de", placeholder="Ex: 01/01/2025", value=page.filtro_de, width="100%"),
                    align="start",
                    spacing="2",
                ),
                rx.vstack(
                    rx.text("Ate (dd/mm/aaaa)", font_size="0.75rem", font_weight="500", color="#64748b"),
                    rx.input(name="ate", placeholder="Ex: 31/12/2025", value=page.filtro_ate, width="100%"),
                    align="start",
                    spacing="2",
                ),
                rx.vstack(
                    rx.text("Filial", font_size="0.75rem", font_weight="500", color="#64748b"),
                    _filtro_select(page.filiais, "filial", "Todas", OPCOES_TODAS),
                    align="start",
                    spacing="2",
                ),
                rx.vstack(
                    rx.text("Departamento", font_size="0.75rem", font_weight="500", color="#64748b"),
                    _filtro_select(page.deptos, "departamento", "Todos", OPCOES_TODOS),
                    align="start",
                    spacing="2",
                ),
                rx.vstack(
                    rx.text("Item", font_size="0.75rem", font_weight="500", color="#64748b"),
                    _filtro_select(page.itens, "item", "Todos", OPCOES_TODOS),
                    align="start",
                    spacing="2",
                ),
                rx.vstack(
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="search", width="0.875rem", height="0.875rem"),
                            rx.text("Filtrar", font_size="0.875rem"),
                            spacing="2",
                        ),
                        type="submit",
                        background="#2563eb",
                        color="white",
                        border_radius="0.75rem",
                        padding="0.625rem 1.25rem",
                        _hover={"background": "#1d4ed8"},
                        font_weight="500",
                        width="100%",
                    ),
                    align="start",
                    spacing="2",
                ),
                columns=rx.breakpoints({"base": "1", "sm": "2", "lg": "3", "xl": "6"}),
                spacing="4",
                width="100%",
            ),
            on_submit=page.filtrar,
            width="100%",
        ),
        padding="1.5rem",
        background="white",
        border="1px solid #f1f5f9",
        border_radius="1rem",
        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
        width="100%",
    )


def relatorios() -> rx.Component:
    page = RelatoriosState
    return rx.box(
        menu_lateral(),
        rx.box(
            toast(),
            rx.container(
                rx.vstack(
                    page_header("Relatorios", "Consulte e exporte os dados de despachos", "bar-chart-3"),
                    _bloco_filtros(),
                    # Resumo + export
                    rx.hstack(
                        rx.text(
                            f"{page.rows.length()} despacho(s) encontrado(s)",
                            font_size="0.875rem",
                            color="#475569",
                        ),
                        rx.text("-", font_size="0.875rem", color="#cbd5e1"),
                        rx.text(
                            f"{page.total_ml} ml de tinta despachada | {page.total_unidades} un em toner/cartucho",
                            font_size="0.875rem",
                            color="#475569",
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="download", width="0.875rem", height="0.875rem"),
                                rx.text("Exportar CSV", font_size="0.875rem"),
                                spacing="2",
                            ),
                            on_click=page.exportar_csv,
                            background="#f1f5f9",
                            color="#475569",
                            border_radius="0.75rem",
                            padding="0.625rem 1.25rem",
                            _hover={"background": "#e2e8f0"},
                            font_weight="500",
                        ),
                        spacing="4",
                        align="center",
                        width="100%",
                        margin_bottom="1rem",
                    ),
                    # Tabela de despachos
                    rx.box(
                        rx.cond(
                            page.rows.length() > 0,
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        *[
                                            rx.table.column_header_cell(t, padding="0.75rem 1rem", font_size="0.688rem", color="#94a3b8", text_align="left")
                                            for t in ["Data", "Filial", "Departamento", "Item", "Qtd", "Chamado", "Recebido por"]
                                        ]
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(page.rows, _linha_relatorio)
                                ),
                                width="100%",
                                size="2",
                            ),
                            rx.box(
                                rx.icon(tag="search", width="2.5rem", height="2.5rem", color="#e2e8f0"),
                                rx.text(
                                    "Nenhum despacho encontrado com os filtros selecionados.",
                                    font_size="0.875rem",
                                    color="#94a3b8",
                                    margin_top="0.5rem",
                                ),
                                padding="3rem 1rem",
                                text_align="center",
                                width="100%",
                            ),
                        ),
                        padding="1.5rem",
                        background="white",
                        border="1px solid #f1f5f9",
                        border_radius="1rem",
                        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
                        width="100%",
                        overflow_x="auto",
                    ),
                    # Totais por filial/departamento
                    rx.cond(
                        page.agregados.length() > 0,
                        rx.box(
                            rx.hstack(
                                rx.icon(tag="pie-chart", width="0.875rem", height="0.875rem", color="#94a3b8"),
                                rx.text("Total despachado por filial / departamento", font_size="0.875rem", font_weight="600", color="#1e293b"),
                                spacing="2",
                            ),
                            rx.divider(margin_y="0.75rem"),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        *[
                                            rx.table.column_header_cell(t, padding="0.75rem 1rem", font_size="0.688rem", color="#94a3b8", text_align="left")
                                            for t in ["Filial", "Departamento", "Total Itens"]
                                        ]
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(page.agregados, _linha_agregado)
                                ),
                                width="100%",
                                size="2",
                            ),
                            padding="1.5rem",
                            background="white",
                            border="1px solid #f1f5f9",
                            border_radius="1rem",
                            box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    width="100%",
                    spacing="6",
                ),
                padding=rx.breakpoints({"base": "1rem", "sm": "2rem"}),
                max_width="80rem",
            ),
            margin_left=rx.breakpoints({"base": "4rem", "sm": "16rem"}),
            min_height="100vh",
            background="#f8fafc",
        ),
        on_mount=page.carregar,
        width="100%",
        min_height="100vh",
    )