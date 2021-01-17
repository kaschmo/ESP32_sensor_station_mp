import ssd1306
from machine import Pin, I2C
import time

class LEDDisplay:
    def __init__(self, rst, scl, sda):
        # OLED Handling and start message
        rst = Pin(rst, Pin.OUT)
        rst.value(1)
        scl = Pin(scl, Pin.OUT, Pin.PULL_UP)
        sda = Pin(sda, Pin.OUT, Pin.PULL_UP)
        i2c = I2C(scl=scl, sda=sda, freq=450000)
        self.oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

        #init text
        self.oled.fill(0)
        self.oled.text('Display initialized',0,0)
        self.oled.show()

        #menu page
        self.menu_page = 0
        self.menu_timer = 0
        self.state = 1

    def write(self, *args, **kwargs):
        self.oled.fill(0)
        i=0
        for ar in args:
            self.oled.text(ar, 0, i*8)
            i=i+1
        self.oled.show()
        self.state = 1

    def off(self):
        if (self.state == 1):
            print('switching off display')
            self.oled.fill(0)
            self.oled.show()
            self.menu_page = 0
            self.state = 0

    def next_page(self):
        self.menu_page = self.menu_page + 1
        self.menu_timer = time.ticks_ms()
        print('Display: cycle menu')

    
    def wrap(self):
        self.menu_page = 0
        self.menu_timer = time.ticks_ms()

    def refresh(self):
        #todo hard coded
        if (time.ticks_ms() - self.menu_timer > 5000):
            self.off()