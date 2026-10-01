#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pagina Despacho — enviar suprimentos para filial, com confirmacao de estoque negativo."""

import reflex as rx

from app_reflex.componentes import (
    menu_lateral, toast, page_header, select_de_lista,
)
from app_reflex.estados import DespachoState


def _linha_saldo(item: dict) -> rx.Component:
    """Linha da tabela de despachos recentes."""
    return rx.table.row(
        rx.table.cell(rx.text(item["data"], font_size="0.813rem", color="#475569"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(item["filial"], font_size="0.813rem", font_weight="500", color="#334155"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(item["departamento"], font_size="0.813rem", color="#475569"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(item["item"], font_size="0.813rem", color="#475569"), padding="0.75rem 1rem"),
        rx.table.cell(rx.text(item["qtd_txt"], font_size="0.813rem", font_weight="600"), padding="0.75rem 1rem"),
        rx.table.cell(rx.cond(
            item["chamado"],
            rx.text(item["chamado"], font_size="0.813rem", color="#64748b"),
            rx.text("-", font_size="0.813rem", color="#cbd5e1"),
        ), padding="0.75rem 1rem"),
        rx.table.cell(rx.cond(
            item["recebido_por"],
            rx.text(item["recebido_por"], font_size="0.813rem", color="#64748b"),
            rx.text("-", font_size="0.813rem", color="#cbd5e1"),
        ), padding="0.75rem 1rem"),
        class_name="table-row",
    )


def despacho() -> rx.Component:
    page = DespachoState
    return rx.box(
        menu_lateral(),
        rx.box(
            toast(),
            rx.container(
                rx.vstack(
                    page_header("Despacho para Filial", "Envie suprimentos registrando a saida", "truck"),
                    # Formulario
                    rx.box(
                        rx.form.root(
                            rx.grid(
                                rx.vstack(
                                    rx.text("Data (dd/mm/aaaa)", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    rx.input(
                                        name="data",
                                        placeholder="Ex: 01/09/2026",
                                        required=True,
                                        width="100%",
                                        value=page.data,
                                        background="white",
                                        color="#1e293b",
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.text("Filial", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    select_de_lista(
                                        page.filiais,
                                        name="filial_id",
                                        placeholder="Selecione a filial",
                                        required=True,
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.text("Departamento", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    select_de_lista(
                                        page.deptos,
                                        name="departamento_id",
                                        placeholder="Selecione o departamento",
                                        required=True,
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.text("Item", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    select_de_lista(
                                        page.itens,
                                        name="item_id",
                                        placeholder="Selecione o item",
                                        required=True,
                                        on_change=page.ao_mudar_item,
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
                                        step="1",
                                        placeholder="0",
                                        required=True,
                                        width="100%",
                                        background="white",
                                        color="#1e293b",
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.text("N. Chamado", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    rx.input(
                                        name="chamado",
                                        placeholder="Opcional",
                                        width="100%",
                                        background="white",
                                        color="#1e293b",
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.vstack(
                                    rx.text("Recebido por", font_size="0.75rem", font_weight="500", color="#64748b"),
                                    rx.input(
                                        name="recebedor",
                                        placeholder="Opcional",
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
                                columns=rx.breakpoints({"base": "1", "sm": "2", "lg": "4"}),
                                spacing="4",
                                width="100%",
                            ),
                            # Saldo do item selecionado (dual L · ml p/ Tinta)
                            rx.cond(
                                page.saldo_txt != "",
                                rx.box(
                                    rx.text(
                                        f"Saldo atual do item: {page.saldo_txt}",
                                        font_size="0.813rem",
                                        color="#475569",
                                        padding="0.75rem",
                                    ),
                                    width="100%",
                                ),
                                rx.fragment(),
                            ),
                            rx.hstack(
                                rx.cond(
                                    page.confirmacao_pendente,
                                    rx.button(
                                        "Confirmar Despacho Negativo",
                                        on_click=page.confirmar,
                                        background="#d97706",
                                        color="white",
                                        border_radius="0.75rem",
                                        padding="0.625rem 1.25rem",
                                        _hover={"background": "#b45309"},
                                        font_weight="600",
                                    ),
                                    rx.button(
                                        rx.hstack(
                                            rx.icon(tag="truck", width="1rem", height="1rem"),
                                            rx.text("Registrar Despacho", font_size="0.875rem"),
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
                    # Aviso de confirmacao pendente
                    rx.cond(
                        page.confirmacao_pendente,
                        rx.box(
                            rx.hstack(
                                rx.icon(tag="triangle-alert", width="1.125rem", height="1.125rem", color="#d97706"),
                                rx.text(
                                    "Despacho com estoque negativo aguardando confirmacao.",
                                    font_size="0.875rem",
                                    font_weight="600",
                                    color="#92400e",
                                ),
                                spacing="3",
                            ),
                            padding="1.25rem",
                            background="#fffbeb",
                            border="1px solid #fde68a",
                            border_radius="1rem",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    # Tabela de despachos recentes
                    rx.box(
                        rx.hstack(
                            rx.text("Ultimos Despachos", font_size="0.875rem", font_weight="600", color="#1e293b"),
                            rx.icon(tag="history", width="1rem", height="1rem", color="#94a3b8"),
                            justify="between",
                            width="100%",
                        ),
                        rx.divider(margin_y="0.75rem"),
                        rx.cond(
                            page.despachos.length() > 0,
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
                                    rx.foreach(page.despachos, _linha_saldo)
                                ),
                                width="100%",
                                size="2",
                            ),
                            rx.text("Nenhum despacho registrado ainda.", font_size="0.875rem", color="#94a3b8", padding="0.75rem 1rem"),
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