import sys
import time
import struct
import logging
import threading
import queue
from RF24 import RF24, RF24_PA_HIGH, RF24_250KBPS
from RF24Network import RF24Network, RF24NetworkHeader


# RF Library Instalation
#   Home page:            https://nrf24.github.io/RF24/index.html
#   C code Instalation:   https://nrf24.github.io/RF24/md_docs_linux_install.html
#   Python wrapper:       https://nrf24.github.io/RF24/md_docs_python_wrapper.html



class Loco:
  def __init__(self, locoId):
    self.cmd = 'g'
    self.value = 0.0
    self.locoId = locoId
    self.name = ''
    self.fieldNames = []
    self.data = []
    self.queue = queue.Queue()

  def toFloat(self, value):
    try:
      return float(value)
    except:
      return 0.0

  def push(self, cmd, value):
    value = self.toFloat(value)
    self.queue.put( (cmd, value) )

  def pop(self):
    try:
      self.cmd, self.value = self.queue.get(False)
    except queue.Empty:
      pass
    return self.cmd, self.value

  def updateNames(self, name, fields):
    self.name = name
    self.fieldNames = fields
    print("Reg", name, fields)


  def updateData(self, data):
    self.data = data
    nice = [F'{x:.2f}' for x in self.data]
    nice = ', '.join(nice)
    logging.info(f"Loco[{self.locoId}]: {nice}")
    print("Normal", data)

class Comms:
  packetRegistration = ord('r')
  packetNormal = ord('n')

  def __init__(self, cePin, csnPin):
    self.run = True
    self.node = 0
    self.radio = RF24(cePin, csnPin)
    self.network = RF24Network(self.radio)
    self.thread = threading.Thread(target=self.commThread)
    self.locoMap = {}

  def start(self):
    if not self.radio.begin():
        raise RuntimeError("*** Radio hardware is not responding")
    self.radio.setPALevel(RF24_PA_HIGH)
    self.radio.setDataRate(RF24_250KBPS)
    self.network.begin(self.node)
    # self.radio.printPrettyDetails()
    self.thread.start()

  def stop(self):
    self.run = False
    self.thread.join()

  def askToRegister(self, locoId):
    print("Unknown, ask to register")
    payload = struct.pack('<bf', Comms.packetRegistration, 0)
    self.network.write(RF24NetworkHeader(locoId), payload)

  def send(self, locoId):
    if locoId in self.locoMap:
      loco = self.locoMap[locoId]
      cmd, value = loco.pop()
      payload = struct.pack('<bf', ord(cmd), value)
      report = self.network.write(RF24NetworkHeader(locoId), payload)
      # print("Sent [%s] = %s, %s"%(locoId, payload, report))
      #Todo don't POP if network send fails

  def register(self, locoId, payload):
    if locoId not in self.locoMap:
      self.locoMap[locoId] = Loco(locoId)
    size = len(payload)
    unpacked = struct.unpack(f'<{size}s', payload)
    unpacked = unpacked[0].decode()
    fields = unpacked.split()
    self.locoMap[locoId].updateNames(fields[0], fields[1:])

  def normal(self, locoId, payload):
    if locoId in self.locoMap:
      lenInFloats = int(len(payload) / 4)
      fmt = '<' + 'f'*lenInFloats
      unpacked = struct.unpack(fmt, payload)
      if unpacked:
        self.locoMap[locoId].updateData(unpacked)
    else:
      self.askToRegister(locoId)

  def processPacket(self, locoId, packetType, payload):
    if (packetType == Comms.packetRegistration):
      self.register(locoId, payload)
    else:
      self.normal(locoId, payload)

  def commThread(self):
    try:
      while self.run:
        self.network.update()
        
        # self.send(1)
        # time.sleep(0.100)

        while self.network.available():
          header, payload = self.network.read()
          if len(payload) > 0:
            packetType = payload[0]
            locoId = header.from_node
            payload = payload[1:]
            self.processPacket(locoId, packetType, payload)
            # time.sleep(0.050)
            self.send(locoId)
        # time.sleep(0.020)
    finally:
      self.radio.powerDown()


if __name__ == "__main__":
  logging.basicConfig(level=logging.WARNING,
                      format='%(asctime)s %(message)s',
                      filename='station.log',
                      filemode='a')
  logging.error('Start')

  comms = Comms(25, 8)
  comms.start()
  
  while comms.run:
    time.sleep(1)

  comms.stop()
  logging.error('Stop')

