# MicroPython SH1106 OLED driver, I2C and SPI interfaces
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Paweł Ługowski (@plugowski)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


from micropython import const
import utime as time
import framebuf

# register definitions
SET_CONTRAST = const(0x81)
SET_NORM_INV = const(0xa6)
SET_DISP = const(0xae)
SET_SCAN_DIR = const(0xc0)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP = const(0xa1)
SET_MUX_RATIO = const(0xa8)
SET_DISP_OFFSET = const(0xd3)
SET_COM_PIN_CFG = const(0xda)
SET_LOW_COLUMN_ADDRESS = const(0x00)
SET_HIGH_COLUMN_ADDRESS = const(0x10)
SET_PAGE_ADDRESS = const(0xB0)
SET_DISP_CLK_DIV = const(0xd5)
SET_PRECHARGE = const(0xd9)
SET_VCOM_DESEL = const(0xdb)
SET_CHARGE_PUMP = const(0x8d)


class SH1106(framebuf.FrameBuffer):

    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    def init_display(self):
        for cmd in (
                0x80,  # control byte
                SET_DISP | 0x00,  # Display OFF
                SET_LOW_COLUMN_ADDRESS,  # Low Column
                SET_HIGH_COLUMN_ADDRESS,  # High Column
                SET_PAGE_ADDRESS,  # Page
                SET_DISP_START_LINE,  # Start line
                SET_SEG_REMAP,  # remap
                SET_COM_PIN_CFG, 0x12,  # com pins
                SET_DISP_OFFSET, 0x00,  # display offset: NO offset
                SET_SCAN_DIR, 0xc8,  # scan direction
                SET_NORM_INV,  # normal display
                0xA4,  # display ON
                SET_CONTRAST, 0x50,  # set contrast
                SET_MUX_RATIO, 0x3f,  # multiplex ratio: 1/64 duty
                SET_DISP_CLK_DIV, 0x80,  # Display clock divide
                SET_PRECHARGE, 0xf1,  # precharge period
                SET_VCOM_DESEL, 0x40,  # VCOM deselect
                SET_CHARGE_PUMP, 0x14,  # charge pump
                SET_DISP | 0x01):  # display ON
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        self.write_cmd(SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(SET_DISP | 0x01)

    def sleep(self, value):
        self.write_cmd(SET_DISP | (not value))

    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def show(self):
        for page in range(self.height // 8):
            self.write_cmd(SET_PAGE_ADDRESS | page)
            self.write_cmd(SET_LOW_COLUMN_ADDRESS | 2)
            self.write_cmd(SET_HIGH_COLUMN_ADDRESS | 0)
            self.write_data(self.buffer[self.width * page:self.width * page + self.width])


class SH1106_I2C(SH1106):
    def __init__(self, width, height, i2c, addr=0x3c, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.temp[0] = self.addr << 1
        self.temp[1] = 0x40  # Co=0, D/C#=1
        self.i2c.start()
        self.i2c.write(self.temp)
        self.i2c.write(buf)
        self.i2c.stop()


class SH1106_SPI(SH1106):
    def __init__(self, width, height, spi, dc, res, cs=None, external_vcc=False):
        self.rate = 10 * 1000 * 1000
        dc.init(dc.OUT, value=0)
        if res is not None:
            res.init(res.OUT, value=0)
        if cs is not None:
            cs.init(cs.OUT, value=1)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        self.res(1)
        time.sleep_ms(1)
        self.res(0)
        time.sleep_ms(10)
        self.res(1)
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        if self.cs is not None:
            self.cs(1)
            self.dc(0)
            self.cs(0)
            self.spi.write(bytearray([cmd]))
            self.cs(1)
        else:
            self.dc(0)
            self.spi.write(bytearray([cmd]))

    def write_data(self, buf):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        if self.cs is not None:
            self.cs(1)
            self.dc(1)
            self.cs(0)
            self.spi.write(buf)
            self.cs(1)
        else:
            self.dc(1)
            self.spi.write(buf)
