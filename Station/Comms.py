import sys
import time
import struct
import logging
import queue
import Wireless
import paho.mqtt.client as mqtt
from Config import MQTT_PREFIX_WEB, MQTT_PREFIX_JMRI

packetLocoAuth = 'r'
packetLocoNorm = 'n'
packetThrAuth = 'q'
packetThrSub = 's'
packetThrNorm = 'p'


commandThrottle  = 't'
commandDirection = 'd'
commandLight     = '@'

class Loco:
  def __init__(self, addr, name, fields):
    self.cmd = 't'
    self.value = 0.0
    self.addr = addr
    self.name = name
    self.fields = fields
    self.data = []
    self.queue = queue.Queue()
    self.throttles = {}

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

class Throttle:
  def __init__(self, addr):
    self.addr = addr
    self.subscribedAddr = None
    self.subscribedLoco = None

  def subscribe(self, locoAddr):
    self.subscribedAddr = locoAddr


class Comms:
  def __init__(self, wireless):
    self.run = True
    self.node = 0
    self.wireless = wireless
    self.wireless.setOnReceive(self.onReceive)
    self.wireless.setOnLoop(self.onLoop)
    self.locoMap = {}
    self.thrMap = {}
    self.onAuth = None
    self.onData = None
    self.slow = 0

  def start(self):
    self.wireless.start()

  def stop(self):
    self.wireless.stop()

  def get(self, addr):
    if addr in self.locoMap:
      return self.locoMap[addr]

  def askLocoToAuthorize(self, locoAddr):
    logging.warning(f"Unknown Loco {locoAddr}, ask to authorize")
    payload = struct.pack('<bf', ord(packetLocoAuth), 0)
    self.wireless.write(locoAddr, payload)

  def send(self, loco, toAddr):
    cmd, value = loco.peek()
    payload = struct.pack('<bf', ord(cmd), value)
    if self.wireless.write(toAddr, payload):
      loco.pop()

  def authorizeLoco(self, addr, payload):
    size = len(payload)
    unpacked = struct.unpack(f'<{size}s', payload)
    unpacked = unpacked[0].decode()
    fields = unpacked.split()
    loco = Loco(addr, fields[1], fields[2:])
    self.locoMap[addr] = loco
    self.onAuth(loco)

  def askThrToAuthorize(self, addr):
    payload = packetThrAuth
    addrList = list(self.locoMap.keys())
    addrList.sort()
    for i in addrList:
      payload += f'{i} {self.locoMap[i].name} '
    size = len(payload) - 1
    logging.warning(f"Unknown Thr {addr}, ask to authorize, payload {payload}")
    packed = struct.pack(f'<{size}s', bytes(payload, 'utf-8'))
    self.wireless.write(addr, packed)

  def authorizeThr(self, addr, payload):
    if addr not in self.thrMap:
      self.thrMap[addr] = Throttle(addr)
    thr = self.thrMap[addr]
    unpacked = struct.unpack('<Bf', payload)
    thr.subscribedAddr = str(unpacked[0])
    logging.warning(f"Subsribe from {addr} to {thr.subscribedAddr}");
    for k, v in self.locoMap.items():
      if addr in v.throttles:
        del v.throttles[addr]
    if thr.subscribedAddr in self.locoMap:
      loco = self.locoMap[thr.subscribedAddr]
      loco.throttles[addr] = thr
      thr.subscribedLoco = loco

  def normalPacket(self, loco, payload):
    lenInFloats = int(len(payload) / 2)
    fmt = 'H'*lenInFloats
    unpacked = struct.unpack('<' + fmt, payload)
    loco.updateData(unpacked)
    self.onData(loco)
    if self.slow == 0:
      for addr, t in loco.throttles.items():
        logging.info(f"Loco data forward to {addr},  {unpacked}")
        packed = struct.pack('<b' + fmt, ord(packetLocoNorm), *unpacked)
        self.wireless.write(int(addr), packed)
        self.slow = 0
    else:
      self.slow -= 1

  def handleThrottle(self, thr, payload):
    if thr.subscribedAddr:
      toAddr = int(thr.subscribedAddr)
      toLoco = thr.subscribedLoco
      if toLoco:
        cmd, value = struct.unpack('<bf', payload)
        cmd = chr(cmd)
        toLoco.push(cmd, value)
        logging.info(f"Forward command to {toAddr}: {cmd}/{value}")

  def onReceive(self, fromNode, payload):
    addr = str(fromNode)
    packetType = payload[0]
    payload = payload[1:]
    if (packetType == ord(packetLocoNorm)):
      if addr in self.locoMap:
        loco = self.locoMap[addr]
        self.normalPacket(loco, payload)
      else:
        self.askLocoToAuthorize(fromNode)
    elif (packetType == ord(packetThrNorm)):
      if addr in self.thrMap:
        thr = self.thrMap[addr]
        self.handleThrottle(thr, payload)
      else:
        self.askThrToAuthorize(fromNode)
    elif (packetType == ord(packetLocoAuth)):
      self.authorizeLoco(addr, payload)
    elif (packetType == ord(packetThrAuth)):
      self.askThrToAuthorize(fromNode)
    elif (packetType == ord(packetThrSub)):
      self.authorizeThr(addr, payload)
    else:
      logging.error(f"Unknown packet type: {packetType}")

  def onLoop(self):
    for addr, loco in self.locoMap.items():
      if not loco.queue.empty():
        self.send(loco, int(addr))



