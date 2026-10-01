#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Componentes badge: tipo de item e quantidade de despacho."""

import reflex as rx


def badge_tipo(tipo: str) -> rx.Component:
    """Badge colorido conforme o tipo do item."""
    estilos = {
        "Toner": ("#eff6ff", "#1d4ed8", "#bfdbfe"),
        "Tinta": ("#faf5ff", "#6d28d9", "#e9d5ff"),
        "Cartucho": ("#fffbeb", "#b45309", "#fde68a"),
    }
    fundo, texto, borda = estilos.get(tipo, ("#f8fafc", "#334155", "#e2e8f0"))
    return rx.badge(
        tipo,
        variant="soft",
        font_size="0.75rem",
        font_weight="600",
        padding="0.25rem 0.6rem",
        border_radius="9999px",
        background=fundo,
        color=texto,
        border=f"1px solid {borda}",
    )


def badge_qtd(qtd) -> rx.Component:
    """Quantum badge vermelho usado nas tabelas de despacho."""
    return rx.box(
        rx.text(str(qtd), font_size="0.75rem", font_weight="700"),
        display="inline-flex",
        align_items="center",
        justify_content="center",
        background="#fef2f2",
        color="#b91c1c",
        border_radius="0.5rem",
        padding="0.125rem 0.5rem",
        min_width="2rem",
    )