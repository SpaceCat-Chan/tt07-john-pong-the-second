from amaranth import *
from PIL import Image

class Top(Elaboratable):
    def __init__(self):
        self.o_r = Signal(3)
        self.o_g = Signal(3)
        self.o_b = Signal(3)
        self.o_hsync = Signal()
        self.o_vsync = Signal()

        self.i_move_up = Signal()
        self.i_move_down = Signal()

        self.i_player_two_up = Signal()
        self.i_player_two_down = Signal()
        self.i_player_two_active = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules.vga = self.vga = VGAOutput(16, 96, 48, 10, 2, 33)
        

        m.d.comb += self.vga.i_enable.eq(1)

        prev_vsync = Signal(1)
        m.d.pix += prev_vsync.eq(self.vga.o_vsync)

        pope_location = Signal(22, reset=((240 - 20) << 12) + (320 - 17)) # reset at (320-20),(240-17) which is the middle of the screen when accounting for the dimensions of the pope
        pope_h_velocity = Signal(1, reset=0)
        pope_v_velocity = Signal(signed(7), reset=-1)
        
        paddle_location = Signal(10, reset=240-75)
        enemy_paddle_location = Signal(10, reset=240-75)

        time_until_start = Signal(range(180), reset=179)

        player_score = Signal(3)
        enemy_score = Signal(3)


        lfsr = Signal(16, reset=1)
        m.d.pix += lfsr.eq(Cat(lfsr[10] ^ lfsr[12] ^ lfsr[13] ^ lfsr[15], lfsr[0:15]))


        with m.If(prev_vsync & ~self.vga.o_vsync): # we just entered vsync, do all logic now
            with m.If(time_until_start > 0):
                m.d.pix += time_until_start.eq(time_until_start - 1)
                m.d.pix += pope_v_velocity.eq(lfsr[0:4].as_signed())
            with m.Else():
                with m.If(pope_h_velocity):
                    m.d.pix += pope_location[0:10].eq(pope_location[0:10] + 3)
                with m.Else():
                    m.d.pix += pope_location[0:10].eq(pope_location[0:10] - 3)
                m.d.pix += pope_location[10:22].eq(pope_location[10:22] + 3 * pope_v_velocity)
                
                with m.If(pope_location[12:22] <= 20):
                    m.d.pix += pope_v_velocity.eq(Mux(pope_v_velocity > 0, pope_v_velocity, -pope_v_velocity))
                with m.If(pope_location[12:22] >= 480 - 40):
                    m.d.pix += pope_v_velocity.eq(Mux(pope_v_velocity < 0, pope_v_velocity, -pope_v_velocity))

                with m.If((pope_h_velocity == 0) & (pope_location[0:10] < 50) & ((pope_location[12:22] > paddle_location - 40) & (pope_location[12:22] <= paddle_location + 150))):
                    m.d.pix += [
                        pope_h_velocity.eq(1),
                        pope_v_velocity.eq(((pope_location[12:22] - paddle_location - 55) >> 3) + lfsr[0:3].as_signed())
                    ]
                    
                with m.If((pope_h_velocity == 1) & (pope_location[0:10] >= 640 - 50 - 34) & ((pope_location[12:22] > enemy_paddle_location - 40) & (pope_location[12:22] <= enemy_paddle_location + 150))):
                    m.d.pix += [
                        pope_h_velocity.eq(0),
                        pope_v_velocity.eq(((pope_location[12:22] - enemy_paddle_location - 55) >> 3) + lfsr[0:3].as_signed())
                    ]

                with m.If(self.i_move_up & (paddle_location >= 3)):
                    m.d.pix += paddle_location.eq(paddle_location - 3)
                with m.If(self.i_move_down & (paddle_location < (480-150-3))):
                    m.d.pix += paddle_location.eq(paddle_location + 3)

                with m.If((pope_location[12:22] > enemy_paddle_location + 75 - 20) & (enemy_paddle_location < 480-150-20) & (self.i_player_two_active == 0)):
                    m.d.pix += enemy_paddle_location.eq(enemy_paddle_location + 2)
                with m.If((pope_location[12:22] < enemy_paddle_location + 75 - 20) & (enemy_paddle_location > 20) & (self.i_player_two_active == 0)):
                    m.d.pix += enemy_paddle_location.eq(enemy_paddle_location - 2)

                with m.If(self.i_player_two_up & (enemy_paddle_location >= 3) & (self.i_player_two_active)):
                    m.d.pix += enemy_paddle_location.eq(enemy_paddle_location - 3)
                with m.If(self.i_player_two_down & (enemy_paddle_location < (480-150-3)) & (self.i_player_two_active)):
                    m.d.pix += enemy_paddle_location.eq(enemy_paddle_location + 3)

                with m.If(pope_location[0:10] <= 6):
                    m.d.pix += [
                        pope_location.eq(pope_location.reset),
                        pope_h_velocity.eq(pope_h_velocity.reset),
                        pope_v_velocity.eq(pope_v_velocity.reset),
                        paddle_location.eq(paddle_location.reset),
                        enemy_paddle_location.eq(enemy_paddle_location.reset),
                        time_until_start.eq(time_until_start.reset),
                        enemy_score.eq(enemy_score + 1),
                    ]
                with m.If(pope_location[0:10] >= 640 - 34):
                    m.d.pix += [
                        pope_location.eq(pope_location.reset),
                        pope_h_velocity.eq(pope_h_velocity.reset),
                        pope_v_velocity.eq(pope_v_velocity.reset),
                        paddle_location.eq(paddle_location.reset),
                        enemy_paddle_location.eq(enemy_paddle_location.reset),
                        time_until_start.eq(time_until_start.reset),
                        player_score.eq(player_score + 1),
                    ]

        m.d.comb += [
            self.vga.i_pope_location.eq(Cat(pope_location[0:10], pope_location[12:22])),
            self.vga.i_paddle_location.eq(paddle_location),
            self.vga.i_enemy_paddle_location.eq(enemy_paddle_location),
            self.vga.i_player_score.eq(player_score),
            self.vga.i_enemy_score.eq(enemy_score),
            self.vga.i_timer.eq(time_until_start),
            self.o_r.eq(self.vga.o_r),
            self.o_g.eq(self.vga.o_g),
            self.o_b.eq(self.vga.o_b),
            self.o_hsync.eq(self.vga.o_hsync),
            self.o_vsync.eq(self.vga.o_vsync),
        ]
        return m




