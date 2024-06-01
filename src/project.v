/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

`include "./vga.v"

module tt_um_spacecat_chan_john_pong_the_second (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  sphn_vga_top meow(
    .o_r(uo_out[2:0]),
    .o_g(uo_out[5:3]),
    .o_b(uio_out[2:0]),
    .o_hsync(uo_out[6]),
    .o_vsync(uo_out[7]),
    .i_move_up(ui_in[0]),
    .i_move_down(ui_in[1]),
    .i_player_two_up([ui_in[2]]),
    .i_player_two_down([ui_in[3]]),
    .i_player_two_active([ui_in[4]]),
    .pix_clk(clk),
    .pix_rst(~rst_n)
  );

  // All output pins must be assigned. If not used, assign to 0.
  assign uio_oe[0] = 1;
  assign uio_oe[1] = 1;
  assign uio_oe[2] = 1;
  assign uio_oe[7:3] = 0;
  assign uio_out[7:3]  = 0;

  // List all unused inputs to prevent warnings
  wire _unused = &{ui_in, uio_in, ena, 1'b0};

endmodule