class CommsMqtt:
  def __init__(self, comms):
    self.comms = comms
    self.mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "RRPush")
    self.mqttClient.on_message = self.on_message

  def loop_forever(self):
    self.mqttClient.connect('127.0.0.1')
    self.mqttClient.subscribe(f'{MQTT_PREFIX_JMRI}/#')
    self.mqttClient.loop_forever()

  def onAuth(self, loco):
    nice = ' '.join(loco.fields)
    logging.warning(f"New Loco: {MQTT_PREFIX_WEB}/{loco.addr}/fileds - {loco.name} {nice}")
    self.mqttClient.publish(f"{MQTT_PREFIX_WEB}/{loco.addr}/fileds", f"{loco.name} {nice}", retain=True)

  def onData(self, loco):
    nice = [F'{x:.2f}' for x in loco.data]
    nice = ' '.join(nice)
    logging.info(f"Loco[{loco.addr}]: {nice}")
    self.mqttClient.publish(f"{MQTT_PREFIX_WEB}/{loco.addr}/data", f"{nice}")

  def on_message(self, client, userdata, msg):
      payload = str(msg.payload, 'UTF-8')
      subTopic = msg.topic[len(MQTT_PREFIX_JMRI + '/'):]
      locoAddr, subTopic = subTopic.split('/', 1)

      loco = self.comms.get(locoAddr)
      logging.info(f"MQTT/{locoAddr}/{subTopic}: {payload}")
      if loco:
        if subTopic == 'throttle':
          loco.push(commandThrottle, payload)
        elif subTopic == 'direction':
          if payload == 'FORWARD':
            loco.push(commandDirection, 1)
          elif payload == 'REVERSE':
            loco.push(commandDirection, 2)
          else:
            loco.push(commandDirection, 0)
        elif subTopic == 'function/0':
          if payload == 'ON':
            loco.push(commandLight, 1)
          else:
            loco.push(commandLight, 0)
        elif subTopic == 'command':
          loco.push(payload[0], payload[1:])


logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(message)s',
                    filename='comms.log',
                    filemode='a')
logging.error('Start')

w = Wireless.Wireless(25, 8)
comms = Comms(w)
cm = CommsMqtt(comms)
comms.onAuth = cm.onAuth
comms.onData = cm.onData

comms.start()
cm.loop_forever()

comms.stop()
logging.error('Stop')

