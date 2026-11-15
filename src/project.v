/*
 * SPDX-License-Identifier: Apache-2.0
 *
 * Phase 0 flow-bring-up design: a hardwired UART transmitter (8N1).
 * This is a temporary exercise to prove the RTL-to-GDS flow, not the
 * final programmable engine.
 *
 * Pins:
 *   ui_in[7:0]   byte to send (sampled when a send starts)
 *   uio_in[0]    send: a rising edge starts a frame if the transmitter is idle
 *   uo_out[0]    tx   (idle high)
 *   uo_out[1]    busy (high from the start of a frame until the stop bit ends)
 */

`default_nettype none

module tt_um_sds_protocol_engine (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // 60 MHz / 521 = 115,163 baud (0.04% from 115,200).
  localparam integer CLKS_PER_BIT = 521;
  localparam [9:0] LAST_CNT = 10'(CLKS_PER_BIT - 1);

  localparam [1:0] IDLE = 2'd0, START = 2'd1, DATA = 2'd2, STOP = 2'd3;

  // The send input is asynchronous to clk: pass it through two flops
  // before using it, then detect its rising edge.
  reg send_s1, send_s2, send_s3;
  wire send_rise = send_s2 & ~send_s3;

  reg [1:0] state;
  reg [7:0] sh;      // byte being sent, shifted right once per bit
  reg [2:0] bitidx;  // which data bit is being sent (0..7)
  reg [9:0] cnt;     // clock cycles elapsed within the current bit

  wire tick = (cnt == LAST_CNT);

  // Moore output: the pin depends only on state (and sh[0] while in DATA).
  assign uo_out[0] = (state == START) ? 1'b0 : (state == DATA) ? sh[0] : 1'b1;
  assign uo_out[1] = (state != IDLE);
  assign uo_out[7:2] = 6'b0;
  assign uio_out = 8'b0;
  assign uio_oe  = 8'b0;  // all bidirectional pins are inputs

  always @(posedge clk) begin
    if (!rst_n) begin
      state  <= IDLE;
      send_s1 <= 1'b0;
      send_s2 <= 1'b0;
      send_s3 <= 1'b0;
    end else begin
      send_s1 <= uio_in[0];
      send_s2 <= send_s1;
      send_s3 <= send_s2;

      case (state)
        IDLE: if (send_rise) begin
          sh     <= ui_in;
          bitidx <= 3'd0;
          cnt    <= 10'd0;
          state  <= START;
        end
        START: begin
          cnt <= tick ? 10'd0 : cnt + 10'd1;
          if (tick) state <= DATA;
        end
        DATA: begin
          cnt <= tick ? 10'd0 : cnt + 10'd1;
          if (tick) begin
            sh <= {1'b0, sh[7:1]};
            if (bitidx == 3'd7) state <= STOP;
            else bitidx <= bitidx + 3'd1;
          end
        end
        STOP: begin
          cnt <= tick ? 10'd0 : cnt + 10'd1;
          if (tick) state <= IDLE;
        end
      endcase
    end
  end

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, uio_in[7:1], 1'b0};

endmodule
