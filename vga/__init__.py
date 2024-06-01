import logging
import asyncio
from amaranth import *

from ....gateware.pll import *

from ... import *

from ..main import Top

class BoilerplateSubtarget(Elaboratable):
    def __init__(self, pads, in_fifo, out_fifo):
        self.pads     = pads
        self.in_fifo  = in_fifo
        self.out_fifo = out_fifo

    def elaborate(self, platform):
        m = Module()
        m.domains.pix = cd_pix = ClockDomain(reset_less=True)
        m.submodules += PLL(f_in=platform.default_clk_frequency, f_out=25175000, odomain="pix")
        m.submodules.vga = self.vga = Top()

        m.d.comb += [
            self.pads.r0_t.o.eq(self.vga.o_r[0]),
            self.pads.r0_t.oe.eq(1),
            self.pads.r1_t.o.eq(self.vga.o_r[1]),
            self.pads.r1_t.oe.eq(1),
            self.pads.r2_t.o.eq(self.vga.o_r[2]),
            self.pads.r2_t.oe.eq(1),
            self.pads.g0_t.o.eq(self.vga.o_g[0]),
            self.pads.g0_t.oe.eq(1),
            self.pads.g1_t.o.eq(self.vga.o_g[1]),
            self.pads.g1_t.oe.eq(1),
            self.pads.g2_t.o.eq(self.vga.o_g[2]),
            self.pads.g2_t.oe.eq(1),
            self.pads.b0_t.o.eq(self.vga.o_b[0]),
            self.pads.b0_t.oe.eq(1),
            self.pads.b1_t.o.eq(self.vga.o_b[1]),
            self.pads.b1_t.oe.eq(1),
            self.pads.b2_t.o.eq(self.vga.o_b[2]),
            self.pads.b2_t.oe.eq(1),
            self.pads.hsync_t.o.eq(self.vga.o_hsync),
            self.pads.hsync_t.oe.eq(1),
            self.pads.vsync_t.o.eq(self.vga.o_vsync),
            self.pads.vsync_t.oe.eq(1),
            self.vga.i_move_down.eq(self.pads.down_t.i),
            self.vga.i_move_up.eq(self.pads.up_t.i),
        ]

        return m


class VgaApplet(GlasgowApplet):
    logger = logging.getLogger(__name__)
    help = "boilerplate applet"
    preview = True
    description = """
    An example of the boilerplate code required to implement a minimal Glasgow applet.

    The only things necessary for an applet are:
        * a subtarget class,
        * an applet class,
        * the `build` and `run` methods of the applet class.

    Everything else can be omitted and would be replaced by a placeholder implementation that does
    nothing. Similarly, there is no requirement to use IN or OUT FIFOs, or any pins at all.
    """

    __pins = ("hsync","vsync","r0","r1","r2","g0","g1","g2","b0","b1","b2","up","down")

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)

        for pin in cls.__pins:
            access.add_pin_argument(parser, pin, default=True)

    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        iface.add_subtarget(BoilerplateSubtarget(
            pads=iface.get_pads(args, pins=self.__pins),
            in_fifo=iface.get_in_fifo(),
            out_fifo=iface.get_out_fifo(),
        ))

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        return await device.demultiplexer.claim_interface(self, self.mux_interface, args)

    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, iface):
        pass

# -------------------------------------------------------------------------------------------------

class BoilerplateAppletTestCase(GlasgowAppletTestCase, applet=VgaApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()