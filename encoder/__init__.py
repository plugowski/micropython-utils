from machine import Pin
from machine import Timer


class Encoder(object):

    def __init__(self, clk: int, dt: int, callback=None, min: int = None, max: int = None, start: int = 0,
                 step: int = 1):
        self.clk = Pin(clk, Pin.IN, Pin.PULL_UP)
        self.dt = Pin(dt, Pin.IN, Pin.PULL_UP)
        self.callback = callback
        self.prev_clk = self.encoder_clk = self.encoder_dt = False
        self.max = max
        self.min = min
        self.i = start
        self.step = step

        timer = Timer(-1)
        timer.init(period=1, mode=Timer.PERIODIC, callback=self.update)

    @property
    def position(self):
        return self.i

    def update(self, tmr):

        self.encoder_clk = self.clk.value()
        self.encoder_dt = self.dt.value()

        if not self.encoder_clk and self.prev_clk:
            state = self.step if self.encoder_dt else -1 * self.step
            new_pos = self.i + state if self.min is None else max(self.min, self.i + state)
            new_pos = new_pos if self.max is None else min(new_pos, self.max)
            self.i = new_pos

            if self.callback is not None:
                self.callback(self.i)

        self.prev_clk = self.encoder_clk