class VGAOutput(Elaboratable):
    def __init__(self, hfront, hsync, hback, vfront, vsync, vback):
        self._hfront = hfront
        self._hsync = hsync
        self._hback = hback
        self._vfront = vfront
        self._vsync = vsync
        self._vback = vback

        self.i_enable = Signal()
        self.i_pope_location = Signal(20)
        self.i_paddle_location = Signal(10)
        self.i_enemy_paddle_location = Signal(10)
        self.i_player_score = Signal(3)
        self.i_enemy_score = Signal(3)
        self.i_timer = Signal(range(180))

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
        

        m.d.comb += [
            self.o_hsync.eq(1),
            self.o_vsync.eq(1),
        ]

        #player score
        with m.If((clock[0:11] >= 100) & 
                  (clock[0:11] < 125) & 
                  (clock[11:22] >= 50) & 
                  (clock[11:22] < 75)):
            m.d.comb += [
                self.o_r.eq(7),
                self.o_b.eq(~self.i_player_score),
                self.o_g.eq(~self.i_player_score),
            ]

        #enemy score
        with m.If((clock[0:11] >= 640-125) & 
                  (clock[0:11] < 640-100) & 
                  (clock[11:22] >= 50) & 
                  (clock[11:22] < 75)):
            m.d.comb += [
                self.o_r.eq(7),
                self.o_b.eq(~self.i_enemy_score),
                self.o_g.eq(~self.i_enemy_score),
            ]

        #timer count down
        with m.If((clock[0:11] >= 220) & 
                  (clock[0:11] < 420) & 
                  (clock[11:22] >= 100) & 
                  (clock[11:22] < 200)):
            m.d.comb += [
                self.o_r.eq((self.i_timer > 120).replicate(3)),
                self.o_b.eq(((self.i_timer > 60) & (self.i_timer <= 120)).replicate(3)),
                self.o_g.eq(((self.i_timer <= 60) & (self.i_timer != 0)).replicate(3)),
            ]

        with Image.open("jp2smol_indexed.png") as image:
            bbox = image.getbbox()
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            palette = image.getpalette("RGB")
            
            palette_index = Signal(range(30))

            with m.Switch(clock[0:11] - self.i_pope_location[0:10]):
                for x in range(width):
                    with m.Case(x):
                        with m.Switch(clock[11:22] - self.i_pope_location[10:20]):
                            for y in range(height):
                                data = image.getpixel((bbox[0] + x, bbox[1] + y))
                                if data == 0:
                                    continue
                                with m.Case(y):
                                    m.d.comb += [
                                        palette_index.eq(data),
                                    ]
            with m.Switch(palette_index):
                for palette_item in range(1,31):
                    with m.Case(palette_item):
                        m.d.comb += [
                            self.o_r.eq(palette[palette_item * 3] >> 5),
                            self.o_g.eq(palette[palette_item * 3 + 1] >> 5),
                            self.o_b.eq(palette[palette_item * 3 + 2] >> 5),
                        ]

        with m.If(
            (clock[11:22] >= self.i_paddle_location) &
            (clock[11:22] < self.i_paddle_location + 150) &
            (clock[0:11] >= 25) &
            (clock[0:11] < 50)
        ):
            m.d.comb += [
                self.o_r.eq(7),
                self.o_g.eq(7),
                self.o_b.eq(7),
            ]
        with m.If(
            (clock[11:22] >= self.i_enemy_paddle_location) &
            (clock[11:22] < self.i_enemy_paddle_location + 150) &
            (clock[0:11] < 640-25) &
            (clock[0:11] >= 640-50)
        ):
            m.d.comb += [
                self.o_r.eq(7),
                self.o_g.eq(7),
                self.o_b.eq(7),
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

    print("starting work")
    mod =Top()
    result = (convert(mod, name="sphn_vga_top", ports=[mod.o_r, mod.o_r, mod.o_g, mod.o_b, mod.o_hsync, mod.o_vsync, mod.i_move_up, mod.i_move_down, mod.i_player_two_up, mod.i_player_two_down, mod.i_player_two_active],
        emit_src=False, strip_internal_attrs=True))
    print("verilog generated")

    with open("src/vga.v", "w") as file:
        file.write(result)
    print("file written")

    def test():
        yield mod.i_enable.eq(1)

        for _ in range(1000000):
            yield

        print("done")


    sim = Simulator(mod)
    sim.add_clock(2e-12, domain="pix")
    sim.add_sync_process(test, domain="pix")

    with sim.write_vcd("test.vcd", "test.gtkw"):
        sim.run()

    print("hii")

