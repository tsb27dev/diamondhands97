# 1. Hardware e que bus existe realmente

## Aviso importante (verificar antes de comprar/ligar nada)
O Corsa C (2000–2006) é de uma geração de transição. Dependendo da versão/ECU,
o diagnóstico OBD pode ser só **K-line (ISO 9141/14230, pino 7)** e **não ter CAN
na ficha OBD**. O 1.3 CDTI (Z13DT, Multijet/Marelli) é motor de origem Fiat; em
muitos exemplares há CAN entre ECU/ABS/painel, mas **não assumas** que está nos
pinos 6/14 da ficha OBD.

Verifica **com o carro desligado**, multímetro na ficha OBD-II (16 pinos, vista do lado do condutor):

| Pino | Função | O que procurar |
|------|--------|----------------|
| 4/5  | massas | ~0 Ω à carroçaria |
| 16   | +12 V permanente | 12 V |
| 6    | CAN-H  | pino com ligação no conector? ~2,5 V com ignição ligada |
| 14   | CAN-L  | idem; ~120 Ω entre 6 e 14 (duas terminações de 60 Ω) = CAN HS presente |
| 7    | K-line | ~12 V com ignição ligada (sem comunicação) |

* **Pinos 6/14 sem cobre / sem 60 Ω → não há CAN na OBD.** Opções: ler K-line
  (ELM327/FTDI + KWP2000 — fora do âmbito deste repo por agora) ou ligar-se directamente
  aos fios CAN atrás do painel/ECU (par entrançado), com muito cuidado.
* Se houver CAN, o débito mais provável é **500 kbit/s**; usa `scripts/probe_bitrate.sh`.

## Material
* Adaptador USB-CAN com SocketCAN: CANable/candleLight (gs_usb), PEAK PCAN-USB, ou Raspberry Pi + MCP2515.
  (ELM327 baratos **não servem** para sniffing contínuo.)
* Cabo/adaptador OBD-II → DB9 ou fios (pino 6 = CAN-H, 14 = CAN-L, 4 = GND).

## Segurança
* Primeira captura **sempre em listen-only** (`scripts/setup_socketcan.sh`) — não transmite nada para o bus.
* Nunca envies tramas com o carro em andamento nem para ABS/airbag/ECU sem saberes o que fazem.
* Não desligues a bateria nem uses a ficha OBD durante testes de airbag.
