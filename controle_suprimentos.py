#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controle de Tinta e Toner - Filiais
Sistema local (Python + SQLite, sem dependencias externas) para registrar
compras de suprimentos, despachos para filiais/departamentos e gerar
relatorios de consumo.

Autor: gerado com Claude
"""

import os
import sqlite3
import csv
import datetime
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_TITLE = "Controle de Tinta e Toner - Filiais"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "controle_suprimentos.db")
LOG_FILE = os.path.join(BASE_DIR, "controle_suprimentos.log")

# ---------------------------------------------------------------------------
# Configuracao de logging estruturado
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("controle_suprimentos")

# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    logger.debug("Conexao aberta com banco: %s", DB_PATH)
    return conn


def init_db():
    """Cria as tabelas do banco se ainda nao existirem."""
    logger.info("Inicializando banco de dados: %s", DB_PATH)
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS filiais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS departamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                tipo TEXT NOT NULL DEFAULT 'Toner',
                estoque_minimo INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS entradas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                item_id INTEGER NOT NULL REFERENCES itens(id),
                quantidade INTEGER NOT NULL,
                fornecedor TEXT,
                valor_unitario REAL,
                observacao TEXT
            );

            CREATE TABLE IF NOT EXISTS despachos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                filial_id INTEGER NOT NULL REFERENCES filiais(id),
                departamento_id INTEGER NOT NULL REFERENCES departamentos(id),
                item_id INTEGER NOT NULL REFERENCES itens(id),
                quantidade INTEGER NOT NULL,
                numero_chamado TEXT,
                recebido_por TEXT,
                observacao TEXT
            );
            """
        )
        conn.commit()
        conn.close()
        logger.info("Banco de dados inicializado com sucesso.")
    except sqlite3.Error as e:
        logger.exception("Erro ao inicializar o banco de dados: %s", e)
        raise


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def hoje():
    return datetime.date.today().strftime("%d/%m/%Y")


def to_iso(data_br):
    """Converte dd/mm/aaaa -> aaaa-mm-dd para ordenacao/filtro correto."""
    try:
        d = datetime.datetime.strptime(data_br.strip(), "%d/%m/%Y")
        return d.strftime("%Y-%m-%d")
    except ValueError:
        logger.debug("Data invalida recebida em to_iso: %r", data_br)
        return None


def fmt_date_display(data_br):
    return data_br


def center_window(win, w, h):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


# ---------------------------------------------------------------------------
# Aba: Cadastros (Filiais / Departamentos / Itens)
# ---------------------------------------------------------------------------

class AbaCadastros(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True)

        self.tab_filiais = CadastroSimples(
            sub, "filiais", ["nome"], ["Nome da filial"], titulo="Filiais"
        )
        self.tab_deptos = CadastroSimples(
            sub, "departamentos", ["nome"], ["Nome do departamento"], titulo="Departamentos"
        )
        self.tab_itens = CadastroItens(sub)

        sub.add(self.tab_filiais, text="Filiais")
        sub.add(self.tab_deptos, text="Departamentos")
        sub.add(self.tab_itens, text="Itens (tinta/toner)")

    def refresh(self):
        self.tab_filiais.refresh()
        self.tab_deptos.refresh()
        self.tab_itens.refresh()


