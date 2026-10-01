#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pagina Entrada de Estoque — registrar recebimentos."""

import reflex as rx

from app_reflex.componentes import (
    menu_lateral, toast, page_header, select_de_lista,
)
from app_reflex.estados import EntradaState


def entrada() -> rx.Component:
    page = EntradaState
    return rx.box(
        menu_lateral(),
        rx.box(
            toast(),
            rx.container(
                rx.vstack(
                    page_header("Entrada de Estoque", "Registre recebimentos de suprimentos", "package-plus"),
                    # Formulario
                    rx.box(
                        rx.form.root(
                            rx.grid(
                                rx.vstack(
                                    rx.text("Item", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    select_de_lista(
                                        page.itens,
                                        name="item_id",
                                        placeholder="Selecione o item",
                                        required=True,
                                        on_change=page.ao_mudar_item,
                                        color="#1e293b",
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.hstack(
                                        rx.text("Quantidade", font_size="0.75rem", font_weight="500", color="#64748b"),
                                        rx.text(
                                            f"({page.unidade})",
                                            font_size="0.688rem",
                                            color="#94a3b8",
                                        ),
                                        spacing="1",
                                    ),
                                    rx.input(
                                        name="quantidade",
                                        type="number",
                                        min=0,
                                        step="0.5",
                                        placeholder="0",
                                        required=True,
                                        width="100%",
                                        background="white",
                                        color="#f7f7f7",
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.text("Valor unitario", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    rx.input(
                                        name="valor_unitario",
                                        type="number",
                                        step="0.01",
                                        placeholder="0,00",
                                        width="100%",
                                        background="white",
                                        color="#1e293b",
                                    ),
                                    rx.text("Opcional", font_size="0.688rem", color="#94a3b8"),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.text("Fornecedor", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    rx.input(
                                        name="fornecedor",
                                        placeholder="Nome do fornecedor",
                                        width="100%",
                                        background="white",
                                        color="#1e293b",
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.text("Observacao", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    rx.text_area(
                                        name="observacao",
                                        placeholder="Notas (opcional)",
                                        width="100%",
                                        rows="1",
                                        background="white",
                                        color="#1e293b",
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                columns=rx.breakpoints({"base": "1", "sm": "2", "lg": "3"}),
                                spacing="4",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.button(
                                    rx.hstack(
                                        rx.icon(tag="save", width="1rem", height="1rem"),
                                        rx.text("Registrar Entrada", font_size="0.875rem"),
                                        spacing="2",
                                    ),
                                    type="submit",
                                    background="#2563eb",
                                    color="white",
                                    border_radius="0.75rem",
                                    padding="0.625rem 1.25rem",
                                    _hover={"background": "#1d4ed8"},
                                    font_weight="500",
                                ),
                                rx.button(
                                    "Limpar",
                                    type="reset",
                                    background="#f1f5f9",
                                    color="#475569",
                                    border_radius="0.75rem",
                                    padding="0.625rem 1.25rem",
                                    _hover={"background": "#e2e8f0"},
                                    font_weight="500",
                                ),
                                spacing="3",
                            ),
                            on_submit=page.salvar,
                            reset_on_submit=True,
                            width="100%",
                        ),
                        padding="1.5rem",
                        background="white",
                        border="1px solid #f1f5f9",
                        border_radius="1rem",
                        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
                        width="100%",
                    ),
                    # Tabela de entradas recentes
                    rx.box(
                        rx.hstack(
                            rx.text("Entradas Recentes", font_size="0.875rem", font_weight="600", color="#1e293b"),
                            rx.icon(tag="history", width="1rem", height="1rem", color="#94a3b8"),
                            justify="between",
                            width="100%",
                        ),
                        rx.divider(margin_y="0.75rem"),
                        rx.cond(
                            page.entradas.length() > 0,
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        *[
                                            rx.table.column_header_cell(t, padding="0.75rem 1rem", font_size="0.688rem", color="#94a3b8", text_align="left")
                                            for t in ["Data", "Item", "Qtd", "Fornecedor", "Valor"]
                                        ]
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(
                                        page.entradas,
                                        lambda e: rx.table.row(
                                            rx.table.cell(rx.text(e["data"], font_size="0.813rem", color="#475569"), padding="0.75rem 1rem"),
                                            rx.table.cell(rx.text(e["nome"], font_size="0.813rem", font_weight="500", color="#334155"), padding="0.75rem 1rem"),
                                            rx.table.cell(rx.text(f"+{e['qtd_txt']}", font_size="0.813rem", font_weight="700", color="#059669"), padding="0.75rem 1rem"),
                                            rx.table.cell(rx.cond(e["fornecedor"], rx.text(e["fornecedor"], font_size="0.813rem", color="#64748b"), rx.text("-", font_size="0.813rem", color="#cbd5e1")), padding="0.75rem 1rem"),
                                            rx.table.cell(rx.cond(
                                                e["valor_unitario"],
                                                rx.text(e["valor_unitario"], font_size="0.813rem", color="#64748b"),
                                                rx.text("-", font_size="0.813rem", color="#cbd5e1"),
                                            ), padding="0.75rem 1rem"),
                                            class_name="table-row",
                                        )
                                    )
                                ),
                                width="100%",
                                size="2",
                            ),
                            rx.text("Nenhuma entrada registrada ainda.", font_size="0.875rem", color="#94a3b8", padding="0.75rem 1rem"),
                        ),
                        padding="1.5rem",
                        background="white",
                        border="1px solid #f1f5f9",
                        border_radius="1rem",
                        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
                        width="100%",
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