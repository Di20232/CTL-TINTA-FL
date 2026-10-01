"""Pacote de componentes compartilhados — um arquivo por funcao."""

from app_reflex.componentes.estilos import AZUL, AZUL_HOVER, BORDA, CINZA_FUNDO
from app_reflex.componentes.toast import toast
from app_reflex.componentes.menu_lateral import menu_lateral
from app_reflex.componentes.cartoes import cartao_stats
from app_reflex.componentes.badges import badge_tipo, badge_qtd
from app_reflex.componentes.pg_header import page_header
from app_reflex.componentes.selects import select_de_lista
from app_reflex.componentes.rotas import PAGINAS

__all__ = [
    "AZUL", "AZUL_HOVER", "BORDA", "CINZA_FUNDO",
    "toast", "menu_lateral", "cartao_stats", "badge_tipo",
    "badge_qtd", "page_header", "select_de_lista",
    "PAGINAS",
]