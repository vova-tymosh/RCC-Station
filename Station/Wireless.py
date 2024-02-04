import sys
import time
import struct
import logging
import threading
import pigpio
import queue
from RF24 import RF24, RF24_PA_HIGH, RF24_250KBPS


# RF Library Instalation
#   Home page:            https://nrf24.github.io/RF24/index.html
#   C code Instalation:   https://nrf24.github.io/RF24/md_docs_linux_install.html
#   Python wrapper:       https://nrf24.github.io/RF24/md_docs_python_wrapper.html


class Wireless:
  def __init__(self, cePin, csnPin):
    self.radio = RF24(cePin, csnPin)
    self.clientIndex = 1
    if not self.radio.begin():
        raise RuntimeError("radio hardware is not responding")
    self.radio.enableDynamicPayloads()
    self.radio.enableAckPayload()
    self.radio.setPALevel(RF24_PA_HIGH)
    self.radio.setDataRate(RF24_250KBPS)
    self.radio.printDetails()

  def startClient(self, clientAddr):
    self.radio.openReadingPipe(self.clientIndex, bytes(clientAddr, 'utf-8'))
    self.radio.writeAckPayload(self.clientIndex, struct.pack('<bf', 0, 0))
    self.clientIndex += 1

  def stop(self):
    self.radio.powerDown()


# Below is for test only
if __name__ == "__main__":
  w = Wireless(25, 8)
  w.startClient('a')
  time.sleep(1)
  w.stop()

