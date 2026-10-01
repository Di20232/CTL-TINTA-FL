"""Regressoes de estoque, validacao e CSV sem acessar o banco real.

Execute na raiz: python -m unittest discover -s tests -p "test_*.py" -v

Usa somente a biblioteca padrao. Cada teste de banco recebe um diretorio
 temporario exclusivo. Nao importa o app web, nao inicia servidores e nao
 executa os fuzzers antigos. As assercoes descrevem o comportamento esperado;
 bugs existentes devem aparecer como falhas, nao como expectedFailure.
"""

import csv
import io
import math
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import db
from app_reflex import util_unidade as unidade
from app_reflex.util_csv import gerar_csv_relatorio


class BancoTemporario(unittest.TestCase):
    """Base sem testes: redireciona toda conexao de db.py antes do init_db."""

    def setUp(self):
        temporario = tempfile.TemporaryDirectory(prefix="ctl_regressao_")
        self.addCleanup(temporario.cleanup)
        caminho = Path(temporario.name) / "teste.db"
        self.assertNotEqual(caminho.resolve(), Path(db.DB_PATH).resolve())
        remendo = patch.object(db, "DB_PATH", str(caminho))
        remendo.start()
        self.addCleanup(remendo.stop)
        db.init_db()
        # Fixtures fixas e sinteticas, sem depender das funcoes sob teste.
        with closing(db.get_conn()) as conn, conn:
            conn.execute("INSERT INTO filiais (id, nome) VALUES (1, 'Filial teste')")
            conn.execute("INSERT INTO departamentos (id, nome) VALUES (1, 'TI teste')")
            conn.executemany(
                "INSERT INTO itens (id, nome, tipo, estoque_minimo) VALUES (?, ?, ?, ?)",
                [(1, "Toner teste", "Toner", 5), (2, "Tinta teste", "Tinta", 1)],
            )

    def consultar(self, sql, parametros=()):
        with closing(db.get_conn()) as conn:
            return conn.execute(sql, parametros).fetchall()

    def total(self, tabela):
        if tabela not in {"filiais", "departamentos", "itens", "entradas", "despachos"}:
            raise ValueError("Tabela fora do escopo do teste")
        return self.consultar(f"SELECT COUNT(*) FROM {tabela}")[0][0]

    def entrada(self, quantidade=10, item_id=1, valor=10):
        return db.inserir_entrada("2026-09-16", item_id, quantidade, "Teste", valor, "")

    def despacho(self, quantidade=3, item_id=1, filial_id=1, chamado="TESTE-1"):
        return db.inserir_despacho(
            "2026-09-16", filial_id, 1, item_id, quantidade, chamado, "Teste", ""
        )

    def assert_rejeita_sem_gravar(self, operacao, tabela):
        """Aceita rejeicao por ValueError/IntegrityError ou retorno sem gravacao."""
        antes = self.total(tabela)
        try:
            operacao()
        except (ValueError, sqlite3.IntegrityError):
            pass
        self.assertEqual(self.total(tabela), antes, "Dado invalido foi persistido")


