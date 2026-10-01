#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuzzer de path traversal / escrita arbitraria.
Alvos:
  1) controle_suprimentos.AbaRelatorios.exportar_csv  (path via filedialog)
  2) shot.main  (path = os.path.join(SHOTS, f"{nome}.png"))
Objetivo: tentar escrever fora do diretorio esperado usando payloads maliciosos
em 'path' (exportar_csv) e em 'nome' (shot). Captura falhas concretas.
"""
import os
import sys
import io
import traceback
import tempfile
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(ROOT, "_fuzzer_tmp")
os.makedirs(TMP, exist_ok=True)

# -----------------------------------------------------------------------
# Importa alvos sem instanciar a GUI Tkinter o maximo possivel.
# Para exportar_csv precisamos de uma instancia de AbaRelatorios, que herda
# de ttk.Frame -- instanciar exige um Tk root. Em vez disso, testamos a
# logica de escrita diretamente (open + csv.writer) com os mesmos payloads
# que a funcao real aceitaria, e tambem testamos o comportamento de
# os.path.join (vetor do shot.py) isoladamente.
# -----------------------------------------------------------------------

sys.path.insert(0, ROOT)

import csv as _csv

# Payloads de path traversal / escrita arbitraria
PAYLOADS = [
    # relativos
    ("../ travessa relativa 1", "../evil_out.csv"),
    ("../ travessa relativa 2", "../../evil_out.csv"),
    ("../ travessa relativa 3", "../../../evil_out.csv"),
    ("../ travessa com subdir", "../subdir_evil/evil.csv"),
    ("../ + nome de arquivo do sistema", "../controle_suprimentos.py"),
    ("../ tentando sobrescrever db", "../controle_suprimentos.db"),
    ("../ tentando sobrescrever log", "../controle_suprimentos.log"),
    # absolutos (Windows)
    ("absoluto Windows raiz", "C:\\evil_abs.csv"),
    ("absoluto Windows temp", os.path.join(tempfile.gettempdir(), "evil_abs2.csv")),
    ("absoluto Unix-like em Windows", "/evil_unix.csv"),
    ("absoluto com dispositivo", "CON"),
    ("absoluto com dispositivo NUL", "NUL"),
    # caracteres especiais / nome
    ("nome com .. no meio", "relatorio..csv"),
    ("nome com barra invertida", "evil\\dir\\x.csv"),
    ("nome com barra normal", "evil/dir/x.csv"),
    ("nome com ponto-e-virgula", "evil;x.csv"),
    ("nome com espaco", "evil name.csv"),
    ("nome com unicode", "relatório_é.csv"),
    ("nome vazio", ""),
    ("nome so ponto", "."),
    ("nome so dois pontos", ".."),
    ("nome com null byte", "evil\x00.csv"),
    ("nome muito longo", "A" * 300 + ".csv"),
    ("nome com wildcards", "*.csv"),
    ("nome com pipe", "evil|x.csv"),
    # tentativa de sobrescrever arquivos criticos via path absoluto
    ("sobrescrever hosts (abs)", r"C:\Windows\System32\drivers\etc\hosts_test_fuzzer"),
    ("sobrescrever system32 (abs)", r"C:\Windows\System32\evil_fuzzer.csv"),
]

# Para o vetor do shot.py: payloads injetados no segmento 'nome' antes do .png
SHOT_PAYLOADS = [
    ("shot ../ simples", "../evil_shot.png"),
    ("shot ../ duplo", "../../evil_shot.png"),
    ("shot absoluto Windows", "C:\\evil_shot_abs.png"),
    ("shot absoluto Unix", "/evil_shot_unix.png"),
    ("shot com .. no meio", "../sub/evil_shot.png"),
    ("shot tentando escapar para raiz", "../../../evil_shot.png"),
    ("shot nome com null byte", "evil\x00shot.png"),
    ("shot nome com caractere invalido", "evil<:>shot.png"),
    ("shot nome vazio", ""),
    ("shot nome so ponto", "."),
]


def _resolve_for_shot(nome):
    """Replica a construcao de path do shot.py: os.path.join(SHOTS, f'{nome}.png')."""
    SHOTS = os.path.join(ROOT, "screenshots")
    return os.path.join(SHOTS, f"{nome}.png")


def _is_within(child, parent):
    """True se 'child' esta dentro de 'parent' (ambos resolvidos absolutos)."""
    try:
        cr = os.path.abspath(child)
        pr = os.path.abspath(parent)
        return os.path.commonpath([pr, cr]) == pr
    except ValueError:
        return False


def fuzz_exportar_csv():
    """
    Replica a logica de escrita de exportar_csv (open(path,'w',...) + csv.writer)
    mas aponta para dentro de TMP quando seguro, ou registra falha quando o
    payload escapa / e efetivamente escrito fora.
    Para simular o comportamento real, tentamos o open() com o path EXATAMENTE
    como recebido (sem join com nada), pois e isso que a funcao faz.
    """
    print("=" * 78)
    print("FUZZER: AbaRelatorios.exportar_csv (open(path, 'w') + csv.writer)")
    print("=" * 78)
    failures = []
    rows = [["2024-01-01", "Filial X", "Depto Y", "Item Z", 5, "CH-1", "Fulano"]]
    for label, path in PAYLOADS:
        # converte path relativo para ser interpretado a partir de TMP (cwd do fuzzer)
        # para simular o comportamento real: a funcao recebe o path cru do filedialog.
        # Em Windows, path relativos sao resolvidos a partir do CWD. Mudamos CWD para TMP.
        cwd_orig = os.getcwd()
        os.chdir(TMP)
        try:
            # Replica exatamente: if not path: return  -> para path vazio, a funcao aborta.
            if not path:
                print(f"  [SKIP ] {label:45s} path vazio -> exportar_csv aborta (return). OK defensivo.")
                continue
            # Replica: with open(path, "w", newline="", encoding="utf-8-sig") as f
            # CAPTURA: se o open() cria arquivo fora de TMP, e uma escrita arbitria.
            try:
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    w = _csv.writer(f, delimiter=";")
                    w.writerow(["Data", "Filial"])
                    for r in rows:
                        w.writerow(r)
                # Verifica onde o arquivo efetivamente foi criado
                abs_path = os.path.abspath(path)
                within = _is_within(abs_path, TMP)
                # Tenta limpar
                try:
                    if os.path.isfile(abs_path):
                        os.remove(abs_path)
                except OSError:
                    pass
                if not within:
                    failures.append({
                        "label": label,
                        "path": path,
                        "resolved": abs_path,
                        "within_tmp": within,
                        "trace": "open(path,'w') criou arquivo FORA do diretorio esperado (escrita arbitria).",
                    })
                    print(f"  [FAIL ] {label:45s} -> {abs_path}  (FORA de TMP)")
                else:
                    print(f"  [ok   ] {label:45s} -> {abs_path}")
            except (OSError, ValueError, PermissionError) as e:
                # A funcao real so captura OSError. ValueError (null byte) NAO e capturado
                # e propagaria como excecao nao tratada -> crash.
                etype = type(e).__name__
                if isinstance(e, OSError) and not isinstance(e, PermissionError):
                    # replicaria o except OSError da funcao -> messagebox, return (silencioso)
                    print(f"  [ok   ] {label:45s} -> OSError capturado ({e})")
                else:
                    # PermissionError e ValueError NAO sao capturados pelo except OSError
                    # -> propagariam e crashariam o app
                    failures.append({
                        "label": label,
                        "path": path,
                        "resolved": "(nao criado)",
                        "within_tmp": None,
                        "trace": f"{etype}: {e} -- NAO capturado por 'except OSError' em exportar_csv; propagaria e crasharia.",
                    })
                    print(f"  [FAIL ] {label:45s} -> {etype}: {e}  (NAO capturado por except OSError)")
        except Exception as e:
            failures.append({
                "label": label,
                "path": path,
                "resolved": "(erro inesperado)",
                "within_tmp": None,
                "trace": f"Erro inesperado no fuzzer: {type(e).__name__}: {e}\n{traceback.format_exc()}",
            })
            print(f"  [ERR  ] {label:45s} -> {type(e).__name__}: {e}")
        finally:
            os.chdir(cwd_orig)
    return failures


def fuzz_shot():
    """
    Replica a construcao de path do shot.py: os.path.join(SHOTS, f'{nome}.png')
    e verifica se o path resultante escapa de SHOTS. Em seguida tenta o open()
    simulado (apenas cria o arquivo para confirmar a escrita, depois remove).
    """
    print()
    print("=" * 78)
    print("FUZZER: shot.main (path = os.path.join(SHOTS, f'{nome}.png'))")
    print("=" * 78)
    failures = []
    SHOTS = os.path.join(ROOT, "screenshots")
    os.makedirs(SHOTS, exist_ok=True)
    for label, nome in SHOT_PAYLOADS:
        try:
            # Replica exatamente a construcao do shot.py
            path = os.path.join(SHOTS, f"{nome}.png")
            abs_path = os.path.abspath(path)
            within = _is_within(abs_path, SHOTS)
            # Simula a escrita (page.screenshot(path=path)) criando o arquivo
            try:
                with open(path, "wb") as f:
                    f.write(b"\x89PNG\r\n\x1a\nFAKE")
                created = os.path.isfile(abs_path)
            except (OSError, ValueError, PermissionError) as e:
                etype = type(e).__name__
                # shot.py NAO tem try/except em volta do screenshot() -> qualquer erro crasha
                if not within:
                    failures.append({
                        "label": label,
                        "path": path,
                        "resolved": abs_path,
                        "within_shots": False,
                        "trace": f"os.path.join escapou de SHOTS -> {abs_path}. {etype} ao tentar escrever: {e}. shot.py sem try/except -> crash.",
                    })
                    print(f"  [FAIL ] {label:45s} -> {abs_path}  (FORA de SHOTS, {etype})")
                else:
                    print(f"  [ok   ] {label:45s} -> {abs_path}  ({etype} dentro de SHOTS)")
                continue
            # limpou
            try:
                if created and os.path.isfile(abs_path):
                    os.remove(abs_path)
            except OSError:
                pass
            if not within:
                failures.append({
                    "label": label,
                    "path": path,
                    "resolved": abs_path,
                    "within_shots": False,
                    "trace": f"os.path.join(SHOTS, '{{nome}}.png') resultou em path FORA de SHOTS: {abs_path}. "
                              f"Arquivo efetivamente criado fora do diretorio esperado -> escrita arbitria confirmada.",
                })
                print(f"  [FAIL ] {label:45s} -> {abs_path}  (FORA de SHOTS, escrita confirmada)")
            else:
                print(f"  [ok   ] {label:45s} -> {abs_path}")
        except Exception as e:
            failures.append({
                "label": label,
                "path": nome,
                "resolved": "(erro inesperado)",
                "within_shots": None,
                "trace": f"Erro inesperado no fuzzer: {type(e).__name__}: {e}\n{traceback.format_exc()}",
            })
            print(f"  [ERR  ] {label:45s} -> {type(e).__name__}: {e}")
    return failures


def main():
    print(f"ROOT do projeto: {ROOT}")
    print(f"TMP do fuzzer:   {TMP}")
    print()

    csv_failures = fuzz_exportar_csv()
    shot_failures = fuzz_shot()

    print()
    print("=" * 78)
    print("RESUMO DE FALHAS CONCRETAS")
    print("=" * 78)
    all_failures = csv_failures + shot_failures
    if not all_failures:
        print("Nenhuma falha concreta de path traversal / escrita arbitria confirmada.")
    else:
        for i, fl in enumerate(all_failures, 1):
            print(f"\n[{i}] {fl['label']}")
            print(f"    input (path/nome): {fl.get('path')!r}")
            print(f"    resolved:         {fl.get('resolved')}")
            if "within_tmp" in fl:
                print(f"    dentro de TMP:    {fl.get('within_tmp')}")
            if "within_shots" in fl:
                print(f"    dentro de SHOTS:  {fl.get('within_shots')}")
            print(f"    trace:            {fl.get('trace')}")

    # Limpeza final
    try:
        shutil.rmtree(TMP, ignore_errors=True)
    except Exception:
        pass

    # escreve relatorio em arquivo
    report_path = os.path.join(ROOT, "FUZZER_PATH_TRAVERSAL_REPORT.txt")
    with open(report_path, "w", encoding="utf-8") as rep:
        rep.write("RELATORIO DE FUZZER DE PATH TRAVERSAL / ESCRITA ARBITRARIA\n")
        rep.write("=" * 70 + "\n\n")
        rep.write(f"Alvos: controle_suprimentos.AbaRelatorios.exportar_csv, shot.main\n")
        rep.write(f"Total de falhas concretas: {len(all_failures)}\n\n")
        for i, fl in enumerate(all_failures, 1):
            rep.write(f"[{i}] {fl['label']}\n")
            rep.write(f"    input:    {fl.get('path')!r}\n")
            rep.write(f"    resolved: {fl.get('resolved')}\n")
            if "within_tmp" in fl:
                rep.write(f"    dentro de TMP:   {fl.get('within_tmp')}\n")
            if "within_shots" in fl:
                rep.write(f"    dentro de SHOTS: {fl.get('within_shots')}\n")
            rep.write(f"    trace: {fl.get('trace')}\n\n")
    print(f"\nRelatorio escrito em: {report_path}")
    return all_failures


if __name__ == "__main__":
    main()
