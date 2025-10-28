#
# RF24 Wireless communication
# 
# RF Library Instalation
#   Home page:            https://nrf24.github.io/RF24/index.html
#   C code Instalation:   https://nrf24.github.io/RF24/md_docs_linux_install.html
#   Python wrapper:       https://nrf24.github.io/RF24/md_docs_python_wrapper.html
#
import time
import queue
import threading
import logging
from pyrf24 import RF24, RF24Network, RF24NetworkHeader, RF24_PA_LOW, RF24_PA_HIGH, RF24_250KBPS


class WirelessNode:

    def __init__(self, addr, _write, timeout):
        self.addr = int(addr)
        self.write = _write
        self.timeout = timeout
        self.message = None
        self.queue = queue.Queue()
        self.sinceError = 0

    def disconncted(self):
        return self.sinceError and time.time() > self.sinceError + self.timeout

    def push(self, message):
        self.queue.put(message)

    def pop(self):
        if self.message == None:
            if self.queue.empty():
                return False
            self.message = self.queue.get(False)
        if self.write(self.addr, self.message):
            self.message = None
            self.sinceError = 0
            return True
        else:
            if self.sinceError == 0:
                self.sinceError = time.time()
            return False

class Wireless:

  def __init__(self, cePin, csnPin, timeout = 5):
    self.STATION_NODE = 0
    self.run = True
    self.onReceive = None
    self.onDisconnect = None
    self.timeout = timeout
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
    if toNode in self.nodes:
      self.nodes[toNode].push(payload)

  def disconnect(self, node):
    if self.onDisconnect:
      self.onDisconnect(node.addr)
    if node.addr in self.nodes:
      del self.nodes[node.addr]

  def commThread(self):
    try:
      while self.run:
        needWait = True
        self.network.update()
        if self.network.available():
          header, payload = self.network.read()
          needWait = False
          if header.from_node not in self.nodes:
            with self.nodesLock:
              self.nodes[header.from_node] = WirelessNode(header.from_node, self.writeInternal, self.timeout)
          if len(payload) > 0 and self.onReceive:
            self.onReceive(header.from_node, payload)
        with self.nodesLock:
          toDisconnect = []
          for node in self.nodes.values():
            if node.pop():
              needWait = False
            if node.disconncted():
              toDisconnect.append(node)
          for node in toDisconnect:
            self.disconnect(node)

        if needWait:
          time.sleep(0.01)
    finally:
      self.radio.powerDown()


# # Below is for test only
# if __name__ == "__main__":
#   w = Wireless(25, 8)
#   w.startClient('a')
#   time.sleep(1)
#   w.stop()

