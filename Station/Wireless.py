#
# RF24 Wireless communication
# 
# RF Library Instalation
#   Home page:            https://nrf24.github.io/RF24/index.html
#   C code Instalation:   https://nrf24.github.io/RF24/md_docs_linux_install.html
#   Python wrapper:       https://nrf24.github.io/RF24/md_docs_python_wrapper.html
#
import threading
from RF24 import RF24, RF24_PA_HIGH, RF24_250KBPS
from RF24Network import RF24Network, RF24NetworkHeader


class Wireless:
  def __init__(self, cePin, csnPin):
    self.run = True
    self.node = 0
    self.onReceive = None
    self.radio = RF24(cePin, csnPin)
    self.network = RF24Network(self.radio)
    self.thread = threading.Thread(target=self.commThread)

  def setOnReceive(self, onReceive):
    self.onReceive = onReceive

  def start(self):
    if not self.radio.begin():
      raise RuntimeError("*** Radio hardware is not responding")
    self.radio.setPALevel(RF24_PA_HIGH)
    self.radio.setDataRate(RF24_250KBPS)
    self.network.begin(self.node)
    self.thread.start()
    # self.radio.printPrettyDetails()

  def stop(self):
    self.run = False
    self.thread.join()

  def write(self, toNode, payload):
    return self.network.write(RF24NetworkHeader(toNode), payload)

  def commThread(self):
    try:
      while self.run:
        self.network.update()
        while self.network.available():
          header, payload = self.network.read()
          if len(payload) > 0 and self.onReceive:
            self.onReceive(header.from_node, payload)
    finally:
      self.radio.powerDown()


# # Below is for test only
# if __name__ == "__main__":
#   w = Wireless(25, 8)
#   w.startClient('a')
#   time.sleep(1)
#   w.stop()

