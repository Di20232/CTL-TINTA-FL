#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado da pagina de Cadastros (CRUD de filiais, departamentos, itens)."""

import logging

import reflex as rx

import db

from app_reflex.estados._helpers import _rows_to_dicts
from app_reflex.estados.estado_base import EstadoBase
from app_reflex.util_unidade import unidade_do_tipo, numero_br

logger = logging.getLogger(__name__)


class CadastrosState(EstadoBase):
    """Estado da pagina de cadastros."""

    filiais: list[dict] = []
    deptos: list[dict] = []
    itens: list[dict] = []

    # Form de item
    item_nome: str = ""
    item_tipo: str = "Toner"
    item_minimo: str = "0"

    # Form simples (filial/depto)
    registros: list[dict] = []

    # Dialogo de exclusao com cascata
    # confirm_*: popula o dialogo (titulo, texto, dados)
    # _pending_payload: dict imutavel guardado ANTES de o dialogo fechar;
    #   o handler de exclusao le de la em vez de ler confirm_*,
    #   evitando race-condition com on_open_change.
    confirm_open: bool = False
    confirm_tabela: str = ""
    confirm_id: int = 0
    confirm_nome: str = ""
    confirm_total: int = 0  # quantidade de lançamentos vinculados a remover
    confirm_rotulo: str = ""  # "despacho(s)" / "entrada(s)"
    _pending_payload: dict = {}  # snapshot salvo antes de fechar o dialogo

    @rx.event
    def carregar(self):
        self._recarregar()

    def _recarregar(self):
        try:
            self.filiais = _rows_to_dicts(db.listar("filiais"))
            self.deptos = _rows_to_dicts(db.listar("departamentos"))
            self.itens = _rows_to_dicts(db.listar_itens())
            for i in self.itens:
                unid = unidade_do_tipo(i["tipo"])
                i["min_txt"] = f"{numero_br(i['estoque_minimo'])} {unid}"
                i["unidade"] = unid
        except Exception:
            logger.exception("Falha ao recarregar listas de cadastros")
            self.notificar("Erro ao carregar os cadastros.", "error")

    # ---------------- Filiais ----------------
    @rx.event
    def adicionar_filial(self, form_data: dict):
        nome = (form_data.get("nome") or "").strip()
        if not nome:
            logger.debug("adicionar_filial: nome vazio, operacao cancelada")
            self.notificar("Digite um nome para a filial.", "error")
            return
        try:
            inserido = db.inserir("filiais", nome)
        except Exception:
            logger.exception("Erro inesperado ao inserir filial '%s'", nome)
            self.notificar("Erro ao salvar a filial.", "error")
            return
        if inserido:
            logger.info("Filial '%s' adicionada", nome)
            self.notificar(f"Filial '{nome}' adicionada com sucesso!", "success")
        else:
            logger.info("Filial '%s' nao inserida (nome duplicado)", nome)
            self.notificar(f"Ja existe uma filial com o nome '{nome}'.", "error")
        self._recarregar()

    # ---------------- Departamentos ----------------
    @rx.event
    def adicionar_depto(self, form_data: dict):
        nome = (form_data.get("nome") or "").strip()
        if not nome:
            logger.debug("adicionar_depto: nome vazio, operacao cancelada")
            self.notificar("Digite um nome para o departamento.", "error")
            return
        try:
            inserido = db.inserir("departamentos", nome)
        except Exception:
            logger.exception("Erro inesperado ao inserir departamento '%s'", nome)
            self.notificar("Erro ao salvar o departamento.", "error")
            return
        if inserido:
            logger.info("Departamento '%s' adicionado", nome)
            self.notificar(f"Departamento '{nome}' adicionado com sucesso!", "success")
        else:
            logger.info("Departamento '%s' nao inserido (nome duplicado)", nome)
            self.notificar(f"Ja existe um departamento com o nome '{nome}'.", "error")
        self._recarregar()

    # ---------------- Itens ----------------
    @rx.event
    def adicionar_item(self, form_data: dict):
        nome = (form_data.get("nome") or "").strip()
        tipo = (form_data.get("tipo") or "").strip() or "Toner"
        minimo_str = (form_data.get("estoque_minimo") or "").strip()

        # Define estoque mínimo padrão baseado no tipo se não especificado
        if not minimo_str:
            if tipo.lower() == "tinta":
                minimo = 1  # 1 litro para tinta
            else:  # Toner ou Cartucho
                minimo = 5  # 5 unidades para toner/cartucho
        else:
            try:
                minimo = int(minimo_str)
            except (TypeError, ValueError):
                logger.warning(
                    "adicionar_item: estoque minimo invalido '%s'", minimo_str
                )
                self.notificar("Estoque minimo deve ser um numero.", "error")
                return

        if not nome:
            self.notificar("Digite um nome para o item.", "error")
            return
        try:
            inserido = db.inserir_item(nome, tipo, minimo)
        except Exception:
            logger.exception("Erro inesperado ao inserir item '%s'", nome)
            self.notificar("Erro ao salvar o item.", "error")
            return
        if inserido:
            logger.info("Item '%s' (tipo=%s, minimo=%d) adicionado", nome, tipo, minimo)
            self.notificar(f"Item '{nome}' adicionado com sucesso!", "success")
        else:
            logger.info("Item '%s' nao inserido (nome duplicado)", nome)
            self.notificar(f"Ja existe um item com o nome '{nome}'.", "error")
        self._recarregar()

    # ---------------- Exclusao generica com cascata ----------------
    def _nome_do_registro(self, tabela: str, registro_id: int) -> str:
        """Nome exibivel do registro, para o dialogo de confirmacao."""
        if tabela == "filiais":
            for r in self.filiais:
                if r["id"] == registro_id:
                    return r["nome"]
        elif tabela == "departamentos":
            for r in self.deptos:
                if r["id"] == registro_id:
                    return r["nome"]
        elif tabela == "itens":
            for r in self.itens:
                if r["id"] == registro_id:
                    return r["nome"]
        return "(registro)"

    @rx.event
    def excluir(self, tabela: str, registro_id: int):
        """Clique na lixeira: tenta excluir. Se houver lançamentos vinculados,
        abre confirmacao para exclusao em cascata (remove os lançamentos)."""
        try:
            registro_id = int(registro_id)
        except (TypeError, ValueError):
            logger.warning("excluir: registro_id invalido %r", registro_id)
            self.notificar("Registro invalido.", "error")
            return

        tabela = str(tabela or "")
        if tabela not in ("filiais", "departamentos", "itens"):
            self.notificar("Tipo de registro invalido.", "error")
            return

        # Quantos lançamentos dependem deste registro?
        dep_tabelas = {
            "filiais": ("despachos", "filial_id", "despacho(s)"),
            "departamentos": ("despachos", "departamento_id", "despacho(s)"),
            "itens": ("entradas", "item_id", "entrada(s)"),
        }
        dep_tabela, dep_col, dep_rotulo = dep_tabelas[tabela]
        conn = db.get_conn()
        try:
            total_dep = conn.execute(
                f"SELECT COUNT(*) FROM {dep_tabela} WHERE {dep_col} = ?",
                (registro_id,),
            ).fetchone()[0]
            if tabela == "itens":
                total_dep += conn.execute(
                    "SELECT COUNT(*) FROM despachos WHERE item_id = ?",
                    (registro_id,),
                ).fetchone()[0]
        except Exception:
            logger.exception(
                "Erro ao consultar dependencias de %s id=%d", tabela, registro_id
            )
            self.notificar("Erro ao verificar dependencias do registro.", "error")
            return
        finally:
            conn.close()

        nome = self._nome_do_registro(tabela, registro_id)

        if total_dep > 0:
            # Registro em uso: pede confirmacao para cascata
            logger.info(
                "Exclusao de %s '%s' (id=%d) pendente: %d dependencias — "
                "aguardando confirmacao do usuario",
                tabela, nome, registro_id, total_dep,
            )
            self.confirm_open = True
            self.confirm_tabela = tabela
            self.confirm_id = registro_id
            self.confirm_nome = nome
            self.confirm_total = total_dep
            self.confirm_rotulo = dep_rotulo
            return

        # Sem dependencias: exclui direto
        try:
            excluido = db.excluir(tabela, registro_id)
        except Exception:
            logger.exception(
                "Erro inesperado ao excluir %s id=%d", tabela, registro_id
            )
            self.notificar("Erro ao excluir o registro.", "error")
            return
        if excluido:
            logger.info("%s '%s' (id=%d) excluido(a)", tabela, nome, registro_id)
            self.notificar(f"'{nome}' excluido(a) com sucesso!", "success")
        else:
            logger.info(
                "%s id=%d nao encontrado para exclusao", tabela, registro_id
            )
            self.notificar("Nao foi possivel excluir o registro.", "error")
        self._recarregar()

    @rx.event
    def confirmar_exclusao_cascata(self):
        """Exclui o registro e todos os lançamentos vinculados (confirmado).

        Salva o payload em _pending_payload ANTES de fechar o dialogo,
        para que on_open_change (que chama cancelar_exclusao) nao zere
        os dados antes de este handler executar.
        """
        # Snapshot antes de fechar — on_open_change pode rodar entre agora e o commit
        self._pending_payload = {
            "tabela": self.confirm_tabela,
            "id": int(self.confirm_id or 0),
            "nome": self.confirm_nome,
        }
        self._fechar_confirmacao()

        tabela = self._pending_payload["tabela"]
        rid = self._pending_payload["id"]
        nome = self._pending_payload["nome"]

        if tabela not in ("filiais", "departamentos", "itens") or not rid:
            logger.warning(
                "confirmar_exclusao_cascata: payload invalido tabela=%r rid=%d",
                tabela, rid,
            )
            self.notificar("Registro invalido para exclusao.", "error")
            self._pending_payload = {}
            return

        conn = db.get_conn()
        try:
            # Remove primeiro os lançamentos que dependem deste registro,
            # depois o proprio registro (respeitando as FKs).
            if tabela == "filiais":
                conn.execute("DELETE FROM despachos WHERE filial_id = ?", (rid,))
            elif tabela == "departamentos":
                conn.execute("DELETE FROM despachos WHERE departamento_id = ?", (rid,))
            elif tabela == "itens":
                conn.execute("DELETE FROM entradas WHERE item_id = ?", (rid,))
                conn.execute("DELETE FROM despachos WHERE item_id = ?", (rid,))
            conn.execute(f"DELETE FROM {tabela} WHERE id = ?", (rid,))
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception(
                "Erro ao excluir %s '%s' (id=%d) em cascata", tabela, nome, rid
            )
            self.notificar(
                "Erro ao excluir o registro e seus lancamentos.", "error"
            )
            return
        finally:
            conn.close()

        logger.info(
            "%s '%s' (id=%d) e dependencias excluidos em cascata",
            tabela, nome, rid,
        )
        self.notificar(
            f"'{nome}' e seus lançamentos foram excluidos com sucesso!", "success"
        )
        self._pending_payload = {}
        self._recarregar()

    @rx.event
    def cancelar_exclusao(self, aberto=None):
        """Fecha o dialogo sem excluir nada.

        Aceita o argumento opcional 'aberto' (bool) enviado por
        on_open_change quando o usuario fecha por Escape/fora/roda.
        Tambem serve para o botao Cancelar (sem argumento).

        NAO limpa _pending_payload — apenas confirmar_exclusao_cascata
        o faz apos sucesso, evitando race-condition com on_open_change.
        """
        self._fechar_confirmacao()

    def _fechar_confirmacao(self):
        self.confirm_open = False
        self.confirm_tabela = ""
        self.confirm_id = 0
        self.confirm_nome = ""
        self.confirm_total = 0
        self.confirm_rotulo = ""