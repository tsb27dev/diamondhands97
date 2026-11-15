# Contexto para continuar noutro chat

## Objetivo do utilizador
Descodificar o CAN bus do **Opel Corsa C 2006 1.3 CDTI** (motor Z13DT, Multijet/Magneti Marelli) e ter uma **alternativa própria a uma máquina de diagnóstico Autel** (ler/apagar DTCs, dados em tempo real). Responder sempre em **pt-pt**.

## Estado atual
- Projeto Python em `corsa-c-can/` (repo `tsb27dev/diamondhands97`, branch `ccr-244dfc59-okq0hq`). Não foi possível criar repo novo no GitHub a partir da sessão; a pasta pode ser movida (`git subtree split -P corsa-c-can`).
- **Ainda não há sinais reais descodificados**: não há logs do carro. 7 testes passam, só com dados sintéticos.
- Nenhum PR criado (não foi pedido).

## O que existe no código (`corsacan/`)
| Módulo | Função |
|---|---|
| `logparse.py` | lê `candump -L`, `candump -ta` e CSV |
| `analyze.py` | stats por ID, deteção de contadores, `diff` de capturas, correlação com sinal de referência (ex.: RPM OBD) |
| `signals.py` | sinais em JSON (convenção de bits DBC), decode, export `.dbc` |
| `obd.py` | PIDs Mode 01, `decode_payload`, `scan` ao vivo |
| `dtc.py` | descodificação de DTCs (P/C/B/U) |
| `diag.py` | `CanLink` (ISO-TP) e `KLineLink` (ISO 14230 fast / ISO 9141 slow); ler/apagar DTC, PIDs live, VIN |
| `cli.py` | comandos: `stats diff correlate decode obd-csv dbc obd-scan diag` |

Scripts: `scripts/setup_socketcan.sh` (listen-only), `scripts/probe_bitrate.sh`. Docs: `docs/01-hardware-e-bus.md`, `docs/02-workflow-reverse-engineering.md`.

## Limites conhecidos / honestidade
- **Não se sabe se o Corsa C tem CAN na ficha OBD** (pinos 6/14). Pode ser só **K-line** (pino 7). Verificar: na Autel, ver "Protocolo" (ISO 15765 = CAN; ISO 14230/9141 = K-line) ou medir ~60 Ω entre pinos 6 e 14.
- O caminho **K-line nunca foi testado em hardware** (só frames simulados). O init (fast/slow) é o ponto mais provável de precisar de ajuste. Nota: o byte de formato KWP para endereço funcional 0x33 é `0xC0|len` (frame canónico `C1 33 F1 81 66`).
- `diag` só faz **OBD-II genérico** (ECU motor). ABS/airbag/painel e códigos Opel específicos exigem serviços proprietários (a descobrir por captura).
- Decisão tomada: **não implementar flash/remap de ECU** (risco de brickar, seed/key, checksums, implicações legais/emissões). Se o utilizador quiser afinar, indicar preparador com bancada.
- Clear DTC pede confirmação e avisa que repõe monitores de prontidão.

## Hardware recomendado (conforme protocolo)
- **CAN:** CANable 2.0 (firmware candleLight/gs_usb, ~25–40 €); alternativa Raspberry Pi + MCP2515. Não usar ELM327 barato para sniffing.
- **K-line:** cabo FTDI K-line (~10 €). O Pi com MCP2515 **não serve** para K-line.
- Primeira captura sempre em **listen-only**.

## Próximos passos
1. Utilizador confirma o protocolo na Autel (CAN vs K-line) e compra o adaptador certo.
2. `corsacan diag dtc --link can|kline` e partilhar resultado/erro para afinar o código.
3. Se houver CAN: fazer as capturas de `docs/02-...` (idle, luzes, piscas, travão, rpm) e correr `stats`, `diff`, `correlate`; preencher `signals/corsa_c.json`.
4. Mandar os `.log` para o assistente descodificar sinais.

## Comandos úteis
```bash
pip install -e .[dev,live,kline] && pytest
corsacan stats logs/idle.log
corsacan diff logs/lights_off.log logs/lights_on.log
corsacan correlate logs/drive.log logs/rpm_ref.csv
corsacan diag dtc --link kline --port /dev/ttyUSB0 --init fast
```
