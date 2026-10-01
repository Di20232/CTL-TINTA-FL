#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Componente menu lateral (sidebar fixa) — definicao das rotas incluida."""

import reflex as rx

from app_reflex.componentes.estilos import BORDA
from app_reflex.componentes.rotas import PAGINAS


def menu_lateral() -> rx.Component:
    """Sidebar fixa com links das paginas."""
    return rx.el.aside(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(tag="droplets", width="1.25rem", height="1.25rem", color="white"),
                    width="2.25rem",
                    height="2.25rem",
                    border_radius="0.75rem",
                    background="linear-gradient(135deg, #3b82f6, #2563eb)",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                # Titulo/descricao: escondidos em telas muito pequenas (xs)
                rx.vstack(
                    rx.text("Controle de Tinta", font_size="0.875rem", font_weight="700", color="#1e293b", spacing="0"),
                    rx.text("Filiais", font_size="0.688rem", color="#94a3b8", font_weight="500"),
                    spacing="0",
                    display=rx.breakpoints({"base": "none", "sm": "flex"}),
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
            rx.vstack(
                *[
                    rx.link(
                        rx.hstack(
                            rx.icon(tag=icone, width="18px", height="18px"),
                            rx.text(
                                nome,
                                font_size="0.875rem",
                                font_weight="500",
                                display=rx.breakpoints({"base": "none", "sm": "inline"}),
                            ),
                            spacing="3",
                            justify="center",
                            width="100%",
                        ),
                        href=rota,
                        width="100%",
                        padding="0.625rem 0.75rem",
                        border_radius="0.5rem",
                        color="#475569",
                        transition="all 0.15s ease",
                        _hover={
                            "background": "rgba(59, 130, 246, 0.08)",
                            "color": "#2563eb",
                        },
                        class_name="sidebar-link",
                    )
                    for rota, nome, icone in PAGINAS
                ],
                width="100%",
                padding="1rem 0.75rem",
                spacing="1",
                flex="1",
            ),
            rx.box(
                rx.text(
                    " CTL-TINTA-FL v2.0",
                    font_size="0.688rem",
                    color="#94a3b8",
                    display=rx.breakpoints({"base": "none", "sm": "inline"}),
                ),
                width="100%",
                padding="1rem 1.5rem",
                border_top=f"1px solid {BORDA}",
            ),
            spacing="0",
            width="100%",
            height="100vh",
            display="flex",
        ),
        position="fixed",
        left="0",
        top="0",
        height="100vh",
        # Em telas >=sm (>=48rem) a sidebar tem 16rem; abaixo fica estreita (icons only)
        width=rx.breakpoints({"base": "4rem", "sm": "16rem"}),
        background="white",
        border_right=f"1px solid {BORDA}",
        z_index="40",
    )