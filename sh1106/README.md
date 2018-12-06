# MicroPython driver for SH1106 OLED Display

Driver for SH1106 displays based on official [SSD1306][1] driver. Many thanks for Tomasz Jabłoński and his [article][2],
which helps me to set correct registers for that type of driver.

## Class

The driver contains the SH1106 class and the derived SH1106_I2C and SH1106_SPI classes. Besides the constructors, the methods are the same.

### I2C
```
display = sh1106.SH1106_I2C(width, height, i2c, address)
```

* width and height define the size of the display in pixxels.
* i2c is an I2C object, which has to be created beforehand and tells the ports for SDA and SCL.
* adr is the I2C address of the display [default 0x3c].

### SPI
```
display = sh1106.SH1106_SPI(width, height, spi, dc, res, cs)
```

* width and height define the size of the display in pixels.
* spi is an SPI object, which has to be created beforehand and tells the ports for SCLJ and MOSI. MISO is not used.
* dc is the GPIO Pin object for the Data/Command selection. It will be initialized by the driver.
* res is the GPIO Pin object for the reset connection. 'None' if not needed.
* cs is the GPIO Pin object for the CS connection. It can be set to 'None' or omitted.


## Framebuffer Methods
`frambuf` is available as parameter which you can use. For example:

```python
import framebuf

fb = framebuf.FrameBuffer(bitmap_bytearray, 48, 64, framebuf.MONO_HLSB)
display.framebuf.blit(fb, 40, 0)
display.show()
```

## Sample Code

### I2C

```
from machine import Pin, I2C
import sh1106

i2c = I2C(scl=Pin(22), sda=Pin(23))
display = sh1106.SH1106_I2C(128, 64, i2c)
display.fill(0)
display.text('OLED I2C TEST', 0, 0)
display.show()
```

### SPI
```
from machine import Pin, SPI
import sh1106

spi = SPI(1, baudrate=1000000)
display = sh1106.SH1106_SPI(128, 64, spi, Pin(22), Pin(23), Pin(4))
display.fill(0)
display.text('OLED SPI TEST', 0, 0)
display.show()
```

[1]: https://github.com/micropython/micropython/blob/master/drivers/display/ssd1306.py
[2]: https://stm32.eu/2016/03/29/obsluga-wyswietlacza-oled-128x64-ze-sterownikiem-sh1106/