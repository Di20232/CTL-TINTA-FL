#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pagina Cadastros — CRUD de filiais, departamentos e itens."""

import reflex as rx

from app_reflex.componentes import (
    menu_lateral, toast, page_header, badge_tipo,
)
from app_reflex.estados import CadastrosState


def _bloco_cadastro_filial() -> rx.Component:
    page = CadastrosState
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(tag="building-2", width="1rem", height="1rem", color="#2563eb"),
                width="2.25rem",
                height="2.25rem",
                border_radius="0.625rem",
                background="#2563eb15",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.text("Filiais", font_size="0.875rem", font_weight="600", color="#1e293b"),
            spacing="3",
            align="center",
        ),
        rx.divider(margin_y="0.625rem"),
        rx.form.root(
            rx.hstack(
                rx.input(
                    name="nome",
                    placeholder="Nome da filial",
                    required=True,
                    flex="1",
                    background="white",
                    color="#1e293b",
                ),
                rx.button(
                    rx.hstack(
                        rx.icon(tag="plus", width="0.875rem", height="0.875rem"),
                        rx.text("Adicionar", font_size="0.875rem"),
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
                spacing="3",
                width="100%",
            ),
            on_submit=page.adicionar_filial,
            reset_on_submit=True,
            width="100%",
        ),
        rx.vstack(
            rx.foreach(
                page.filiais,
                lambda f: rx.hstack(
                    rx.text(f["nome"], font_size="0.813rem", color="#334155"),
                    rx.spacer(),
                    rx.button(
                        rx.icon(tag="trash-2", width="0.875rem", height="0.875rem", color="#f87171"),
                        on_click=page.excluir("filiais", f["id"]),
                        type="button",
                        variant="ghost",
                        color="#ef4444",
                        padding="0.25rem",
                        _hover={"bg": "#fef2f2", "color": "#dc2626"},
                    ),
                    justify="between",
                    width="100%",
                    padding="0.4rem 0",
                ),
            ),
            spacing="1",
            width="100%",
            margin_top="0.75rem",
        ),
        padding="1.25rem",
        background="white",
        border="1px solid #f1f5f9",
        border_radius="1rem",
        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
        width="100%",
    )


def _bloco_cadastro_depto() -> rx.Component:
    page = CadastrosState
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(tag="layers", width="1rem", height="1rem", color="#06b6d4"),
                width="2.25rem",
                height="2.25rem",
                border_radius="0.625rem",
                background="#06b6d415",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.text("Departamentos", font_size="0.875rem", font_weight="600", color="#1e293b"),
            spacing="3",
            align="center",
        ),
        rx.divider(margin_y="0.625rem"),
        rx.form.root(
            rx.hstack(
                rx.input(
                    name="nome",
                    placeholder="Nome do departamento",
                    required=True,
                    flex="1",
                    background="white",
                    color="#1e293b",
                ),
                rx.button(
                    rx.hstack(
                        rx.icon(tag="plus", width="0.875rem", height="0.875rem"),
                        rx.text("Adicionar", font_size="0.875rem"),
                        spacing="2",
                    ),
                    type="submit",
                    background="#06b6d4",
                    color="white",
                    border_radius="0.75rem",
                    padding="0.625rem 1.25rem",
                    _hover={"background": "#0891b2"},
                    font_weight="500",
                ),
                spacing="3",
                width="100%",
            ),
            on_submit=page.adicionar_depto,
            reset_on_submit=True,
            width="100%",
        ),
        rx.vstack(
            rx.foreach(
                page.deptos,
                lambda d: rx.hstack(
                    rx.text(d["nome"], font_size="0.813rem", color="#334155"),
                    rx.spacer(),
                    rx.button(
                        rx.icon(tag="trash-2", width="0.875rem", height="0.875rem", color="#f87171"),
                        on_click=page.excluir("departamentos", d["id"]),
                        type="button",
                        variant="ghost",
                        color="#ef4444",
                        padding="0.25rem",
                        _hover={"bg": "#fef2f2", "color": "#dc2626"},
                    ),
                    justify="between",
                    width="100%",
                    padding="0.4rem 0",
                ),
            ),
            spacing="1",
            width="100%",
            margin_top="0.75rem",
        ),
        padding="1.25rem",
        background="white",
        border="1px solid #f1f5f9",
        border_radius="1rem",
        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
        width="100%",
    )


