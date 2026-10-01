#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Componente cabecalho padrao das paginas."""

import reflex as rx


def page_header(titulo: str, subtitulo: str, icone: str) -> rx.Component:
    """Cabecalho padrao das paginas."""
    return rx.hstack(
        rx.vstack(
            rx.text(titulo, font_size="1.5rem", font_weight="700", color="#1e293b"),
            rx.text(subtitulo, font_size="0.875rem", color="#64748b", margin_top="0.25rem"),
            spacing="0",
            align="start",
        ),
        rx.icon(tag=icone, width="1.5rem", height="1.5rem", color="#94a3b8"),
        justify="between",
        width="100%",
        margin_bottom="2rem",
    )