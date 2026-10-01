#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Componente cartao de estatistica (dashboard)."""

import reflex as rx


def cartao_stats(titulo: str, valor, icone: str, cor: str, alerta=False) -> rx.Component:
    """Card de resumo com icone colorido."""
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(tag=icone, width="1.25rem", height="1.25rem", color="white"),
                width="2.75rem",
                height="2.75rem",
                border_radius="0.75rem",
                background=cor,
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.text(titulo, font_size="0.75rem", color="#64748b", font_weight="500"),
                rx.text(valor, font_size="1.5rem", font_weight="700", color="#1e293b"),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
        ),
        padding="1.25rem",
        background="white",
        border="1px solid #f1f5f9",
        border_radius="1rem",
        box_shadow="0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
        class_name="card",
        flex="1",
        min_width="200px",
    )