def _bloco_cadastro_item() -> rx.Component:
    page = CadastrosState
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(tag="package", width="1rem", height="1rem", color="#8b5cf6"),
                width="2.25rem",
                height="2.25rem",
                border_radius="0.625rem",
                background="#8b5cf615",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.text("Itens de Suprimento", font_size="0.875rem", font_weight="600", color="#1e293b"),
            spacing="3",
            align="center",
        ),
        rx.divider(margin_y="0.625rem"),
        rx.form.root(
            rx.grid(
                rx.vstack(
                    rx.text("Nome", font_size="0.75rem", font_weight="500", color="#64748b"),
                    rx.input(
                        name="nome",
                        placeholder="Ex: Toner HP 12A",
                        required=True,
                        width="100%",
                        background="white",
                        color="#1e293b",
                    ),
                    align="start",
                    spacing="2",
                ),
                rx.vstack(
                    rx.text("Tipo", font_size="0.75rem", font_weight="500", color="#64748b"),
                    rx.select(
                        ["Toner", "Tinta", "Cartucho"],
                        name="tipo",
                        placeholder="Tipo",
                        width="100%",
                        default_value="Toner",
                        css={"background": "white", "color": "#1e293b"},
                    ),
                    align="start",
                    spacing="2",
                ),
                rx.vstack(
                    rx.text("Estoque minimo", font_size="0.75rem", font_weight="500", color="#64748b"),
                    rx.input(
                        name="estoque_minimo",
                        type="number",
                        min=0,
                        step=1,
                        placeholder="Tinta: 1L | Toner: 5un",
                        width="100%",
                        background="white",
                        color="#1e293b",
                    ),
                    rx.text("Deixe vazio para usar padrão", font_size="0.688rem", color="#94a3b8"),
                    align="start",
                    spacing="2",
                ),
                rx.vstack(
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="plus", width="0.875rem", height="0.875rem"),
                            rx.text("Adicionar Item", font_size="0.875rem"),
                            spacing="2",
                        ),
                        type="submit",
                        background="#8b5cf6",
                        color="white",
                        border_radius="0.75rem",
                        padding="0.625rem 1.25rem",
                        _hover={"background": "#7c3aed"},
                        font_weight="500",
                        width="100%",
                    ),
                    align="start",
                    spacing="2",
                ),
                columns=rx.breakpoints({"base": "1", "sm": "2", "lg": "4"}),
                spacing="4",
                width="100%",
            ),
            on_submit=page.adicionar_item,
            reset_on_submit=True,
            width="100%",
        ),
        rx.cond(
            page.itens.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        *[
                            rx.table.column_header_cell(t, padding="0.75rem 1rem", font_size="0.688rem", color="#94a3b8", text_align="left")
                            for t in ["Item", "Tipo", "Minimo", ""]
                        ]
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        page.itens,
                        lambda i: rx.table.row(
                            rx.table.cell(rx.text(i["nome"], font_size="0.813rem", font_weight="500", color="#334155"), padding="0.75rem 1rem"),
                            rx.table.cell(badge_tipo(i["tipo"]), padding="0.75rem 1rem"),
                            rx.table.cell(rx.text(i["min_txt"], font_size="0.813rem", color="#64748b"), padding="0.75rem 1rem"),
                            rx.table.cell(
                                rx.button(
                                    rx.icon(tag="trash-2", width="0.875rem", height="0.875rem", color="#f87171"),
                                    on_click=page.excluir("itens", i["id"]),
                                    type="button",
                                    variant="ghost",
                                    color="#ef4444",
                                    padding="0.25rem",
                                    _hover={"bg": "#fef2f2", "color": "#dc2626"},
                                ),
                                padding="0.75rem 1rem",
                            ),
                            class_name="table-row",
                        )
                    )
                ),
                width="100%",
                size="2",
            ),
            rx.text("Nenhum item cadastrado ainda.", font_size="0.875rem", color="#94a3b8", padding="0.75rem 1rem"),
        ),
        padding="1.25rem",
        background="white",
        border="1px solid #f1f5f9",
        border_radius="1rem",
        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
        width="100%",
    )


def _dialog_exclusao() -> rx.Component:
    """Dialogo de confirmacao para excluir registro com lançamentos vinculados."""
    page = CadastrosState
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title(
                "Excluir registro?",
                font_size="1.125rem",
                font_weight="700",
                color="#1e293b",
            ),
            rx.alert_dialog.description(
                f"O registro '{page.confirm_nome}' possui {page.confirm_total} "
                f"{page.confirm_rotulo} vinculado(s). Excluir remove também "
                f"esses lançamentos. Deseja continuar?",
                font_size="0.875rem",
                color="#475569",
                margin_top="0.5rem",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancelar",
                        on_click=page.cancelar_exclusao,
                        variant="soft",
                        color_scheme="gray",
                    )
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Excluir tudo",
                        on_click=page.confirmar_exclusao_cascata,
                        background="#dc2626",
                        color="white",
                        _hover={"background": "#b91c1c"},
                    )
                ),
                spacing="3",
                justify="end",
                margin_top="1.25rem",
                width="100%",
            ),
            max_width="26rem",
        ),
        open=page.confirm_open,
        on_open_change=page.cancelar_exclusao,
    )


def cadastros() -> rx.Component:
    page = CadastrosState
    return rx.box(
        menu_lateral(),
        rx.box(
            toast(),
            _dialog_exclusao(),
            rx.container(
                rx.vstack(
                    page_header("Cadastros", "Gerencie filiais, departamentos e itens", "settings"),
                    rx.grid(
                        _bloco_cadastro_filial(),
                        _bloco_cadastro_depto(),
                        columns=rx.breakpoints({"base": "1", "lg": "2"}),
                        spacing="4",
                        width="100%",
                    ),
                    _bloco_cadastro_item(),
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