class CadastroSimples(ttk.Frame):
    """Cadastro generico de uma tabela com uma unica coluna 'nome'."""

    def __init__(self, master, tabela, campos, labels, titulo=""):
        super().__init__(master, padding=10)
        self.tabela = tabela

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text=labels[0] + ":").pack(side="left")
        self.entry = ttk.Entry(top, width=40)
        self.entry.pack(side="left", padx=6)
        ttk.Button(top, text="Adicionar", command=self.adicionar).pack(side="left", padx=4)
        ttk.Button(top, text="Excluir selecionado", command=self.excluir).pack(side="left", padx=4)

        self.tree = ttk.Treeview(self, columns=("nome",), show="headings", height=14)
        self.tree.heading("nome", text=labels[0])
        self.tree.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            conn = get_conn()
            for row in conn.execute(f"SELECT id, nome FROM {self.tabela} ORDER BY nome"):
                self.tree.insert("", "end", iid=row[0], values=(row[1],))
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao listar registros da tabela %s: %s", self.tabela, e)

    def adicionar(self):
        nome = self.entry.get().strip()
        if not nome:
            messagebox.showwarning(APP_TITLE, "Digite um nome.")
            return
        conn = get_conn()
        try:
            conn.execute(f"INSERT INTO {self.tabela} (nome) VALUES (?)", (nome,))
            conn.commit()
            logger.info("Registro adicionado em %s: %s", self.tabela, nome)
        except sqlite3.IntegrityError:
            logger.warning("Tentativa de adicionar nome duplicado em %s: %s", self.tabela, nome)
            messagebox.showwarning(APP_TITLE, "Ja existe um registro com esse nome.")
        except sqlite3.Error as e:
            logger.exception("Erro inesperado ao adicionar registro em %s: %s", self.tabela, e)
            messagebox.showerror(APP_TITLE, "Erro ao adicionar registro. Verifique o log para detalhes.")
        finally:
            conn.close()
        self.entry.delete(0, "end")
        self.refresh()

    def excluir(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(APP_TITLE, "Selecione um item na lista.")
            return
        if not messagebox.askyesno(APP_TITLE, "Excluir o registro selecionado?"):
            return
        conn = get_conn()
        try:
            conn.execute(f"DELETE FROM {self.tabela} WHERE id=?", (sel[0],))
            conn.commit()
            logger.info("Registro excluido de %s (id=%s)", self.tabela, sel[0])
        except sqlite3.IntegrityError:
            logger.warning("Exclusao bloqueada por dependencias em %s (id=%s)", self.tabela, sel[0])
            messagebox.showerror(
                APP_TITLE,
                "Nao foi possivel excluir: existem lancamentos (entradas/despachos) usando este registro.",
            )
        except sqlite3.Error as e:
            logger.exception("Erro inesperado ao excluir registro em %s: %s", self.tabela, e)
            messagebox.showerror(APP_TITLE, "Erro ao excluir registro. Verifique o log para detalhes.")
        finally:
            conn.close()
        self.refresh()


class CadastroItens(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(top, text="Item/Modelo:").grid(row=0, column=0, sticky="w")
        self.e_nome = ttk.Entry(top, width=30)
        self.e_nome.grid(row=0, column=1, padx=4)

        ttk.Label(top, text="Tipo:").grid(row=0, column=2, sticky="w")
        self.cb_tipo = ttk.Combobox(top, values=["Toner", "Tinta", "Cartucho", "Outro"], width=12, state="readonly")
        self.cb_tipo.set("Toner")
        self.cb_tipo.grid(row=0, column=3, padx=4)

        ttk.Label(top, text="Estoque minimo:").grid(row=0, column=4, sticky="w")
        self.e_min = ttk.Entry(top, width=8)
        self.e_min.insert(0, "0")
        self.e_min.grid(row=0, column=5, padx=4)

        ttk.Button(top, text="Adicionar", command=self.adicionar).grid(row=0, column=6, padx=6)
        ttk.Button(top, text="Excluir selecionado", command=self.excluir).grid(row=0, column=7, padx=4)

        self.tree = ttk.Treeview(
            self, columns=("nome", "tipo", "minimo"), show="headings", height=14
        )
        self.tree.heading("nome", text="Item/Modelo")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("minimo", text="Estoque minimo")
        self.tree.column("minimo", width=110, anchor="center")
        self.tree.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            conn = get_conn()
            for row in conn.execute(
                "SELECT id, nome, tipo, estoque_minimo FROM itens ORDER BY nome"
            ):
                self.tree.insert("", "end", iid=row[0], values=(row[1], row[2], row[3]))
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao listar itens: %s", e)

    def adicionar(self):
        nome = self.e_nome.get().strip()
        tipo = self.cb_tipo.get().strip() or "Toner"
        try:
            minimo = int(self.e_min.get().strip() or 0)
        except ValueError:
            logger.warning("Estoque minimo invalido informado: %r", self.e_min.get())
            messagebox.showwarning(APP_TITLE, "Estoque minimo deve ser um numero.")
            return
        if not nome:
            messagebox.showwarning(APP_TITLE, "Digite o nome/modelo do item.")
            return
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO itens (nome, tipo, estoque_minimo) VALUES (?, ?, ?)",
                (nome, tipo, minimo),
            )
            conn.commit()
            logger.info("Item cadastrado: nome=%s, tipo=%s, minimo=%d", nome, tipo, minimo)
        except sqlite3.IntegrityError:
            logger.warning("Tentativa de cadastrar item duplicado: %s", nome)
            messagebox.showwarning(APP_TITLE, "Ja existe um item com esse nome.")
        except sqlite3.Error as e:
            logger.exception("Erro inesperado ao cadastrar item: %s", e)
            messagebox.showerror(APP_TITLE, "Erro ao cadastrar item. Verifique o log para detalhes.")
        finally:
            conn.close()
        self.e_nome.delete(0, "end")
        self.e_min.delete(0, "end")
        self.e_min.insert(0, "0")
        self.refresh()

    def excluir(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(APP_TITLE, "Selecione um item na lista.")
            return
        if not messagebox.askyesno(APP_TITLE, "Excluir o item selecionado?"):
            return
        conn = get_conn()
        try:
            conn.execute("DELETE FROM itens WHERE id=?", (sel[0],))
            conn.commit()
            logger.info("Item excluido (id=%s)", sel[0])
        except sqlite3.IntegrityError:
            logger.warning("Exclusao de item bloqueada por dependencias (id=%s)", sel[0])
            messagebox.showerror(
                APP_TITLE,
                "Nao foi possivel excluir: existem lancamentos (entradas/despachos) usando este item.",
            )
        except sqlite3.Error as e:
            logger.exception("Erro inesperado ao excluir item: %s", e)
            messagebox.showerror(APP_TITLE, "Erro ao excluir item. Verifique o log para detalhes.")
        finally:
            conn.close()
        self.refresh()


# ---------------------------------------------------------------------------
# Aba: Entrada de Estoque (compras)
# ---------------------------------------------------------------------------

class AbaEntrada(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app

        form = ttk.LabelFrame(self, text="Registrar entrada de estoque (compra)", padding=10)
        form.pack(fill="x")

        ttk.Label(form, text="Data:").grid(row=0, column=0, sticky="w", pady=3)
        self.e_data = ttk.Entry(form, width=12)
        self.e_data.insert(0, hoje())
        self.e_data.grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Item:").grid(row=0, column=2, sticky="w", pady=3)
        self.cb_item = ttk.Combobox(form, width=28, state="readonly")
        self.cb_item.grid(row=0, column=3, sticky="w", padx=4)

        ttk.Label(form, text="Quantidade:").grid(row=1, column=0, sticky="w", pady=3)
        self.e_qtd = ttk.Entry(form, width=12)
        self.e_qtd.grid(row=1, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Fornecedor:").grid(row=1, column=2, sticky="w", pady=3)
        self.e_forn = ttk.Entry(form, width=28)
        self.e_forn.grid(row=1, column=3, sticky="w", padx=4)

        ttk.Label(form, text="Valor unitario (R$):").grid(row=2, column=0, sticky="w", pady=3)
        self.e_valor = ttk.Entry(form, width=12)
        self.e_valor.grid(row=2, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Observacao:").grid(row=2, column=2, sticky="w", pady=3)
        self.e_obs = ttk.Entry(form, width=28)
        self.e_obs.grid(row=2, column=3, sticky="w", padx=4)

        ttk.Button(form, text="Registrar entrada", command=self.registrar).grid(
            row=3, column=0, columnspan=4, pady=8
        )

        lista = ttk.LabelFrame(self, text="Ultimas entradas", padding=10)
        lista.pack(fill="both", expand=True, pady=(10, 0))

        cols = ("data", "item", "quantidade", "fornecedor", "valor")
        self.tree = ttk.Treeview(lista, columns=cols, show="headings", height=12)
        headers = {
            "data": "Data",
            "item": "Item",
            "quantidade": "Quantidade",
            "fornecedor": "Fornecedor",
            "valor": "Valor unit.",
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
        self.tree.column("quantidade", width=90, anchor="center")
        self.tree.column("valor", width=90, anchor="e")
        self.tree.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        try:
            conn = get_conn()
            itens = conn.execute("SELECT id, nome FROM itens ORDER BY nome").fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao carregar itens para combobox de entrada: %s", e)
            itens = []
        self.item_map = {nome: iid for iid, nome in itens}
        self.cb_item["values"] = list(self.item_map.keys())

        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            conn = get_conn()
            rows = conn.execute(
                """
                SELECT e.data, i.nome, e.quantidade, e.fornecedor, e.valor_unitario
                FROM entradas e JOIN itens i ON i.id = e.item_id
                ORDER BY e.data DESC, e.id DESC LIMIT 200
                """
            ).fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao carregar ultimas entradas: %s", e)
            rows = []
        for r in rows:
            valor = f"{r[4]:.2f}" if r[4] is not None else ""
            self.tree.insert("", "end", values=(r[0], r[1], r[2], r[3] or "", valor))

    def registrar(self):
        data_br = self.e_data.get().strip()
        data_iso = to_iso(data_br)
        if not data_iso:
            logger.warning("Data invalida em entrada: %r", data_br)
            messagebox.showwarning(APP_TITLE, "Data invalida. Use o formato dd/mm/aaaa.")
            return
        item_nome = self.cb_item.get().strip()
        if item_nome not in getattr(self, "item_map", {}):
            messagebox.showwarning(APP_TITLE, "Selecione um item cadastrado.")
            return
        try:
            qtd = int(self.e_qtd.get().strip())
            if qtd <= 0:
                raise ValueError
        except ValueError:
            logger.warning("Quantidade invalida em entrada: %r", self.e_qtd.get())
            messagebox.showwarning(APP_TITLE, "Quantidade deve ser um numero inteiro maior que zero.")
            return
        valor_txt = self.e_valor.get().strip().replace(",", ".")
        valor = None
        if valor_txt:
            try:
                valor = float(valor_txt)
            except ValueError:
                logger.warning("Valor unitario invalido em entrada: %r", valor_txt)
                messagebox.showwarning(APP_TITLE, "Valor unitario invalido.")
                return

        conn = get_conn()
        try:
            conn.execute(
                """
                INSERT INTO entradas (data, item_id, quantidade, fornecedor, valor_unitario, observacao)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data_iso,
                    self.item_map[item_nome],
                    qtd,
                    self.e_forn.get().strip() or None,
                    valor,
                    self.e_obs.get().strip() or None,
                ),
            )
            conn.commit()
            logger.info(
                "Entrada registrada: data=%s, item=%s, qtd=%d, valor=%s",
                data_iso, item_nome, qtd, valor,
            )
        except sqlite3.Error as e:
            logger.exception("Erro inesperado ao registrar entrada: %s", e)
            messagebox.showerror(APP_TITLE, "Erro ao registrar entrada. Verifique o log para detalhes.")
            conn.close()
            return
        conn.close()

        self.e_qtd.delete(0, "end")
        self.e_forn.delete(0, "end")
        self.e_valor.delete(0, "end")
        self.e_obs.delete(0, "end")
        self.e_data.delete(0, "end")
        self.e_data.insert(0, hoje())

        self.refresh()
        self.app.refresh_all(except_widget=self)
        messagebox.showinfo(APP_TITLE, "Entrada registrada com sucesso.")


# ---------------------------------------------------------------------------
# Aba: Despacho para filial
# ---------------------------------------------------------------------------

class AbaDespacho(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app

        form = ttk.LabelFrame(self, text="Registrar despacho para filial", padding=10)
        form.pack(fill="x")

        ttk.Label(form, text="Data:").grid(row=0, column=0, sticky="w", pady=3)
        self.e_data = ttk.Entry(form, width=12)
        self.e_data.insert(0, hoje())
        self.e_data.grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Filial:").grid(row=0, column=2, sticky="w", pady=3)
        self.cb_filial = ttk.Combobox(form, width=24, state="readonly")
        self.cb_filial.grid(row=0, column=3, sticky="w", padx=4)

        ttk.Label(form, text="Departamento (da filial):").grid(row=1, column=0, sticky="w", pady=3)
        self.cb_depto = ttk.Combobox(form, width=24, state="readonly")
        self.cb_depto.grid(row=1, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Item:").grid(row=1, column=2, sticky="w", pady=3)
        self.cb_item = ttk.Combobox(form, width=24, state="readonly")
        self.cb_item.grid(row=1, column=3, sticky="w", padx=4)

        ttk.Label(form, text="Quantidade:").grid(row=2, column=0, sticky="w", pady=3)
        self.e_qtd = ttk.Entry(form, width=12)
        self.e_qtd.grid(row=2, column=1, sticky="w", padx=4)

        ttk.Label(form, text="No do chamado:").grid(row=2, column=2, sticky="w", pady=3)
        self.e_chamado = ttk.Entry(form, width=24)
        self.e_chamado.grid(row=2, column=3, sticky="w", padx=4)

        ttk.Label(form, text="Recebido por:").grid(row=3, column=0, sticky="w", pady=3)
        self.e_recebedor = ttk.Entry(form, width=24)
        self.e_recebedor.grid(row=3, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Observacao:").grid(row=3, column=2, sticky="w", pady=3)
        self.e_obs = ttk.Entry(form, width=24)
        self.e_obs.grid(row=3, column=3, sticky="w", padx=4)

        self.lbl_saldo = ttk.Label(form, text="", foreground="#b45309")
        self.lbl_saldo.grid(row=4, column=0, columnspan=4, sticky="w", pady=(4, 0))
        self.cb_item.bind("<<ComboboxSelected>>", lambda e: self.mostrar_saldo())

        ttk.Button(form, text="Registrar despacho", command=self.registrar).grid(
            row=5, column=0, columnspan=4, pady=8
        )

        lista = ttk.LabelFrame(self, text="Ultimos despachos", padding=10)
        lista.pack(fill="both", expand=True, pady=(10, 0))

        cols = ("data", "filial", "departamento", "item", "quantidade", "chamado", "recebedor")
        self.tree = ttk.Treeview(lista, columns=cols, show="headings", height=12)
        headers = {
            "data": "Data",
            "filial": "Filial",
            "departamento": "Departamento",
            "item": "Item",
            "quantidade": "Qtd",
            "chamado": "No Chamado",
            "recebedor": "Recebido por",
        }
        widths = {
            "data": 80, "filial": 130, "departamento": 130, "item": 150,
            "quantidade": 50, "chamado": 100, "recebedor": 120,
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="center" if c == "quantidade" else "w")
        self.tree.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        try:
            conn = get_conn()
            filiais = conn.execute("SELECT id, nome FROM filiais ORDER BY nome").fetchall()
            deptos = conn.execute("SELECT id, nome FROM departamentos ORDER BY nome").fetchall()
            itens = conn.execute("SELECT id, nome FROM itens ORDER BY nome").fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao carregar dados para combobox de despacho: %s", e)
            filiais, deptos, itens = [], [], []

        self.filial_map = {nome: iid for iid, nome in filiais}
        self.depto_map = {nome: iid for iid, nome in deptos}
        self.item_map = {nome: iid for iid, nome in itens}

        self.cb_filial["values"] = list(self.filial_map.keys())
        self.cb_depto["values"] = list(self.depto_map.keys())
        self.cb_item["values"] = list(self.item_map.keys())

        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            conn = get_conn()
            rows = conn.execute(
                """
                SELECT d.data, f.nome, dp.nome, i.nome, d.quantidade, d.numero_chamado, d.recebido_por
                FROM despachos d
                JOIN filiais f ON f.id = d.filial_id
                JOIN departamentos dp ON dp.id = d.departamento_id
                JOIN itens i ON i.id = d.item_id
                ORDER BY d.data DESC, d.id DESC LIMIT 200
                """
            ).fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao carregar ultimos despachos: %s", e)
            rows = []
        for r in rows:
            self.tree.insert("", "end", values=r)

    def saldo_atual(self, item_id):
        try:
            conn = get_conn()
            entradas = conn.execute(
                "SELECT COALESCE(SUM(quantidade),0) FROM entradas WHERE item_id=?", (item_id,)
            ).fetchone()[0]
            saidas = conn.execute(
                "SELECT COALESCE(SUM(quantidade),0) FROM despachos WHERE item_id=?", (item_id,)
            ).fetchone()[0]
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao calcular saldo do item %s: %s", item_id, e)
            return 0
        return entradas - saidas

    def mostrar_saldo(self):
        nome = self.cb_item.get().strip()
        if nome in getattr(self, "item_map", {}):
            saldo = self.saldo_atual(self.item_map[nome])
            self.lbl_saldo.config(text=f"Saldo atual em estoque para '{nome}': {saldo} unidade(s)")
        else:
            self.lbl_saldo.config(text="")

    def registrar(self):
        data_iso = to_iso(self.e_data.get().strip())
        if not data_iso:
            logger.warning("Data invalida em despacho: %r", self.e_data.get())
            messagebox.showwarning(APP_TITLE, "Data invalida. Use o formato dd/mm/aaaa.")
            return
        filial_nome = self.cb_filial.get().strip()
        depto_nome = self.cb_depto.get().strip()
        item_nome = self.cb_item.get().strip()
        if filial_nome not in getattr(self, "filial_map", {}):
            messagebox.showwarning(APP_TITLE, "Selecione a filial.")
            return
        if depto_nome not in getattr(self, "depto_map", {}):
            messagebox.showwarning(APP_TITLE, "Selecione o departamento.")
            return
        if item_nome not in getattr(self, "item_map", {}):
            messagebox.showwarning(APP_TITLE, "Selecione o item.")
            return
        try:
            qtd = int(self.e_qtd.get().strip())
            if qtd <= 0:
                raise ValueError
        except ValueError:
            logger.warning("Quantidade invalida em despacho: %r", self.e_qtd.get())
            messagebox.showwarning(APP_TITLE, "Quantidade deve ser um numero inteiro maior que zero.")
            return

        item_id = self.item_map[item_nome]
        saldo = self.saldo_atual(item_id)
        if qtd > saldo:
            if not messagebox.askyesno(
                APP_TITLE,
                f"Atencao: o saldo em estoque de '{item_nome}' e {saldo}, "
                f"e voce esta despachando {qtd}. O estoque vai ficar negativo.\n\n"
                "Deseja continuar mesmo assim?",
            ):
                return

        conn = get_conn()
        try:
            conn.execute(
                """
                INSERT INTO despachos
                    (data, filial_id, departamento_id, item_id, quantidade,
                     numero_chamado, recebido_por, observacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data_iso,
                    self.filial_map[filial_nome],
                    self.depto_map[depto_nome],
                    item_id,
                    qtd,
                    self.e_chamado.get().strip() or None,
                    self.e_recebedor.get().strip() or None,
                    self.e_obs.get().strip() or None,
                ),
            )
            conn.commit()
            logger.info(
                "Despacho registrado: data=%s, filial=%s, depto=%s, item=%s, qtd=%d",
                data_iso, filial_nome, depto_nome, item_nome, qtd,
            )
        except sqlite3.Error as e:
            logger.exception("Erro inesperado ao registrar despacho: %s", e)
            messagebox.showerror(APP_TITLE, "Erro ao registrar despacho. Verifique o log para detalhes.")
            conn.close()
            return
        conn.close()

        self.e_qtd.delete(0, "end")
        self.e_chamado.delete(0, "end")
        self.e_recebedor.delete(0, "end")
        self.e_obs.delete(0, "end")
        self.e_data.delete(0, "end")
        self.e_data.insert(0, hoje())
        self.lbl_saldo.config(text="")

        self.refresh()
        self.app.refresh_all(except_widget=self)
        messagebox.showinfo(APP_TITLE, "Despacho registrado com sucesso.")


# ---------------------------------------------------------------------------
# Aba: Estoque atual
# ---------------------------------------------------------------------------

class AbaEstoque(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="Atualizar", command=self.refresh).pack(side="left")
        ttk.Label(top, text="   Linhas em vermelho: abaixo do estoque minimo cadastrado.").pack(side="left")

        cols = ("item", "tipo", "entradas", "saidas", "saldo", "minimo")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        headers = {
            "item": "Item/Modelo", "tipo": "Tipo", "entradas": "Total comprado",
            "saidas": "Total despachado", "saldo": "Saldo atual", "minimo": "Estoque minimo",
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
        for c in ("entradas", "saidas", "saldo", "minimo"):
            self.tree.column(c, width=110, anchor="center")
        self.tree.tag_configure("baixo", background="#fde2e1")
        self.tree.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            conn = get_conn()
            rows = conn.execute(
                """
                SELECT i.nome, i.tipo, i.estoque_minimo,
                       COALESCE((SELECT SUM(quantidade) FROM entradas WHERE item_id=i.id), 0) AS ent,
                       COALESCE((SELECT SUM(quantidade) FROM despachos WHERE item_id=i.id), 0) AS sai
                FROM itens i
                ORDER BY i.nome
                """
            ).fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao carregar estoque atual: %s", e)
            rows = []
        for nome, tipo, minimo, ent, sai in rows:
            saldo = ent - sai
            tag = "baixo" if saldo <= minimo else ""
            self.tree.insert(
                "", "end", values=(nome, tipo, ent, sai, saldo, minimo), tags=(tag,) if tag else ()
            )


# ---------------------------------------------------------------------------
# Aba: Relatorios
# ---------------------------------------------------------------------------

class AbaRelatorios(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app

        filtro = ttk.LabelFrame(self, text="Filtros do relatorio de despachos", padding=10)
        filtro.pack(fill="x")

        ttk.Label(filtro, text="De (dd/mm/aaaa):").grid(row=0, column=0, sticky="w")
        self.e_de = ttk.Entry(filtro, width=12)
        self.e_de.grid(row=0, column=1, padx=4)

        ttk.Label(filtro, text="Ate (dd/mm/aaaa):").grid(row=0, column=2, sticky="w")
        self.e_ate = ttk.Entry(filtro, width=12)
        self.e_ate.grid(row=0, column=3, padx=4)

        ttk.Label(filtro, text="Filial:").grid(row=0, column=4, sticky="w")
        self.cb_filial = ttk.Combobox(filtro, width=20, state="readonly")
        self.cb_filial.grid(row=0, column=5, padx=4)

        ttk.Label(filtro, text="Departamento:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.cb_depto = ttk.Combobox(filtro, width=20, state="readonly")
        self.cb_depto.grid(row=1, column=1, padx=4, pady=(6, 0))

        ttk.Label(filtro, text="Item:").grid(row=1, column=2, sticky="w", pady=(6, 0))
        self.cb_item = ttk.Combobox(filtro, width=20, state="readonly")
        self.cb_item.grid(row=1, column=3, padx=4, pady=(6, 0))

        ttk.Button(filtro, text="Gerar relatorio", command=self.gerar).grid(row=1, column=4, padx=4, pady=(6, 0))
        ttk.Button(filtro, text="Limpar filtros", command=self.limpar).grid(row=1, column=5, padx=4, pady=(6, 0))
        ttk.Button(filtro, text="Exportar para CSV", command=self.exportar_csv).grid(row=1, column=6, padx=4, pady=(6, 0))

        resumo = ttk.Frame(self)
        resumo.pack(fill="x", pady=(10, 0))
        self.lbl_resumo = ttk.Label(resumo, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_resumo.pack(anchor="w")

        cols = ("data", "filial", "departamento", "item", "quantidade", "chamado", "recebedor")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=16)
        headers = {
            "data": "Data", "filial": "Filial", "departamento": "Departamento", "item": "Item",
            "quantidade": "Qtd", "chamado": "No Chamado", "recebedor": "Recebido por",
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
        self.tree.column("quantidade", width=60, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=(8, 0))

        # Sub-relatorio: totais agrupados por filial e departamento
        agr = ttk.LabelFrame(self, text="Total despachado por filial / departamento (no periodo filtrado)", padding=8)
        agr.pack(fill="both", expand=True, pady=(10, 0))
        self.tree_agr = ttk.Treeview(agr, columns=("filial", "departamento", "total"), show="headings", height=8)
        self.tree_agr.heading("filial", text="Filial")
        self.tree_agr.heading("departamento", text="Departamento")
        self.tree_agr.heading("total", text="Total de itens despachados")
        self.tree_agr.column("total", width=160, anchor="center")
        self.tree_agr.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        try:
            conn = get_conn()
            filiais = ["(Todas)"] + [r[0] for r in conn.execute("SELECT nome FROM filiais ORDER BY nome")]
            deptos = ["(Todos)"] + [r[0] for r in conn.execute("SELECT nome FROM departamentos ORDER BY nome")]
            itens = ["(Todos)"] + [r[0] for r in conn.execute("SELECT nome FROM itens ORDER BY nome")]
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao carregar filtros de relatorio: %s", e)
            filiais, deptos, itens = ["(Todas)"], ["(Todos)"], ["(Todos)"]
        self.cb_filial["values"] = filiais
        self.cb_depto["values"] = deptos
        self.cb_item["values"] = itens
        if not self.cb_filial.get():
            self.cb_filial.set("(Todas)")
        if not self.cb_depto.get():
            self.cb_depto.set("(Todos)")
        if not self.cb_item.get():
            self.cb_item.set("(Todos)")
        self.gerar()

    def limpar(self):
        self.e_de.delete(0, "end")
        self.e_ate.delete(0, "end")
        self.cb_filial.set("(Todas)")
        self.cb_depto.set("(Todos)")
        self.cb_item.set("(Todos)")
        self.gerar()

    def _query(self):
        sql = """
            SELECT d.data, f.nome, dp.nome, i.nome, d.quantidade, d.numero_chamado, d.recebido_por
            FROM despachos d
            JOIN filiais f ON f.id = d.filial_id
            JOIN departamentos dp ON dp.id = d.departamento_id
            JOIN itens i ON i.id = d.item_id
            WHERE 1=1
        """
        params = []

        de = self.e_de.get().strip()
        if de:
            de_iso = to_iso(de)
            if not de_iso:
                logger.warning("Data 'De' invalida em relatorio: %r", de)
                messagebox.showwarning(APP_TITLE, "Data 'De' invalida.")
                return None
            sql += " AND d.data >= ?"
            params.append(de_iso)

        ate = self.e_ate.get().strip()
        if ate:
            ate_iso = to_iso(ate)
            if not ate_iso:
                logger.warning("Data 'Ate' invalida em relatorio: %r", ate)
                messagebox.showwarning(APP_TITLE, "Data 'Ate' invalida.")
                return None
            sql += " AND d.data <= ?"
            params.append(ate_iso)

        filial = self.cb_filial.get().strip()
        if filial and filial != "(Todas)":
            sql += " AND f.nome = ?"
            params.append(filial)

        depto = self.cb_depto.get().strip()
        if depto and depto != "(Todos)":
            sql += " AND dp.nome = ?"
            params.append(depto)

        item = self.cb_item.get().strip()
        if item and item != "(Todos)":
            sql += " AND i.nome = ?"
            params.append(item)

        sql += " ORDER BY d.data DESC, d.id DESC"

        try:
            conn = get_conn()
            rows = conn.execute(sql, params).fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.exception("Erro ao executar query de relatorio: %s", e)
            messagebox.showerror(APP_TITLE, "Erro ao gerar relatorio. Verifique o log para detalhes.")
            return None
        return rows

    def gerar(self):
        rows = self._query()
        if rows is None:
            return

        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", "end", values=r)

        total_qtd = sum(r[4] for r in rows)
        self.lbl_resumo.config(
            text=f"{len(rows)} despacho(s) encontrado(s)  |  Total de unidades despachadas: {total_qtd}"
        )

        agregados = {}
        for r in rows:
            chave = (r[1], r[2])
            agregados[chave] = agregados.get(chave, 0) + r[4]

        for i in self.tree_agr.get_children():
            self.tree_agr.delete(i)
        for (filial, depto), total in sorted(agregados.items(), key=lambda x: -x[1]):
            self.tree_agr.insert("", "end", values=(filial, depto, total))

    def exportar_csv(self):
        rows = self._query()
        if rows is None:
            return
        if not rows:
            messagebox.showinfo(APP_TITLE, "Nao ha dados para exportar com os filtros atuais.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv")],
            initialfile="relatorio_despachos.csv",
            title="Salvar relatorio como",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Data", "Filial", "Departamento", "Item", "Quantidade", "No Chamado", "Recebido por"])
                for r in rows:
                    w.writerow(r)
            logger.info("Relatorio exportado para CSV: %s (%d registros)", path, len(rows))
        except OSError as e:
            logger.exception("Erro ao exportar relatorio para CSV: %s", e)
            messagebox.showerror(APP_TITLE, "Erro ao salvar arquivo CSV. Verifique o log para detalhes.")
            return
        messagebox.showinfo(APP_TITLE, f"Relatorio exportado para:\n{path}")


# ---------------------------------------------------------------------------
# Aplicacao principal
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        center_window(self, 1080, 720)
        self.minsize(900, 600)

        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError as e:
            logger.debug("Tema 'vista' indisponivel, usando padrao: %s", e)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.aba_despacho = AbaDespacho(nb, self)
        self.aba_entrada = AbaEntrada(nb, self)
        self.aba_estoque = AbaEstoque(nb, self)
        self.aba_relatorios = AbaRelatorios(nb, self)
        self.aba_cadastros = AbaCadastros(nb, self)

        nb.add(self.aba_despacho, text="  Despachar para filial  ")
        nb.add(self.aba_entrada, text="  Entrada de estoque  ")
        nb.add(self.aba_estoque, text="  Estoque atual  ")
        nb.add(self.aba_relatorios, text="  Relatorios  ")
        nb.add(self.aba_cadastros, text="  Cadastros  ")

    def refresh_all(self, except_widget=None):
        for widget in (self.aba_despacho, self.aba_entrada, self.aba_estoque, self.aba_relatorios, self.aba_cadastros):
            if widget is except_widget:
                continue
            widget.refresh()


def main():
    logger.info("Iniciando aplicacao Controle de Tinta e Toner - Filiais")
    try:
        init_db()
    except Exception as e:
        logger.exception("Falha ao inicializar banco de dados, abortando: %s", e)
        return
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        logger.exception("Erro critico na aplicacao: %s", e)
        raise


if __name__ == "__main__":
    main()
