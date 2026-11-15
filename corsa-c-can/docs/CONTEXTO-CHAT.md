# Contexto para continuar noutro chat (atualizado 2026-11-15)

Responder sempre em **pt-pt**.

## Objetivo do utilizador
Ferramenta **genérica, para qualquer carro**, para descodificar CAN bus / K-line e fazer **diagnóstico próprio** (ler/apagar DTCs, dados em tempo real) em alternativa a uma máquina Autel. O carro de referência é um **Opel Corsa C 2006 1.3 CDTI** (motor Z13DT, Multijet, ECU provavelmente Magneti Marelli).

## Repo
- **Repo oficial: https://github.com/tsb27dev/carcan** (GPL-3.0-or-later). Branch `main`, tag **`v0.1.0`** (commit `84f5291`), CI verde (pytest + ruff em Python 3.10–3.13).
- Local na sessão cloud: `/home/user/carcan` (pode já não existir). O Mac do utilizador: `/Users/tiagobastos/git`.
- Os repos antigos `corsa-c-can/` (dentro de `tsb27dev/diamondhands97`, branch `ccr-244dfc59-okq0hq`) são **descartáveis**; o nome `diamondhands97` não faz sentido para o projeto.
- Boas práticas já configuradas: Conventional Commits, SemVer, `CHANGELOG.md` (Keep a Changelog), `CONTRIBUTING.md`, templates de PR/issues, Dependabot (2 PRs abertos: `actions/checkout` 4→7 e `actions/setup-python` 5→7, CI verde, ainda por rever/fundir).
- Branch protection na `main`: o utilizador estava a criar a regra (sugerido: nome `protect-main`, exigir PR + check `test`, histórico linear, approvals = 0).

## Estrutura do código (`carcan/`)
`logparse.py` (candump -L/-ta, CSV) · `analyze.py` (stats, contadores, diff, correlação) · `signals.py` (JSON → decode/.dbc) · `obd.py` (PIDs Mode 01) · `dtc.py` · `diag.py` (`CanLink` ISO-TP, `KLineLink` ISO 14230/9141) · `cli.py`.
Perfis por veículo em `profiles/<marca>-<modelo>-<ano>-<motor>/` (primeiro: Opel Corsa C, **sem sinais confirmados**, só placeholder).
Comando: `carcan stats|diff|correlate|decode|obd-csv|dbc|obd-scan|diag`.

## Limites / honestidade
- **Nada foi testado em carro real.** 8 testes com dados sintéticos. O caminho **K-line** é o menos fiável (init fast/slow por validar em hardware).
- **Protocolo do Corsa por confirmar**: o Corsa C pode ter só K-line (pino 7) na ficha OBD. A Autel funciona no carro, mas o protocolo não foi registado (ver "Protocolo" no ecrã do scanner, ou medir ~60 Ω entre pinos 6 e 14).
- `diag` só faz OBD-II **genérico** (motor). ABS/airbag/painel exigem serviços proprietários (a descobrir por captura).
- Decisão: **não implementar flash/remap de ECU** (risco de brickar, seed/key, checksums, implicações legais/emissões).
- `diag clear` pede confirmação e avisa que repõe monitores de prontidão.
- Esta sessão **não consegue criar repos** nem fazer push para `main`/tags (403): só para o branch da sessão. A `main` e a tag foram criadas via API/UI pelo utilizador.

## Hardware
- **CAN:** CANable 2.0 (candleLight/gs_usb, ~25–40 €) ou Raspberry Pi + MCP2515. Evitar ELM327 baratos para sniffing. Primeira captura sempre em **listen-only**.
- **K-line:** cabo FTDI K-line (~10 €). O Pi com MCP2515 **não** serve para K-line.

## Próximos passos
1. Confirmar protocolo na Autel (CAN vs K-line) e comprar o adaptador certo.
2. `carcan diag dtc --link can|kline` e partilhar resultado/erro para afinar o código.
3. Se houver CAN: capturas de `docs/02-workflow-reverse-engineering.md` (idle, luzes, piscas, travão, rpm) → `stats`, `diff`, `correlate` → preencher `profiles/opel-corsa-c-2006-1.3-cdti/signals.json`.
4. Rever/fundir os PRs do Dependabot; ativar branch protection.
5. Releases futuras: atualizar `CHANGELOG.md` e versão (`pyproject.toml` + `carcan/__init__.py`), commit `chore(release): X.Y.Z`, tag anotada.

## Comandos úteis
```bash
git clone https://github.com/tsb27dev/carcan.git && cd carcan
pip install -e .[dev,live,kline] && pytest && ruff check .
carcan stats logs/idle.log
carcan diag dtc --link kline --port /dev/ttyUSB0 --init fast
```
