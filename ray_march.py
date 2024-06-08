from math import atan2, radians
from typing import List
from amaranth import *

class Top(Elaboratable):
    def __init__(self, x_res, y_res):
        self.o_r = Signal(3)
        self.o_g = Signal(3)
        self.o_b = Signal(3)
        self.o_hsync = Signal()
        self.o_vsync = Signal()

        self.x_res = x_res
        self.y_res = y_res
    
    def elaborate(self, platform):
        m = Module()

        m.submodules.pixels = pixels = PixelBlock(self.x_res, self.y_res)
        m.submodules.cordic = cordic = Cordic()
        m.submodules.vga = vga = VGAOutput(pixels, 16, 96, 48, 10, 2, 33)

        prev_vsync = Signal()
        m.d.pix += prev_vsync.eq(vga.o_vsync)

        x_counter = Signal(range(self.x_res))
        y_counter = Signal(range(self.y_res))

        # 3.16
        time_counter = Signal(19)

        with m.FSM(domain="pix"):
            with m.State("vsync"):
                with m.If(prev_vsync & ~vga.o_vsync):
                    m.next = "start_sin"
                    m.d.pix += [
                        x_counter.eq(0),
                        y_counter.eq(0),
                        time_counter.eq(time_counter + int(radians(90 / 60) * 2**16)) # 90 degrees per second
                    ]

            with m.State("start_sin"):
                next_time_counter = Signal(19)
                m.d.comb += next_time_counter.eq(time_counter)
                with m.If(time_counter > int(radians(360) * 2**16)):
                    m.d.comb += next_time_counter.eq(time_counter - int(radians(360) * 2**16))
                    m.d.pix += time_counter.eq(next_time_counter)
                
                x_factor = int((radians(180) * 2**16)/self.x_res)
                y_factor = int((radians(180) * 2**16)/self.y_res)

                angle = next_time_counter + x_counter * x_factor + y_counter * y_factor
                final_angle = Mux(angle > int(radians(360) * 2**16), angle - int(radians(360) * 2**16), angle)
                m.d.comb += cordic.i_value.eq(final_angle)
                m.d.comb += cordic.i_start.eq(1)
                m.next = "sin_wait"
            
            with m.State("sin_wait"):
                with m.If(cordic.o_done):
                    m.d.pix += [
                        pixels.i_write_val.eq(Cat((((cordic.o_cos >> 1) + 2**15).as_unsigned() >> 14)[0:3], C(0, 3), (((cordic.o_sin >> 1) + 2**15).as_unsigned() >> 14)[0:3])),
                        pixels.i_write.eq(1),
                        pixels.i_wx.eq(x_counter),
                        pixels.i_wy.eq(y_counter),
                    ]
                    m.d.pix += x_counter.eq(x_counter + 1)
                    m.next = "start_sin"
                    with m.If(x_counter == self.x_res - 1):
                        m.d.pix += x_counter.eq(0)
                        m.d.pix += y_counter.eq(y_counter + 1)
                        with m.If(y_counter == self.y_res - 1):
                            m.d.pix += y_counter.eq(0)
                            m.next = "vsync"

        m.d.comb += [
            self.o_r.eq(vga.o_r),
            self.o_g.eq(vga.o_g),
            self.o_b.eq(vga.o_b),
            self.o_hsync.eq(vga.o_hsync),
            self.o_vsync.eq(vga.o_vsync),
            vga.i_enable.eq(1),
        ]

        return m

class Cordic(Elaboratable):
    def __init__(self):
        # 3.16 precision
        self.i_value = Signal(19)
        self.i_start = Signal()

        # signed 1.16 precision
        self.o_cos = Signal(signed(18))
        self.o_sin = Signal(signed(18))
        self.o_done = Signal()
    
    def elaborate(self, platform):
        m = Module()
    
        intermediate = Signal(19)

        sin_pos = Signal()
        cos_pos = Signal()

        theta = Signal(signed(20))
        x = Signal(19)
        y = Signal(signed(20))
        iters = Signal(range(20))

        atan_lut = [atan2(1, 2**i) for i in range(20)]
        print(atan_lut, sum(atan_lut))

        with m.FSM(domain="pix"):
            with m.State("waiting"):
                with m.If(self.i_start):
                    with m.If(self.i_value > int(radians(180) * 2**16)):
                        m.d.pix += sin_pos.eq(0)
                    with m.Else():
                        m.d.pix += sin_pos.eq(1)
                    post_sin_fix = Mux(self.i_value >= int(radians(180) * 2**16), int(radians(360) * 2**16) - self.i_value, self.i_value)
                    with m.If(post_sin_fix > int(radians(90) * 2**16)):
                        m.d.pix += cos_pos.eq(0)
                    with m.Else():
                        m.d.pix += cos_pos.eq(1)
                    final_fixed = Mux(post_sin_fix >= int(radians(90) * 2**16), int(radians(180) * 2**16) - post_sin_fix, post_sin_fix)
                    m.d.pix += [
                        intermediate.eq(final_fixed << 2),
                        x.eq(0x40000),
                        y.eq(0),
                        iters.eq(0),
                        theta.eq(0)
                    ]
                    m.next = "calc"
            
            with m.State("calc"):
                sigma = Signal(signed(2))
                m.d.comb += sigma.eq(Mux(theta < intermediate, 1, -1))
                lut_val = Signal(18)
                for i in range(20):
                    with m.If(iters == i):
                        m.d.comb += lut_val.eq(int(atan_lut[i] * 2**18))
                m.d.pix += [
                    theta.eq(theta + sigma * lut_val),
                    x.eq(x - ((sigma * y) >> iters)),
                    y.eq(y + ((sigma * x) >> iters)),
                    iters.eq(iters + 1)
                ]
                with m.If(iters == 19):
                    m.d.comb += self.o_cos.eq(((x * 155) >> 10) * Mux(cos_pos, 1, -1))
                    m.d.comb += self.o_sin.eq(((y * 155) >> 10) * Mux(sin_pos, 1, -1))
                    m.d.comb += self.o_done.eq(1)
                    m.next = "waiting"

        return m


