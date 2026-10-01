"""Controle de Tinta e Toner - Filiais.

App Reflex: front-end web local, substituindo o antigo servidor Flask.
Reutiliza a camada de dados db.py (intocada) e o banco SQLite existente.
"""

import reflex as rx

import db

from app_reflex.paginas import (
    cadastros, dashboard, despacho, entrada, estoque, relatorios,
)


def index() -> rx.Component:
    return dashboard.dashboard()


# Garante que as tabelas existam (idempotente; banco ja pode existir)
db.init_db()


app = rx.App()

app.add_page(index, route="/", title="Dashboard - Controle de Tinta")
app.add_page(entrada.entrada, route="/entrada", title="Entrada de Estoque")
app.add_page(despacho.despacho, route="/despacho", title="Despachar")
app.add_page(estoque.estoque, route="/estoque", title="Estoque Atual")
app.add_page(relatorios.relatorios, route="/relatorios", title="Relatorios")
app.add_page(cadastros.cadastros, route="/cadastros", title="Cadastros")