import network
from machine import Pin
from time import sleep

wlan = network.WLAN(network.STA_IF)
wlan.active(False)

try:
    led = Pin('LED', Pin.OUT)
    while True:
        led.value(not led.value())
        sleep(0.5)
except KeyboardInterrupt:
    print("Blinking stopped by user.")
finally:
    wlan.active(False)