class PixelBlock(Elaboratable):
    def __init__(self, x_res, y_res):
        self.i_x = Signal(range(x_res))
        self.i_y = Signal(range(y_res))
        self.i_write = Signal()
        self.i_wx = Signal(range(x_res))
        self.i_wy = Signal(range(y_res))
        self.i_write_val = Signal(9)

        self.o_val = Signal(9)

        self.pixels = [[Signal(9) for _ in range(y_res)] for _ in range(x_res)]
        self.x_res = x_res
        self.y_res = y_res

    def elaborate(self, platform):
        m = Module()

        with m.If(self.i_write):
            for x in range(self.x_res):
                with m.If(self.i_wx == x):
                    for y in range(self.y_res):
                        with m.If(self.i_wy == y):
                            m.d.pix += self.pixels[x][y].eq(self.i_write_val)

        with m.Switch(self.i_x):
            for x in range(self.x_res):
                with m.Case(x):
                    intermediate = Signal(9)
                    m.d.pix += self.o_val.eq(intermediate)
                    with m.Switch(self.i_y):
                        for y in range(self.y_res):
                            with m.Case(y):
                                m.d.comb += intermediate.eq(self.pixels[x][y])

        return m

class VGAOutput(Elaboratable):
    def __init__(self, pixels: PixelBlock, hfront, hsync, hback, vfront, vsync, vback):
        self._hfront = hfront
        self._hsync = hsync
        self._hback = hback
        self._vfront = vfront
        self._vsync = vsync
        self._vback = vback

        self.pixels = pixels

        self.i_enable = Signal()

        self.o_r = Signal(3)
        self.o_g = Signal(3)
        self.o_b = Signal(3)
        self.o_hsync = Signal()
        self.o_vsync = Signal()
    
    def elaborate(self, platform):
        m = Module()

        line_length = 640 + self._hfront + self._hsync + self._hback
        screen_length = 480 + self._vfront + self._vsync + self._vback

        clock = Signal(22)
        with m.If(self.i_enable):
            m.d.pix += clock[0:11].eq(clock[0:11] + 1)
        with m.If(clock[0:11] == line_length - 1):
            m.d.pix += [
                clock[0:11].eq(0),
                clock[11:22].eq(clock[11:22] + 1)
            ]
            with m.If(clock[11:22] == screen_length - 1):
                m.d.pix += clock[11:22].eq(0)
        
        for x in range(self.pixels.x_res):
            with m.If(clock[0:11] > ((640 * x) // self.pixels.x_res)):
                m.d.comb += self.pixels.i_x.eq(x)
        for y in range(self.pixels.y_res):
            with m.If(clock[11:22] > ((480 * y) // self.pixels.y_res)):
                m.d.comb += self.pixels.i_y.eq(y)

        m.d.comb += Cat(self.o_r, self.o_g, self.o_b).eq(self.pixels.o_val)

        m.d.comb += [
            self.o_hsync.eq(1),
            self.o_vsync.eq(1),
        ]

        with m.If((clock[0:11] >= 640) | (clock[11:22] >= 480)):
            m.d.comb += [
                self.o_r.eq(0),
                self.o_g.eq(0),
                self.o_b.eq(0),
            ]
        with m.If((clock[0:11] >= 640 + self._hfront) & (clock[0:11] < line_length - self._hback)):
            m.d.comb += self.o_hsync.eq(0)
        with m.If((clock[11:22] >= 480 + self._vfront) & (clock[11:22] < screen_length - self._vback)):
            m.d.comb += self.o_vsync.eq(0)

        return m



if __name__ == "__main__":
    from amaranth.sim import *
    from amaranth.back.verilog import convert

    mod = Top(4,4)

    def test():
        for _ in range(420010 * 2):
            yield

        print("done")


    sim = Simulator(mod)
    sim.add_clock(2e-12, domain="pix")
    sim.add_sync_process(test, domain="pix")

    with sim.write_vcd("test.vcd", "test.gtkw"):
        sim.run()

    print("hii")

