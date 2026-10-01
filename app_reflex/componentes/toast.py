#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Componente toast: feedback flutuante reativo a EstadoBase.msg / tipo_msg."""

import reflex as rx

from app_reflex.estados.estado_base import EstadoBase


def toast() -> rx.Component:
    """Toast flutuante que reage a EstadoBase.msg / tipo_msg."""
    # CSS deve usar cores hex reais — nunca o nome de classe Tailwind (ex: "bg-red-50")
    # como valor de background/border, porque vira CSS invalido e o toast fica invisivel.
    estilos = {
        "success": ("#ecfdf5", "#065f46", "#a7f3d0", "check-circle", "#10b981"),
        "error": ("#fef2f2", "#991b1b", "#fecaca", "alert-circle", "#ef4444"),
        "warning": ("#fffbeb", "#92400e", "#fde68a", "triangle-alert", "#f59e0b"),
        "info": ("#eff6ff", "#1e40af", "#bfdbfe", "info", "#3b82f6"),
    }
    fundo, texto, borda, icone, cor_icone = estilos.get(
        EstadoBase.tipo_msg, estilos["info"]
    )

    return rx.cond(
        EstadoBase.msg != "",
        rx.box(
            rx.hstack(
                rx.icon(tag=icone, width="1rem", height="1rem", color=cor_icone),
                rx.text(EstadoBase.msg, font_size="0.875rem", font_weight="500"),
                rx.button(
                    rx.icon(tag="x", width="1rem", height="1rem", color="currentColor"),
                    on_click=EstadoBase.limpar_msg,
                    type="button",
                    variant="ghost",
                    padding="0.25rem",
                    color_scheme="gray",
                    _hover={"background": "transparent"},
                ),
                spacing="3",
                align="center",
            ),
            padding="0.75rem 1rem",
            border_radius="0.75rem",
            background=fundo,
            color=texto,
            border=f"1px solid {borda}",
            box_shadow="0 10px 30px rgba(0,0,0,0.10)",
            z_index="100",
            on_click=EstadoBase.limpar_msg,
        ),
        rx.fragment(),
    )