<!---
This file is used to generate the project datasheet.
-->

## How it works

This is the project's first physical-flow milestone: a hardwired UART transmitter (8 data bits, no parity, 1 stop bit, LSB first) used to prove the RTL-to-GDS flow at 8x4 tiles. It is a temporary design. The goal of the project is a reprogrammable protocol engine that runs UART, SPI and I2C from loaded programs; that engine is not implemented yet.

The transmitter is a four-state machine (IDLE, START, DATA, STOP) with a cycle counter that holds each bit for 521 clock cycles (60 MHz / 521 = 115,163 baud). The `send` input is passed through two flip-flops before use because it is asynchronous to the clock. A new frame starts only on a rising edge of `send` while idle, so holding `send` high sends one frame, not many.

## How to test

Apply a byte on `ui[7:0]`, then raise `uio[0]` (send) for at least 3 clock cycles. `uo[0]` (tx) emits one frame; `uo[1]` (busy) is high until the stop bit ends. Reset with `rst_n` low for several cycles before use.

The cocotb tests in `test/` decode `tx` with a receiver that is independent of the RTL. Run them with `cd test && make -B`.

## External hardware

A 3.3 V UART receiver (for example a USB-serial adapter) on `uo[0]`, if you want to see the output outside simulation.