class TestFluxosBanco(BancoTemporario):
    def test_saldo_apos_entrada_e_despacho(self):
        self.entrada(10)
        self.despacho(3)
        self.assertEqual(self.total("entradas"), 1)
        self.assertEqual(self.total("despachos"), 1)
        self.assertEqual(db.saldo_atual(1), 7)

    def test_tinta_fracionada_preserva_litros(self):
        self.entrada(1.5, item_id=2)
        self.despacho(unidade.ml_para_litros(250), item_id=2)
        self.assertAlmostEqual(db.saldo_atual(2), 1.25)

    def test_saldo_itens_confere_com_saldo_individual(self):
        self.entrada(10)
        self.entrada(2.5, item_id=2)
        self.despacho(4)
        self.assertEqual(db.saldo_itens(), {1: 6, 2: 2.5})

    def test_filial_duplicada_nao_cria_segundo_registro(self):
        self.assertFalse(db.inserir("filiais", "Filial teste"))
        self.assertEqual(self.total("filiais"), 1)

    def test_item_em_uso_nao_pode_ser_excluido(self):
        self.entrada()
        self.assertFalse(db.excluir("itens", 1))
        self.assertEqual(self.total("itens"), 2)
        self.assertEqual(self.total("entradas"), 1)

    def test_sql_em_nome_e_tratado_como_texto(self):
        nome = "Teste'); DROP TABLE itens; --"
        self.assertTrue(db.inserir("filiais", nome))
        self.assertEqual(self.total("itens"), 2)
        self.assertIn(nome, [r["nome"] for r in db.listar("filiais")])

    def test_nome_de_tabela_injetado_e_rejeitado(self):
        with self.assertRaises(ValueError):
            db.listar("filiais; DROP TABLE itens; --")
        self.assertEqual(self.total("itens"), 2)

    def test_filtro_sql_nao_retoma_todas_as_linhas(self):
        self.entrada()
        self.despacho()
        self.assertEqual(db.relatorio_despachos({"filial": "' OR '1'='1"}), [])
        self.assertEqual(self.total("despachos"), 1)

    def test_entradas_concorrentes_nao_perdem_registros(self):
        # Carga pequena e finita, somente em arquivo temporario.
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _: self.entrada(1), range(12)))
        self.assertEqual(self.total("entradas"), 12)
        self.assertEqual(db.saldo_atual(1), 12)

    def test_filtro_de_periodo(self):
        self.entrada()
        self.despacho()
        self.assertEqual(len(db.relatorio_despachos({"de": "2026-09-16", "ate": "2026-09-16"})), 1)
        self.assertEqual(db.relatorio_despachos({"ate": "2026-09-15"}), [])


