#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para apagar TODOS os dados do banco controle_suprimentos.db
   Mantém o esquema (tabelas), apenas remove todos os registros."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "controle_suprimentos.db")

def limpar_banco():
    if not os.path.exists(DB_PATH):
        print(f"Banco nao encontrado em: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('PRAGMA foreign_keys=OFF')
        cur.execute('DELETE FROM entradas')
        cur.execute('DELETE FROM despachos')
        cur.execute('DELETE FROM itens')
        cur.execute('DELETE FROM filiais')
        cur.execute('DELETE FROM departamentos')
        conn.commit()
        print("Todos os dados das tabelas foram apagados com sucesso.")
        print("Tabelas mantidas (estrutura intacta): filiais, departamentos, itens, entradas, despachos")
    except sqlite3.Error as e:
        print(f"Erro ao limpar banco: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    limpar_banco()