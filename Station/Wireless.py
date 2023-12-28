import sys
import time
import struct
import logging
import threading
import pigpio
import queue
from nrf24 import *


RF_POWER = RF24_PA.HIGH
RF_BITRATE = RF24_DATA_RATE.RATE_250KBPS

# https://github.com/bjarne-hansen/py-nrf24
#   pip install nrf24
# https://abyz.me.uk/rpi/pigpio/download.html
#   sudo apt-get install pigpio python3-pigpio

class Wireless:
  def __init__(self, cePin):
    self.gpio = pigpio.pi(host = 'localhost', port = 8888)
    if not self.gpio.connected:
      print("Not connected to Raspberry Pi ... goodbye.")
      sys.exit()
    self.radio = NRF24(self.gpio, ce=cePin, payload_size=RF24_PAYLOAD.DYNAMIC, data_rate=RF_BITRATE, pa_level=RF_POWER)
    self.clientIndex = 1

  def startClient(self, clientAddr):
    self.radio.open_reading_pipe(self.clientIndex, clientAddr, size=RF24_PAYLOAD.ACK)
    self.radio.ack_payload(self.clientIndex, struct.pack('<bf', 0, 0))
    self.clientIndex += 1

  def stop(self):
    self.radio.power_down()
    self.gpio.stop()

