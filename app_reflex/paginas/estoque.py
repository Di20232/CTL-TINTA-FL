#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pagina Estoque Atual — tabela com cores por saldo."""

import reflex as rx

from app_reflex.componentes import (
    menu_lateral, toast, page_header, badge_tipo,
)
from app_reflex.estados import EstoqueState


def _linha_estoque(item: dict) -> rx.Component:
    """Linha da tabela de estoque. Vermelha quando saldo <= minimo (>0)."""
    return rx.cond(
        item["baixo"],
        rx.table.row(
            rx.table.cell(
                rx.text(item["nome"], font_size="0.813rem", font_weight="500", color="#334155"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                badge_tipo(item["tipo"]),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text(item["min_txt"], font_size="0.813rem", color="#b91c1c", text_align="center"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text(item["ent_txt"], font_size="0.813rem", color="#059669", text_align="center"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text(item["sai_txt"], font_size="0.813rem", color="#c02626", text_align="center"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text(item["qtd_txt"], font_size="0.813rem", font_weight="700", color="#b91c1c", text_align="center"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.badge("Estoque Baixo", variant="solid", color_scheme="red", font_size="0.688rem"),
                padding="0.75rem 1rem",
            ),
            class_name="table-row",
            background="#fef2f2",
        ),
        rx.table.row(
            rx.table.cell(
                rx.text(item["nome"], font_size="0.813rem", font_weight="500", color="#334155"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                badge_tipo(item["tipo"]),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text(item["min_txt"], font_size="0.813rem", color="#64748b", text_align="center"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text(item["ent_txt"], font_size="0.813rem", color="#059669", text_align="center"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text(item["sai_txt"], font_size="0.813rem", color="#c02626", text_align="center"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text(item["qtd_txt"], font_size="0.813rem", font_weight="700", color="#1e293b", text_align="center"),
                padding="0.75rem 1rem",
            ),
            rx.table.cell(
                rx.text("OK", font_size="0.75rem", color="#10b981", font_weight="600"),
                padding="0.75rem 1rem",
            ),
            class_name="table-row",
            background="transparent",
        ),
    )


def estoque() -> rx.Component:
    page = EstoqueState
    return rx.box(
        menu_lateral(),
        rx.box(
            toast(),
            rx.container(
                rx.vstack(
                    page_header("Estoque Atual", "Situacao dos itens de suprimento", "boxes"),
                    # Resumo rapido
                    rx.hstack(
                        rx.text(
                            f"{page.total_itens} item(s) em cadastro",
                            font_size="0.875rem",
                            color="#475569",
                        ),
                        rx.text(
                            "-",
                            font_size="0.875rem",
                            color="#cbd5e1",
                        ),
                        rx.text(
                            f"{page.total_litros} L de tinta | {page.total_unidades} un em toner/cartucho",
                            font_size="0.875rem",
                            color="#475569",
                        ),
                        spacing="3",
                        align="center",
                        margin_bottom="1rem",
                    ),
                    # Tabela
                    rx.box(
                        rx.cond(
                            page.estoque.length() > 0,
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        *[
                                            rx.table.column_header_cell(t, padding="0.75rem 1rem", font_size="0.688rem", color="#94a3b8", text_align="center")
                                            for t in ["Item", "Tipo", "Minimo", "Entradas", "Saidas", "Saldo", "Status"]
                                        ]
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(page.estoque, _linha_estoque)
                                ),
                                width="100%",
                                size="2",
                            ),
                            rx.text("Nenhum item cadastrado ainda.", font_size="0.875rem", color="#94a3b8", padding="0.75rem 1rem"),
                        ),
                        padding="1.5rem",
                        background="white",
                        border="1px solid #f1f5f9",
                        border_radius="1rem",
                        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
                        width="100%",
                        overflow_x="auto",
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