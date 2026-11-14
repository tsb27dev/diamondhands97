# corsa-c-can

Toolkit (Python, sem dependências obrigatórias) para **capturar, analisar e descodificar o CAN bus de um Opel Corsa C (2006) 1.3 CDTI**.

> Estado: ferramentas prontas e testadas com dados sintéticos. **Ainda não há sinais reais descodificados** — para isso é preciso capturar logs do teu carro (ver `docs/`).
> ⚠️ O Corsa C pode **não ter CAN na ficha OBD** (só K-line). Lê `docs/01-hardware-e-bus.md` primeiro.

## Instalação
```bash
pip install -e .[dev]     # [live] para obd-scan com python-can
pytest
```

## Comandos
| Comando | O que faz |
|---|---|
| `corsacan stats LOG` | período, contadores, bytes constantes/variáveis por ID |
| `corsacan diff A B` | bits que mudam entre duas capturas (botões, luzes…) |
| `corsacan correlate LOG REF.csv` | encontra bytes que seguem um sinal de referência (RPM por OBD) |
| `corsacan obd-csv LOG PID` | extrai um PID OBD-II de um log para CSV |
| `corsacan decode LOG signals.json` | aplica definições de sinais |
| `corsacan dbc signals.json` | exporta `.dbc` |
| `corsacan obd-scan` | consulta PIDs ao vivo (opcional) |

Demo com dados sintéticos:
```bash
python -m tests.make_demo_log logs/demo.log logs/demo_rpm.csv
corsacan stats logs/demo.log
corsacan correlate logs/demo.log logs/demo_rpm.csv
```

## Estrutura
`corsacan/` código · `scripts/` SocketCAN e deteção de bitrate · `docs/` hardware + workflow · `signals/` definições JSON · `logs/` as tuas capturas (ignoradas pelo git)

## Diagnóstico próprio (alternativa a uma Autel)
```bash
corsacan diag dtc    --link can                 # ler códigos (Mode 03); também: pending, permanent
corsacan diag clear  --link can                 # mostra os códigos e pede confirmação antes de apagar
corsacan diag live   --link can --pids 0x0C,0x0D,0x05
corsacan diag vin    --link can
# K-line (cabo FTDI):  pip install -e .[kline]
corsacan diag dtc --link kline --port /dev/ttyUSB0 --init fast   # ou --init slow (ISO 9141)
```
Limites: só OBD-II **genérico** (ECU do motor). ABS, airbag, painel e códigos específicos Opel precisam de serviços proprietários (KWP/UDS) que teriam de ser descobertos por captura. O caminho K-line está testado só com frames simulados, **não em hardware real**.
