# NINA UART startup

Once radio power, hardware reset and crystal startup are complete, configure
the SC16 and begin the startup state machine. The SC16 configuration clears
its hardware and software queues. Continue polling it during the startup
drain, which discards confirmed software RX bytes and waits for a 60 ms quiet
window. The state machine then sends `AT` and expects a verbose `OK`. It sends
`AT+UMRS?` and requires a UART-settings record with the five fields
`115200,1,8,1,1`, followed by `OK`. This verifies 115200 baud, CTS/RTS, eight
data bits, one stop bit and no parity at the NINA. Commands use CR. The parser
accepts CR/LF framing and the matching command echo. It allows the stock
`+STARTUP` greeting while awaiting the first reply.
[u-blox u-connectXpress AT Commands Manual R56, §§2.2–2.3, 3.11 and 4.15](https://content.u-blox.com/sites/default/files/documents/u-connectXpress-ATCommands-Manual_UBX-14044127.pdf)

Each call uses software queues only, consuming at most 32 bytes. Drain,
enqueue and response phases each have a two-second deadline. A malformed or
unexpected reply, UART-setting mismatch, deadline or loss of bridge readiness
latches a startup failure. The caller owns disabling radio power, resetting
the startup state, stopping the SC16 and starting with fresh hardware on the
next attempt. Use a configured command-mode module with the documented CR and
verbose response settings. Source-power loss must stop the bridge and reset the
startup state. `READY` identifies the UART handshake only. BLE discovery,
pairing, link health and plug telemetry remain separate.

Run host and Cortex-M0+ checks from this directory.

```sh
make -f nina-startup.mk nina-startup-test nina-startup-compile
```

The quiet window and deadlines are candidate timings. Confirm power-up,
boot greeting, command responses and CTS/RTS on the received module with
the case scheduler and simultaneous ADS1115 and display activity.
