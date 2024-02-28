import sys
import time
import struct
import logging
import queue
import Wireless


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

  def __init__(self, wireless):
    self.run = True
    self.node = 0
    self.wireless = wireless
    self.wireless.setOnReceive(self.onReceive)
    self.locoMap = {}

  def start(self):
    self.wireless.start()

  def stop(self):
    self.wireless.stop()

  def askToRegister(self, locoId):
    print("Unknown, ask to register")
    payload = struct.pack('<bf', Comms.packetRegistration, 0)
    self.wireless.write(locoId, payload)

  def send(self, locoId):
    if locoId in self.locoMap:
      loco = self.locoMap[locoId]
      cmd, value = loco.pop()
      payload = struct.pack('<bf', ord(cmd), value)
      self.wireless.write(locoId, payload)
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

  def onReceive(self, fromNode, payload):
    locoId = fromNode
    packetType = payload[0]
    payload = payload[1:]
    if (packetType == Comms.packetRegistration):
      self.register(locoId, payload)
    else:
      self.normal(locoId, payload)
    self.send(locoId)


if __name__ == "__main__":
  logging.basicConfig(level=logging.WARNING,
                      format='%(asctime)s %(message)s',
                      filename='station.log',
                      filemode='a')
  logging.error('Start')

  w = Wireless.Wireless(25, 8)
  comms = Comms(w)
  comms.start()
  
  while 1:
    time.sleep(1)

  comms.stop()
  logging.error('Stop')

