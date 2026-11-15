# SPDX-License-Identifier: Apache-2.0
# Phase 0 testbench: hardwired UART TX (8N1).
# The receiver below is independent of the RTL: it only watches the tx pin
# and samples at mid-bit, as a real UART receiver would.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

CPB = 521  # clock cycles per bit; must match CLKS_PER_BIT in src/project.v


def tx(dut):
    return int(dut.uo_out.value) & 1


def busy(dut):
    return (int(dut.uo_out.value) >> 1) & 1


async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, 16666, unit="ps").start())  # ~60 MHz
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


async def pulse_send(dut, byte, cycles=3):
    dut.ui_in.value = byte
    dut.uio_in.value = 1
    await ClockCycles(dut.clk, cycles)
    dut.uio_in.value = 0


async def receive_byte(dut, timeout_bits=20):
    """Wait for a start bit, sample each bit at mid-bit, return (byte, start_low_cycles)."""
    for _ in range(timeout_bits * CPB):
        await FallingEdge(dut.clk)
        if tx(dut) == 0:
            break
    else:
        raise AssertionError("no start bit seen")
    await ClockCycles(dut.clk, CPB // 2, rising=False)
    assert tx(dut) == 0, "start bit not low at mid-bit"
    value = 0
    for k in range(8):
        await ClockCycles(dut.clk, CPB, rising=False)
        value |= tx(dut) << k  # LSB first
    await ClockCycles(dut.clk, CPB, rising=False)
    assert tx(dut) == 1, "stop bit not high at mid-bit"
    return value


@cocotb.test()
async def test_idle_high_after_reset(dut):
    await reset(dut)
    for _ in range(3 * CPB):
        await FallingEdge(dut.clk)
        assert tx(dut) == 1, "tx must idle high"
        assert busy(dut) == 0
    dut._log.info("tx stays high and busy stays low with no send")


@cocotb.test()
async def test_bytes_roundtrip(dut):
    await reset(dut)
    for byte in (0x41, 0x00, 0xFF, 0x55, 0xA5, 0x01, 0x80):
        rx = cocotb.start_soon(receive_byte(dut))
        await pulse_send(dut, byte)
        got = await rx
        assert got == byte, f"sent 0x{byte:02X}, received 0x{got:02X}"
        dut._log.info(f"0x{byte:02X} ok")
        await ClockCycles(dut.clk, 2 * CPB)  # let the frame finish


@cocotb.test()
async def test_start_bit_duration_and_busy(dut):
    """0x41 has b0=1, so the start bit is the only low period: exactly CPB cycles."""
    await reset(dut)
    await pulse_send(dut, 0x41)
    low = 0
    saw_busy = False
    while True:
        await FallingEdge(dut.clk)
        if busy(dut):
            saw_busy = True
        if tx(dut) == 0:
            low += 1
        elif low:
            break
    assert saw_busy, "busy never went high"
    assert low == CPB, f"start bit lasted {low} cycles, expected {CPB}"
    # After the frame (10 bit times from start) busy must drop.
    await ClockCycles(dut.clk, 9 * CPB + 10, rising=False)
    assert busy(dut) == 0, "busy still high after the frame"


@cocotb.test()
async def test_held_send_sends_one_frame(dut):
    """Holding send high for the whole frame must not retrigger a second frame."""
    await reset(dut)
    rx = cocotb.start_soon(receive_byte(dut))
    dut.ui_in.value = 0x41
    dut.uio_in.value = 1
    got = await rx
    assert got == 0x41
    await ClockCycles(dut.clk, 3 * CPB)  # send is still high
    assert tx(dut) == 1 and busy(dut) == 0, "a second frame started while send stayed high"
    dut.uio_in.value = 0


@cocotb.test()
async def test_send_ignored_while_busy(dut):
    """A new rising edge on send during a frame is ignored and does not corrupt it."""
    await reset(dut)
    rx = cocotb.start_soon(receive_byte(dut))
    await pulse_send(dut, 0x41)
    await ClockCycles(dut.clk, 3 * CPB)
    dut.ui_in.value = 0xFF  # change data mid-frame, then pulse send
    await pulse_send(dut, 0xFF)
    got = await rx
    assert got == 0x41, f"frame corrupted: got 0x{got:02X}"
