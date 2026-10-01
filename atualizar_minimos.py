#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para atualizar estoque_minimo dos itens existentes baseado no tipo."""

import db

def atualizar_minimos():
    """Atualiza estoque_minimo: Tinta = 1L, Toner/Cartucho = 5un."""
    conn = db.get_conn()
    try:
        # Atualiza itens do tipo Tinta para 1L
        conn.execute(
            "UPDATE itens SET estoque_minimo = 1 WHERE LOWER(tipo) = 'tinta' AND estoque_minimo = 0"
        )
        tinta_count = conn.execute("SELECT changes()").fetchone()[0]

        # Atualiza itens do tipo Toner para 5un
        conn.execute(
            "UPDATE itens SET estoque_minimo = 5 WHERE LOWER(tipo) = 'toner' AND estoque_minimo = 0"
        )
        toner_count = conn.execute("SELECT changes()").fetchone()[0]

        # Atualiza itens do tipo Cartucho para 5un
        conn.execute(
            "UPDATE itens SET estoque_minimo = 5 WHERE LOWER(tipo) = 'cartucho' AND estoque_minimo = 0"
        )
        cartucho_count = conn.execute("SELECT changes()").fetchone()[0]

        conn.commit()

        print(f"Atualizado com sucesso:")
        print(f"  - Tinta: {tinta_count} itens -> estoque_minimo = 1L")
        print(f"  - Toner: {toner_count} itens -> estoque_minimo = 5un")
        print(f"  - Cartucho: {cartucho_count} itens -> estoque_minimo = 5un")
        print(f"  Total: {tinta_count + toner_count + cartucho_count} itens atualizados")

        # Mostra resultado final
        print("\nItens atuais:")
        itens = conn.execute(
            "SELECT nome, tipo, estoque_minimo FROM itens ORDER BY tipo, nome"
        ).fetchall()
        for nome, tipo, minimo in itens:
            print(f"  {tipo:10s} | {nome:30s} | min = {minimo}")

    except Exception as e:
        conn.rollback()
        print(f"Erro ao atualizar: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    atualizar_minimos()
