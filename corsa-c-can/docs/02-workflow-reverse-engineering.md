# 2. Workflow de descodificação

```bash
pip install -e .[dev]            # + [live] se quiseres obd-scan
sudo scripts/probe_bitrate.sh can0
sudo scripts/setup_socketcan.sh can0 500000
candump -L can0 > logs/idle.log   # ignição ON, motor desligado, ~30 s
```

## Passo 1 — Inventário
`corsacan stats logs/idle.log` mostra por ID: período, DLC, bytes constantes, **contadores** (bytes que fazem +1 — não são dados, são alive counters) e bytes variáveis.

## Passo 2 — Capturas "uma coisa de cada vez"
Faz uma captura para cada acção isolada (30 s cada) e compara:

| Acção | Captura |
|-------|---------|
| Ignição ON, nada a mexer | `idle.log` |
| Luzes mínimos / médios / máximos | `lights_off.log`, `lights_on.log` |
| Pisca esq./dir., quatro piscas | … |
| Vidros, fecho central, porta aberta | … |
| Travão pressionado | `brake_on.log` |
| Motor ligado ao ralenti | `idle_engine.log` |
| Acelerar em ponto morto (rpm 1000→3000→1000) | `rev.log` |

`corsacan diff logs/lights_off.log logs/lights_on.log` → lista os bits estáveis que mudaram (byte.bit 0→1).

## Passo 3 — Sinais analógicos (RPM, velocidade, temperatura)
Usa o OBD-II como referência, se o carro responder em CAN:
```bash
# num terminal: captura tudo
candump -L can0 > logs/drive.log
# noutro: pergunta RPM por OBD (e grava no mesmo log, IDs 0x7DF/0x7E8)
cansend can0 7DF#02010C0000000000   # repetir (ex.: while true; do ...; sleep 0.1; done)
corsacan obd-csv logs/drive.log 0x0C > logs/rpm_ref.csv
corsacan correlate logs/drive.log logs/rpm_ref.csv
```
O topo da lista (`|r|` ≈ 1.0) indica o ID e os bytes (u16 big/little endian) onde está o RPM.
Depois ajusta `factor`/`offset` por regressão linear (RPM = raw × 0.25 é típico).

## Passo 4 — Registar e usar
Escreve os sinais em `signals/corsa_c.json`:
```bash
corsacan decode logs/drive.log signals/corsa_c.json
corsacan dbc signals/corsa_c.json > corsa_c.dbc   # abrir em SavvyCAN / Wireshark / cantools
```
Podes também abrir os logs em **SavvyCAN** (`candump -L` é suportado) para ver gráficos.

## Dicas
* Cluster/ECU normalmente enviam 10–100 Hz; IDs com período irregular são eventos (botões).
* Bytes com checksum: últimos bytes que variam "aleatoriamente" mas dependem dos outros — ignora-os ao mapear.
* Valores em 2 bytes: testa sempre big **e** little endian; e 10/12 bits em vez de 16.
