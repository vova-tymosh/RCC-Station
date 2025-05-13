#
# RF24 Wireless communication
# 
# RF Library Instalation
#   Home page:            https://nrf24.github.io/RF24/index.html
#   C code Instalation:   https://nrf24.github.io/RF24/md_docs_linux_install.html
#   Python wrapper:       https://nrf24.github.io/RF24/md_docs_python_wrapper.html
#
import queue
import threading
import logging
from RF24 import RF24, RF24_PA_LOW, RF24_PA_HIGH, RF24_250KBPS
from RF24Network import RF24Network, RF24NetworkHeader

class WirelessNode:

    def __init__(self, addr, _write):
        self.addr = int(addr)
        self.write = _write
        self.message = None
        self.queue = queue.Queue()

    def push(self, message):
        self.queue.put(message)

    def pop(self):
        if self.message == None:
            if self.queue.empty():
                return
            self.message = self.queue.get(False)
        if self.write(self.addr, self.message):
            self.message = None

class Wireless:

  def __init__(self, cePin, csnPin):
    self.STATION_NODE = 0
    self.run = True
    self.onReceive = None
    self.nodes = {}
    self.nodesLock = threading.Lock()
    self.radio = RF24(cePin, csnPin)
    self.network = RF24Network(self.radio)
    self.thread = threading.Thread(target=self.commThread)

  def start(self):
    if not self.radio.begin():
      raise RuntimeError("*** Radio hardware is not responding")
    self.radio.setPALevel(RF24_PA_LOW)
    self.radio.setDataRate(RF24_250KBPS)
    self.network.begin(self.STATION_NODE)
    self.thread.start()
    # self.radio.printPrettyDetails()

  def stop(self):
    self.run = False
    self.thread.join()

  def writeInternal(self, toNode, payload):
    return self.network.write(RF24NetworkHeader(toNode), payload)

  def write(self, toNode, payload):
    toNode = int(toNode)
    if toNode not in self.nodes:
      with self.nodesLock:
        self.nodes[toNode] = WirelessNode(toNode, self.writeInternal)
    self.nodes[toNode].push(payload)

  def commThread(self):
    try:
      while self.run:
        self.network.update()
        while self.network.available():
          header, payload = self.network.read()
          if len(payload) > 0 and self.onReceive:
            self.onReceive(header.from_node, payload)
        with self.nodesLock:
          for node in self.nodes.values():
            node.pop()
    finally:
      self.radio.powerDown()


# # Below is for test only
# if __name__ == "__main__":
#   w = Wireless(25, 8)
#   w.startClient('a')
#   time.sleep(1)
#   w.stop()

