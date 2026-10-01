#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helpers de conversao de Row sqlite3 -> dict simples."""


def _row_to_dict(row):
    """Converte um sqlite3.Row (ou dict) em dict simples."""
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    return {k: row[k] for k in row.keys()}


def _rows_to_dicts(rows):
    """Converte uma lista de sqlite3.Row em lista de dicts."""
    return [_row_to_dict(r) for r in rows]