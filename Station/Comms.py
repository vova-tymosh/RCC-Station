import sys
import time
import struct
import logging
import queue
import Wireless


class Loco:
  def __init__(self, locoId, name, fields):
    self.cmd = 'g'
    self.value = 0.0
    self.locoId = locoId
    self.name = name
    self.fields = fields
    self.data = []
    self.queue = queue.Queue()
    logging.info(f"New loco Id: {locoId}, Name: {name}, Fields: {fields}")

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

  def updateData(self, data):
    self.data = data
    nice = [F'{x:.2f}' for x in self.data]
    nice = ', '.join(nice)
    logging.info(f"Loco[{self.locoId}]: {nice}")

class Comms:
  packetAuth = ord('r')
  packetNorm = ord('n')

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

  def askToAuthorize(self, locoId):
    logging.info(f"Unknown id {locoId}, ask to authorize")
    payload = struct.pack('<bf', Comms.packetAuth, 0)
    self.wireless.write(locoId, payload)

  def send(self, locoId):
    loco = self.locoMap[locoId]
    cmd, value = loco.pop()
    payload = struct.pack('<bf', ord(cmd), value)
    self.wireless.write(locoId, payload)
    #Todo don't POP if network send fails

  def authorizePacket(self, locoId, payload):
    size = len(payload)
    unpacked = struct.unpack(f'<{size}s', payload)
    unpacked = unpacked[0].decode()
    fields = unpacked.split()
    self.locoMap[locoId] = Loco(locoId, fields[0], fields[1:])

  def normalPacket(self, locoId, payload):
    lenInFloats = int(len(payload) / 4)
    fmt = '<' + 'f'*lenInFloats
    unpacked = struct.unpack(fmt, payload)
    self.locoMap[locoId].updateData(unpacked)

  def onReceive(self, fromNode, payload):
    locoId = fromNode
    packetType = payload[0]
    payload = payload[1:]
    if (packetType == Comms.packetAuth):
      self.authorizePacket(locoId, payload)
    else:
      if locoId in self.locoMap:
        self.normalPacket(locoId, payload)
        self.send(locoId)
      else:
        self.askToAuthorize(locoId)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
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

