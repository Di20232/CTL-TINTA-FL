#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pagina Dashboard — resumo, alertas e ultimos movimentos."""

import reflex as rx

from app_reflex.componentes import (
    menu_lateral, toast, cartao_stats, page_header,
)
from app_reflex.estados import DashboardState


def _card_alerta(alerta: dict) -> rx.Component:
    """Linha de alerta de estoque abaixo do minimo."""
    return rx.hstack(
        rx.icon(tag="triangle-alert", width="1rem", height="1rem", color="#d97706"),
        rx.text(
            f"{alerta['nome']}: saldo {alerta['saldo']} (minimo {alerta['estoque_minimo']})",
            font_size="0.875rem",
            color="#92400e",
        ),
        spacing="3",
        align="center",
        padding="0.625rem 0",
        width="100%",
    )


def _linha_entrada(r: dict) -> rx.Component:
    """Linha de uma entrada no bloco de ultimos movimentos."""
    return rx.hstack(
        rx.icon(tag="package-plus", width="0.875rem", height="0.875rem", color="#059669"),
        rx.text(
            f"{r['nome']} +{r['qtd_txt']}",
            font_size="0.813rem",
            color="#334155",
        ),
        rx.cond(r["fornecedor"], rx.text(r["fornecedor"], font_size="0.75rem", color="#64748b"), rx.text(""),),
        rx.text(r["data"], font_size="0.75rem", color="#94a3b8"),
        justify="between",
        width="100%",
        padding="0.4rem 0",
    )


def _linha_despacho(r: dict) -> rx.Component:
    """Linha de um despacho no bloco de ultimos movimentos."""
    return rx.hstack(
        rx.icon(tag="truck", width="0.875rem", height="0.875rem", color="#2563eb"),
        rx.text(
            f"{r['filial']} / {r['departamento']}",
            font_size="0.813rem",
            color="#334155",
        ),
        rx.hstack(
            rx.text(r["item"], font_size="0.813rem", color="#64748b"),
            rx.text(r["qtd_txt"], font_size="0.813rem", font_weight="600", color="#2563eb"),
            spacing="2",
            align="center",
        ),
        justify="between",
        width="100%",
        padding="0.4rem 0",
    )


def _bloco_movimento(tipo: str, itens: list) -> rx.Component:
    """Bloco de ultimos movimentos (entradas ou despachos)."""
    header = "Ultimas Entradas" if tipo == "entrada" else "Ultimos Despachos"
    icone = "package-plus" if tipo == "entrada" else "truck"
    cor = "#059669" if tipo == "entrada" else "#2563eb"
    linha = _linha_entrada if tipo == "entrada" else _linha_despacho

    vazio = rx.text(
        "Nenhum movimento registrado ainda.",
        font_size="0.875rem",
        color="#94a3b8",
        padding="1rem 0",
    )
    corpo = rx.cond(
        itens.length() > 0,
        rx.vstack(rx.foreach(itens, linha), spacing="0", width="100%"),
        vazio,
    )

    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(tag=icone, width="1rem", height="1rem", color=cor),
                width="2.25rem",
                height="2.25rem",
                border_radius="0.625rem",
                background=cor + "15",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.text(header, font_size="0.875rem", font_weight="600", color="#1e293b"),
            spacing="3",
            align="center",
        ),
        rx.divider(margin_y="0.75rem"),
        corpo,
        padding="1.25rem",
        background="white",
        border="1px solid #f1f5f9",
        border_radius="1rem",
        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
        width="100%",
    )


def dashboard() -> rx.Component:
    page = DashboardState
    return rx.box(
        menu_lateral(),
        rx.box(
            toast(),
            rx.container(
                rx.vstack(
                    page_header("Dashboard", "Visao geral do controle de estoque", "layout-dashboard"),
                    # Cards de resumo
                    rx.grid(
                        rx.foreach(
                            [
                                {"titulo": "Items em Cadastro", "campo": "total_itens", "icone": "package", "cor": "#3b82f6"},
                                {"titulo": "Filiais", "campo": "total_filiais", "icone": "building-2", "cor": "#8b5cf6"},
                                {"titulo": "Departamentos", "campo": "total_deptos", "icone": "layers", "cor": "#06b6d4"},
                                {"titulo": "Saldo Tinta (L)", "campo": "saldo_litros", "icone": "droplets", "cor": "#059669"},
                                {"titulo": "Saldo Toner/Cartucho (un)", "campo": "saldo_unidades", "icone": "boxes", "cor": "#f59e0b"},
                            ],
                            lambda c: cartao_stats(
                                c["titulo"],
                                DashboardState.stats[c["campo"]],
                                c["icone"],
                                c["cor"],
                            ),
                        ),
                        columns=rx.breakpoints({"base": "1", "sm": "2", "lg": "5"}),
                        spacing="4",
                        width="100%",
                    ),
                    # Alertas
                    rx.cond(
                        DashboardState.alertas.length() > 0,
                        rx.box(
                            rx.hstack(
                                rx.icon(tag="triangle-alert", width="1.125rem", height="1.125rem", color="#d97706"),
                                rx.text("Alertas de estoque", font_size="0.875rem", font_weight="600", color="#92400e"),
                                spacing="3",
                            ),
                            rx.vstack(
                                rx.foreach(DashboardState.alertas, _card_alerta),
                                spacing="0",
                                width="100%",
                                margin_top="0.75rem",
                            ),
                            padding="1.25rem",
                            background="#fffbeb",
                            border="1px solid #fde68a",
                            border_radius="1rem",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    # Ultimos movimentos
                    rx.grid(
                        _bloco_movimento("despacho", DashboardState.ult_despachos),
                        _bloco_movimento("entrada", DashboardState.ult_entradas),
                        columns=rx.breakpoints({"base": "1", "lg": "2"}),
                        spacing="4",
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