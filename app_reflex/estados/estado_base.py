#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado base: feedback de toast reutilizado por todas as paginas."""

import reflex as rx


class EstadoBase(rx.State):
    """Base comum: feedback toast + helpers de carregamento."""

    msg: str = ""
    tipo_msg: str = ""  # success | error | warning | info

    def notificar(self, texto: str, tipo: str = "success"):
        """Define a mensagem do toast."""
        self.msg = texto
        self.tipo_msg = tipo

    def limpar_msg(self):
        self.msg = ""
        self.tipo_msg = ""