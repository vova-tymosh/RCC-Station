import sys
import time
import struct
import logging
import queue
import Wireless
import paho.mqtt.client as mqtt


class Loco:
  def __init__(self, locoId, addr, name, fields):
    self.cmd = 'g'
    self.value = 0.0
    self.locoId = locoId
    self.addr = addr
    self.name = name
    self.fields = fields
    self.data = []
    self.queue = queue.Queue()
    logging.info(f"New loco Id: {locoId}, Addr: {addr}, Name: {name}, Fields: {fields}")

  def toFloat(self, value):
    try:
      return float(value)
    except:
      return 0.0

  def push(self, cmd, value):
    value = self.toFloat(value)
    if self.queue.empty():
      self.cmd, self.value = (cmd, value)
    self.queue.put( (cmd, value) )

  def peek(self):
    return self.cmd, self.value

  def pop(self):
    try:
      self.cmd, self.value = self.queue.get(False)
    except queue.Empty:
      pass

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
    self.locoMapByAddr = {}

  def start(self):
    self.wireless.start()

  def stop(self):
    self.wireless.stop()

  def findByAddr(self, locoAddr):
    if locoAddr in self.locoMapByAddr:
      return self.locoMapByAddr[locoAddr]

  def askToAuthorize(self, locoId):
    logging.info(f"Unknown id {locoId}, ask to authorize")
    payload = struct.pack('<bf', Comms.packetAuth, 0)
    self.wireless.write(locoId, payload)

  def send(self, locoId):
    loco = self.locoMap[locoId]
    cmd, value = loco.peek()
    payload = struct.pack('<bf', ord(cmd), value)
    if self.wireless.write(locoId, payload):
      loco.pop()

  def authorizePacket(self, locoId, payload):
    size = len(payload)
    unpacked = struct.unpack(f'<{size}s', payload)
    unpacked = unpacked[0].decode()
    fields = unpacked.split()
    loco = Loco(locoId, fields[0], fields[1], fields[2:])
    self.locoMap[locoId] = loco
    self.locoMapByAddr[loco.addr] = loco

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



def on_message(client, userdata, msg):
    payload = str(msg.payload, 'UTF-8')
    subTopic = msg.topic[len(locoPrefix):]
    locoAddr, subTopic = subTopic.split('/', 1)

    loco = comms.findByAddr(locoAddr)
    logging.info(f"MQTT/{locoAddr}/{subTopic}: {payload}")
    if loco:
      if subTopic == 'throttle':
        loco.push('t', payload)
      elif subTopic == 'direction':
        if payload == 'FORWARD':
          loco.push('g', 1)
        elif payload == 'REVERSE':
          loco.push('g', -1)
        else:
          loco.push('g', 0)
      elif subTopic == 'function/0':
        if payload == 'ON':
          loco.push('b', 1)
        else:
          loco.push('b', 0)
      # elif subTopic == 'function/1':
      #   if payload == 'ON':
      #     client.publish("cab/25/throttle", 50)
      #   else:
      #     loco.push('b', 0)


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    filename='station.log',
                    filemode='a')
logging.error('Start')

w = Wireless.Wireless(25, 8)
comms = Comms(w)
comms.start()

locoPrefix = 'cab/'

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "RRStation")
client.on_message = on_message
client.connect('127.0.0.1')
client.subscribe(f'{locoPrefix}#')

client.loop_forever()

comms.stop()
logging.error('Stop')

