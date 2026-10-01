"""Testes unitarios dos handlers reais, sem iniciar o app Reflex.

Requer Reflex instalado. Usa as funcoes originais dos EventHandlers com um
objeto simples representando os campos de estado. Nao simula o transporte de
 eventos, a hidratacao do navegador ou a renderizacao: esses exigem testes E2E.
O banco e temporario, conforme BancoTemporario. Nenhum fuzzer e importado.
"""

import importlib.util
import types
import unittest
from contextlib import closing
from unittest.mock import patch

import db
from tests.test_regressoes import BancoTemporario


def funcao_original(classe, nome):
    metodo = getattr(classe, nome)
    # Reflex transforma metodos publicos em EventHandler e guarda a funcao em fn.
    return getattr(metodo, "fn", metodo)


def estado_simples(classe, metodos=(), **campos):
    estado = types.SimpleNamespace(msg="", tipo_msg="", **campos)

    def notificar(texto, tipo="success"):
        estado.msg = texto
        estado.tipo_msg = tipo

    estado.notificar = notificar
    for nome in metodos:
        setattr(estado, nome, types.MethodType(funcao_original(classe, nome), estado))
    return estado


@unittest.skipUnless(importlib.util.find_spec("reflex"), "Reflex nao instalado: handlers nao testados")
class TestEstados(BancoTemporario):
    def setUp(self):
        super().setUp()
        # So importa modulos de estados depois de redirecionar o banco.
        # Nao importa app_reflex.app_reflex (que inicializa banco ao importar).
        from app_reflex.estados.cadastros import CadastrosState
        from app_reflex.estados.despacho import DespachoState
        from app_reflex.estados.entrada import EntradaState
        from app_reflex.estados.relatorios import RelatoriosState

        self.cadastros_cls = CadastrosState
        self.despacho_cls = DespachoState
        self.entrada_cls = EntradaState
        self.relatorios_cls = RelatoriosState
        self.itens = [dict(r) for r in db.listar_itens()]

    def estado_entrada(self):
        return estado_simples(
            self.entrada_cls, itens=self.itens, entradas=[], data="", item_id="1",
            quantidade="1", fornecedor="Teste", valor_unitario="", observacao="",
        )

    def estado_despacho(self):
        return estado_simples(
            self.despacho_cls, ("_item_por_id", "_pos_salvar", "_limpar_form"),
            itens=self.itens, filiais=[{"id": 1, "nome": "Filial teste"}],
            deptos=[{"id": 1, "nome": "TI teste"}], despachos=[],
            saldo_item=0, saldo_txt="", unidade="un", confirmacao_pendente=False,
            dados_pendentes={}, data="16/09/2026", filial_id="1",
            departamento_id="1", item_id="1", quantidade="2", chamado="",
            recebedor="", observacao="",
        )

    def estado_relatorio(self):
        return estado_simples(
            self.relatorios_cls, ("_aplicar",), itens=self.itens, rows=[],
            total_qtd=0, total_ml="0", total_unidades=0, agregados=[],
            filtro_de="", filtro_ate="", filtro_filial="",
            filtro_departamento="", filtro_item="", csv_pronto="",
        )

    def formulario_despacho(self):
        return {"data": "16/09/2026", "filial_id": "1", "departamento_id": "1",
                "item_id": "1", "quantidade": "2", "chamado": "TESTE-1",
                "recebedor": "Teste", "observacao": ""}

    def test_entrada_de_item_excluido_nao_anuncia_sucesso(self):
        estado = self.estado_entrada()
        # Simula cadastro excluido por outra sessao depois de carregar o formulario.
        with closing(db.get_conn()) as conn, conn:
            conn.execute("DELETE FROM itens WHERE id = 1")
        funcao_original(self.entrada_cls, "salvar")(
            estado, {"item_id": "1", "quantidade": "1"}
        )
        self.assertEqual(self.total("entradas"), 0)
        self.assertEqual(estado.tipo_msg, "error")

    def test_entrada_rejeita_valor_unitario_negativo(self):
        estado = self.estado_entrada()
        funcao_original(self.entrada_cls, "salvar")(
            estado, {"item_id": "1", "quantidade": "1", "valor_unitario": "-5"}
        )
        self.assertEqual(self.total("entradas"), 0)
        self.assertEqual(estado.tipo_msg, "error")

    def test_entrada_rejeita_payload_com_tipo_incorreto_sem_excecao(self):
        estado = self.estado_entrada()
        funcao_original(self.entrada_cls, "salvar")(
            estado, {"item_id": ["1"], "quantidade": "1"}
        )
        self.assertEqual(self.total("entradas"), 0)
        self.assertEqual(estado.tipo_msg, "error")

    def test_despacho_insuficiente_pede_confirmacao_sem_gravar(self):
        estado = self.estado_despacho()
        funcao_original(self.despacho_cls, "salvar")(estado, self.formulario_despacho())
        self.assertTrue(estado.confirmacao_pendente)
        self.assertEqual(self.total("despachos"), 0)
        self.assertEqual(estado.tipo_msg, "warning")

    def test_reenvio_de_formulario_nao_substitui_confirmacao_explicita(self):
        estado = self.estado_despacho()
        salvar = funcao_original(self.despacho_cls, "salvar")
        salvar(estado, self.formulario_despacho())
        self.assertTrue(estado.confirmacao_pendente)
        # Novo envio, inclusive com outra quantidade, nao e clique em confirmar.
        alterado = self.formulario_despacho()
        alterado["quantidade"] = "4"
        salvar(estado, alterado)
        self.assertEqual(self.total("despachos"), 0)
        self.assertTrue(estado.confirmacao_pendente)

    def test_confirmacao_dupla_nao_duplica_despacho(self):
        estado = self.estado_despacho()
        funcao_original(self.despacho_cls, "salvar")(estado, self.formulario_despacho())
        confirmar = funcao_original(self.despacho_cls, "confirmar")
        confirmar(estado)
        confirmar(estado)
        self.assertEqual(self.total("despachos"), 1)
        self.assertFalse(estado.confirmacao_pendente)
        self.assertEqual(estado.dados_pendentes, {})

    def test_cancelar_nao_grava_despacho(self):
        estado = self.estado_despacho()
        funcao_original(self.despacho_cls, "salvar")(estado, self.formulario_despacho())
        funcao_original(self.despacho_cls, "cancelar")(estado)
        self.assertEqual(self.total("despachos"), 0)
        self.assertFalse(estado.confirmacao_pendente)
        self.assertEqual(estado.dados_pendentes, {})

    def test_relatorio_nao_soma_mililitros_com_unidades(self):
        self.entrada(5)
        self.entrada(1, item_id=2)
        self.despacho(3)
        self.despacho(0.5, item_id=2)
        estado = self.estado_relatorio()
        estado._aplicar({})
        self.assertEqual(estado.total_ml, "500")
        self.assertEqual(estado.total_unidades, 3)
        texto = " | ".join(a["total_txt"] for a in estado.agregados)
        self.assertIn("500 ml", texto)
        self.assertIn("3 un", texto)

    def test_agregados_ordenam_por_unidade_sem_somar_ml_com_un(self):
        # Filial B: 2 un + 900 ml. Filial A: 1 un + 100 ml. Somar daria B > A pelo
        # ml; por (un, ml) B tambem lidera, mas o criterio nunca mistura unidades.
        with closing(db.get_conn()) as conn, conn:
            conn.execute("INSERT INTO filiais (id, nome) VALUES (2, 'Filial B')")
        self.entrada(10)
        self.entrada(5, item_id=2)
        self.despacho(1, filial_id=1)          # A: 1 un
        self.despacho(0.1, item_id=2, filial_id=1)  # A: 100 ml
        self.despacho(2, filial_id=2)          # B: 2 un
        self.despacho(0.9, item_id=2, filial_id=2)  # B: 900 ml
        estado = self.estado_relatorio()
        estado._aplicar({})
        self.assertEqual([a["filial"] for a in estado.agregados], ["Filial B", "Filial teste"])
        self.assertEqual(estado.agregados[0]["total_txt"], "2 un + 900 ml")
        self.assertNotIn("total", estado.agregados[0])

    def test_filtrar_com_erro_limpa_resultado_anterior(self):
        self.entrada(10)
        self.despacho(3)
        estado = self.estado_relatorio()
        estado._aplicar({})
        self.assertTrue(estado.rows and estado.agregados)
        with patch("db.relatorio_despachos", side_effect=OSError("falha simulada")):
            funcao_original(self.relatorios_cls, "filtrar")(estado, {})
        self.assertEqual(estado.tipo_msg, "error")
        self.assertEqual(estado.rows, [])
        self.assertEqual(estado.agregados, [])
        self.assertEqual((estado.total_qtd, estado.total_ml, estado.total_unidades), (0, "0", 0))

    def test_exportacao_nao_ignora_data_invalida(self):
        estado = self.estado_relatorio()
        estado.filtro_de = "31/02/2026"
        with patch("app_reflex.util_csv.gerar_csv_relatorio", return_value="CSV teste") as gerar:
            funcao_original(self.relatorios_cls, "exportar_csv")(estado)
            gerar.assert_not_called()
        self.assertEqual(estado.tipo_msg, "error")

    def test_filtrar_informa_erro_de_banco_sem_excecao(self):
        estado = self.estado_relatorio()
        with patch("db.relatorio_despachos", side_effect=OSError("falha simulada")):
            funcao_original(self.relatorios_cls, "filtrar")(estado, {})
        self.assertEqual(estado.tipo_msg, "error")

    def test_cadastro_rejeita_minimo_negativo(self):
        estado = estado_simples(self.cadastros_cls)
        estado._recarregar = lambda: None
        funcao_original(self.cadastros_cls, "adicionar_item")(
            estado, {"nome": "Item negativo", "tipo": "Toner", "estoque_minimo": "-1"}
        )
        self.assertEqual(self.total("itens"), 2)
        self.assertEqual(estado.tipo_msg, "error")


if __name__ == "__main__":
    unittest.main()
