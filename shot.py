#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tira screenshots de todas as paginas do app Flask."""
import asyncio
import os
from playwright.async_api import async_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "screenshots")
os.makedirs(SHOTS, exist_ok=True)

PAGINAS = [
    ("dashboard", "/"),
    ("entrada", "/entrada"),
    ("despacho", "/despacho"),
    ("estoque", "/estoque"),
    ("relatorios", "/relatorios"),
    ("cadastros", "/cadastros"),
]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        for nome, rota in PAGINAS:
            await page.goto(f"http://localhost:5000{rota}")
            await page.wait_for_timeout(800)  # deixa JS/tailwind/icones carregarem
            path = os.path.join(SHOTS, f"{nome}.png")
            await page.screenshot(path=path, full_page=True)
            print(f"  [{nome}] -> {path}")
        await browser.close()


asyncio.run(main())