class TestFalhasBanco(BancoTemporario):
    def test_entrada_com_fk_inexistente_informa_falha_ao_chamador(self):
        # O chamador usa excecoes para distinguir erro de sucesso.
        with self.assertRaises(sqlite3.IntegrityError):
            self.entrada(item_id=9999)
        self.assertEqual(self.total("entradas"), 0)

    def test_despacho_com_fk_inexistente_informa_falha_ao_chamador(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.despacho(filial_id=9999)
        self.assertEqual(self.total("despachos"), 0)

    def test_erro_de_leitura_nao_e_exibido_como_estoque_vazio(self):
        # Banco quebrado e simulado por mock, sem danificar arquivo algum.
        with patch.object(db, "get_conn") as abrir:
            abrir.return_value.execute.side_effect = sqlite3.OperationalError("falha simulada")
            with self.assertRaises(sqlite3.OperationalError):
                db.estoque_atual()
            abrir.return_value.close.assert_called_once()

    def test_erro_operacional_nao_e_confundido_com_nome_duplicado(self):
        with patch.object(db, "get_conn") as abrir:
            abrir.return_value.execute.side_effect = sqlite3.OperationalError("falha simulada")
            with self.assertRaises(sqlite3.OperationalError):
                db.inserir("filiais", "Nome novo")

    def test_entrada_rejeita_quantidade_negativa(self):
        self.assert_rejeita_sem_gravar(lambda: self.entrada(-5), "entradas")

    def test_despacho_rejeita_quantidade_negativa(self):
        self.assert_rejeita_sem_gravar(lambda: self.despacho(-5), "despachos")

    def test_entrada_rejeita_quantidade_infinita(self):
        self.assert_rejeita_sem_gravar(lambda: self.entrada(math.inf, item_id=2), "entradas")

    def test_entrada_rejeita_preco_negativo(self):
        self.assert_rejeita_sem_gravar(lambda: self.entrada(valor=-1), "entradas")

    def test_entrada_rejeita_preco_infinito(self):
        self.assert_rejeita_sem_gravar(lambda: self.entrada(valor=math.inf), "entradas")

    def test_item_rejeita_minimo_negativo(self):
        self.assert_rejeita_sem_gravar(lambda: db.inserir_item("Invalido", "Toner", -1), "itens")

    def test_entrada_rejeita_data_iso_nao_canonica(self):
        # strptime aceita "2026-9-1"; gravada assim, quebraria ordenacao e filtros.
        for data in ("2026-9-1", "2026-09-1", "2026-9-01", "2026/09/01", " 2026-09-01"):
            with self.subTest(data=data):
                self.assert_rejeita_sem_gravar(
                    lambda: db.inserir_entrada(data, 1, 1, "", None, ""), "entradas"
                )
        self.assertIsNone(db.inserir_entrada("2026-09-01", 1, 1, "", None, ""))

    def test_entrada_rejeita_data_impossivel(self):
        self.assert_rejeita_sem_gravar(
            lambda: db.inserir_entrada("2026-02-31", 1, 1, "", None, ""), "entradas"
        )


class TestValidacoes(unittest.TestCase):
    def test_quantidades_validas_e_unidades(self):
        self.assertEqual(unidade.validar_quantidade("0,5", "Tinta"), (0.5, None))
        self.assertEqual(unidade.validar_quantidade("3", "Toner"), (3, None))
        self.assertEqual(unidade.validar_quantidade_despacho("250", "Tinta"), (250, None))
        self.assertEqual(unidade.formatar_despacho(0.25, "Tinta"), "250 ml")

    def test_toner_nao_aceita_fracao(self):
        valor, erro = unidade.validar_quantidade("0,5", "Toner")
        self.assertIsNone(valor)
        self.assertTrue(erro)

    def test_quantidades_vazias_negativas_e_tipos_invalidos(self):
        for texto in ("", "0", "-1", None, [], {}, 123, "texto"):
            for validar in (unidade.validar_quantidade, unidade.validar_quantidade_despacho):
                with self.subTest(texto=texto, funcao=validar.__name__):
                    valor, erro = validar(texto, "Toner")
                    self.assertIsNone(valor)
                    self.assertTrue(erro)

    def test_quantidade_rejeita_nan_infinito_e_overflow(self):
        for texto in ("nan", "NaN", "inf", "+Infinity", "1e309"):
            for tipo in ("Tinta", "Toner", "Cartucho"):
                for validar in (unidade.validar_quantidade, unidade.validar_quantidade_despacho):
                    with self.subTest(texto=texto, tipo=tipo, funcao=validar.__name__):
                        # Nao deve nem aceitar o valor nem lancar ValueError/OverflowError.
                        valor, erro = validar(texto, tipo)
                        self.assertIsNone(valor)
                        self.assertTrue(erro)

    def test_datas_validas_e_invalidas(self):
        self.assertEqual(db.to_iso("29/02/2024"), "2024-02-29")
        self.assertIsNone(db.to_iso("29/02/2025"))
        self.assertIsNone(db.to_iso("31/02/2026"))
        self.assertEqual(db.to_display("2026-09-16"), "16/09/2026")


class TestCSV(BancoTemporario):
    def test_csv_tem_bom_e_quantidade_em_ml(self):
        self.entrada(1, item_id=2)
        self.despacho(0.25, item_id=2)
        conteudo = gerar_csv_relatorio({})
        self.assertTrue(conteudo.startswith("﻿"))
        linhas = list(csv.reader(io.StringIO(conteudo.lstrip("﻿")), delimiter=";"))
        self.assertEqual(linhas[1][0], "16/09/2026")
        self.assertEqual(linhas[1][4:6], ["250", "ml"])

    def test_csv_preserva_acentos_e_separadores(self):
        chamado = 'Acentuação; "teste"\nlinha 2'
        self.entrada()
        self.despacho(chamado=chamado)
        linhas = list(csv.reader(io.StringIO(gerar_csv_relatorio({}).lstrip("﻿")), delimiter=";"))
        self.assertEqual(linhas[1][6], chamado)

    def test_csv_neutraliza_formula_em_campo_textual(self):
        # Formula aritmetica inofensiva: o teste nao abre planilha nem executa nada.
        self.entrada()
        self.despacho(chamado="=1+1")
        linhas = list(csv.reader(io.StringIO(gerar_csv_relatorio({}).lstrip("﻿")), delimiter=";"))
        self.assertFalse(
            linhas[1][6].lstrip().startswith(("=", "+", "-", "@")),
            "Campo textual pode ser interpretado como formula pela planilha",
        )


if __name__ == "__main__":
    unittest.main()
