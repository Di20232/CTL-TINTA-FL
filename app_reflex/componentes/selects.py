#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Componente select reativo — gera opcoes a partir de Var de lista de dicts."""

import reflex as rx


def select_de_lista(
    itens: list,
    name: str,
    campo_valor: str = "id",
    campo_label: str = "nome",
    placeholder: str = "Selecione",
    **props,
) -> rx.Component:
    """Select cujas opcoes vem de um Var de lista de dicts.

    Cada item deve conter 'id' (valor) e 'nome' (rotulo).
    """
    # Estilo CSS para o trigger (botão do select)
    trigger_style = {
        "background": "white",
        "color": "#1e293b",
        "border": "1px solid #e2e8f0",
        "width": "100%",
        "&[data-placeholder]": {
            "color": "#94a3b8",  # Cor do placeholder quando nada selecionado
        },
    }

    return rx.select.root(
        rx.select.trigger(
            placeholder=placeholder,
            width="100%",
            css=trigger_style,
        ),
        rx.select.content(
            rx.select.group(
                rx.foreach(
                    itens,
                    lambda i: rx.select.item(
                        i[campo_label], value=i[campo_valor]
                    ),
                ),
            ),
        ),
        name=name,
        width="100%",
        **props,
    )