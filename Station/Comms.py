import sys
import time
import struct
import logging
import queue
import Wireless
import paho.mqtt.client as mqtt
from Config import MQTT_PREFIX_WEB, MQTT_PREFIX_JMRI

packetAuth = 'r'
packetNorm = 'n'
commandThrottle  = 't'
commandDirection = 'd'
commandLight     = 'l'

class Loco:
  def __init__(self, addr, name, fields):
    self.cmd = 't'
    self.value = 0.0
    self.addr = addr
    self.name = name
    self.fields = fields
    self.data = []
    self.queue = queue.Queue()

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

class Comms:
  def __init__(self, wireless):
    self.run = True
    self.node = 0
    self.wireless = wireless
    self.wireless.setOnReceive(self.onReceive)
    self.locoMap = {}
    self.onAuth = None
    self.onData = None

  def start(self):
    self.wireless.start()

  def stop(self):
    self.wireless.stop()

  def get(self, addr):
    if addr in self.locoMap:
      return self.locoMap[addr]

  def askToAuthorize(self, locoAddr):
    logging.info(f"Unknown id {locoAddr}, ask to authorize")
    payload = struct.pack('<bf', ord(packetAuth), 0)
    self.wireless.write(locoAddr, payload)

  def send(self, loco, toAddr):
    cmd, value = loco.peek()
    payload = struct.pack('<bf', ord(cmd), value)
    if self.wireless.write(toAddr, payload):
      loco.pop()

  def authorizePacket(self, locoAddr, payload):
    size = len(payload)
    unpacked = struct.unpack(f'<{size}s', payload)
    unpacked = unpacked[0].decode()
    fields = unpacked.split()
    loco = Loco(locoAddr, fields[1], fields[2:])
    self.locoMap[locoAddr] = loco
    self.onAuth(loco)

  def normalPacket(self, loco, payload):
    lenInFloats = int(len(payload) / 4)
    fmt = '<' + 'f'*lenInFloats
    unpacked = struct.unpack(fmt, payload)
    loco.updateData(unpacked)
    self.onData(loco)

  def onReceive(self, fromNode, payload):
    locoAddr = str(fromNode)
    packetType = payload[0]
    payload = payload[1:]
    if (packetType == ord(packetAuth)):
      self.authorizePacket(locoAddr, payload)
    else:
      if locoAddr in self.locoMap:
        loco = self.locoMap[locoAddr]
        self.normalPacket(loco, payload)
        self.send(loco, fromNode)
      else:
        self.askToAuthorize(fromNode)

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
    logging.info(f"New Loco: {MQTT_PREFIX_WEB}/{loco.addr}/fileds - {loco.name} {nice}")
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
            loco.push(commandDirection, -1)
          else:
            loco.push(commandDirection, 0)
        elif subTopic == 'function/0':
          if payload == 'ON':
            loco.push(commandLight, 1)
          else:
            loco.push(commandLight, 0)
        elif subTopic == 'command':
          loco.push(payload[0], payload[1:])


logging.basicConfig(level=logging.INFO,
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

