import sys
import time
import struct
import logging
import queue
import Wireless
import paho.mqtt.client as mqtt
from paho.mqtt.subscribeoptions import SubscribeOptions
from Config import MQTT_PREFIX_WEB, MQTT_PREFIX_JMRI

# packetLocoAuth = 'r'
# packetLocoNorm = 'n'
packetThrAuth = 'q'
packetThrSub = 's'
packetThrNorm = 'p'


# commandThrottle  = 't'
# commandDirection = 'd'
# commandLight     = '@'


CMD_AUTH = 'A';
CMD_HEARTBEAT = 'H';

CMD_THROTTLE = 'T';
CMD_DIRECTION = 'D';
CMD_SET_FUNCTION = 'F';
CMD_GET_FUNCTION = 'P';
CMD_SET_VALUE = 'S';
CMD_GET_VALUE = 'G';
CMD_LIST_VALUE = 'L';

def toInt(value):
  try:
    return int(value)
  except:
    return 0

class Loco:
  def __init__(self, addr, version, fmt, name, fields):
    # self.cmd = 't'
    # self.value = 0.0
    self.payload = struct.pack('<BB', ord(CMD_THROTTLE), 0)
    self.version = version
    self.fmt = fmt
    self.addr = addr
    self.name = name
    self.fields = fields
    self.data = []
    self.queue = queue.Queue()
    self.throttles = {}

  # def toFloat(self, value):
  #   try:
  #     return int(value)
  #   except:
  #     return 0.0

  def push(self, payload):
    if self.queue.empty():
      self.payload = payload
    self.queue.put( payload )

  def peek(self):
    return self.payload

  def pop(self):
    try:
      self.payload = self.queue.get(False)
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
    self.onSetFunction = None
    self.onSetValue = None

  def start(self):
    self.wireless.start()

  def stop(self):
    self.wireless.stop()

  def get(self, addr):
    if addr in self.locoMap:
      return self.locoMap[addr]

  def safeUnpack(self, fmt, data):
    unpacked = []
    try:
      unpacked = struct.unpack(fmt, data)
    except:
      pass
    return unpacked

  def askLocoToAuthorize(self, locoAddr):
    logging.warning(f"Unknown Loco {locoAddr}, ask to authorize")
    payload = struct.pack('<BB', ord(CMD_AUTH), 0)
    self.wireless.write(locoAddr, payload)

  def send(self, loco, toAddr):
    payload = loco.peek()
    # payload = struct.pack('<BB', ord(cmd), value)

    # if cmd == 'z':
    #   _key = "keyTest"
    #   k = len(_key)
    #   _value = "valueTest"
    #   v = len(_value)
    #   payload = struct.pack('<bbbbb{k}s{v}s', ord(cmd), k, v, 0, 0, _key, _value)

    if self.wireless.write(toAddr, payload):
      loco.pop()

  def authorizeLoco(self, addr, payload):
    fields = payload.decode().split()
    if len(fields) > 4:
      loco = Loco(addr = addr, version = fields[0], fmt = fields[1], name = fields[3], fields = fields[4:])
      self.locoMap[addr] = loco
      self.onAuth(loco)
      for k, v in self.thrMap.items():
        self.askThrToAuthorize(int(v.addr))

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
    unpacked = self.safeUnpack('<Bf', payload)
    if len(unpacked) > 0:
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
    fmt = '<' + loco.fmt
    size = struct.calcsize(fmt)
    if len(payload) >= size:
      unpacked = self.safeUnpack(fmt, payload)
      unpacked = unpacked[1:]
      loco.updateData(unpacked)
      self.onData(loco)
      for addr, t in loco.throttles.items():
        logging.info(f"Loco data forward to {addr},  {unpacked}")
        self.wireless.write(int(addr), payload)

  def handleThrottle(self, thr, payload):
    if thr.subscribedAddr:
      toAddr = int(thr.subscribedAddr)
      toLoco = thr.subscribedLoco
      if toLoco:
        unpacked = self.safeUnpack('<bf', payload)
        if len(unpacked) == 2:
          cmd, value = unpacked
          cmd = chr(cmd)
          toLoco.push(cmd, value)
          logging.info(f"Forward command to {toAddr}: {cmd}/{value}")

  def onReceive(self, fromNode, payload):
    addr = str(fromNode)
    packetType = chr(payload[0])

    logging.error(f">>>:{payload}")

    if (packetType == CMD_HEARTBEAT):
      if addr in self.locoMap:
        loco = self.locoMap[addr]
        self.normalPacket(loco, payload)
      else:
        self.askLocoToAuthorize(fromNode)
    elif (packetType == packetThrNorm):
      if addr in self.thrMap:
        thr = self.thrMap[addr]
        self.handleThrottle(thr, payload[1:])
      else:
        self.askThrToAuthorize(fromNode)
    elif (packetType == CMD_AUTH):
      self.authorizeLoco(addr, payload[1:])
    elif (packetType == CMD_SET_FUNCTION):
      if addr in self.locoMap:
        loco = self.locoMap[addr]
        unpacked = self.safeUnpack('<BB', payload)
        functionId = unpacked[1] & 0x7F
        activate = unpacked[1] & 0x80
        self.onSetFunction(loco, functionId, activate)
    elif (packetType == CMD_SET_VALUE):
      if addr in self.locoMap:
        loco = self.locoMap[addr]
        unpacked = struct.unpack('<BB', payload[:2])
        k = toInt(unpacked[1])
        v = len(payload) - 2 - k - 2
        unpacked = struct.unpack(f'<BB{k}sB{v}sB', payload)
        key = unpacked[2].decode()
        value = unpacked[4].decode()
        self.onSetValue(loco, key, value)
    elif (packetType == packetThrAuth):
      self.askThrToAuthorize(fromNode)
    elif (packetType == packetThrSub):
      self.authorizeThr(addr, payload[1:])
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
    options = SubscribeOptions(noLocal=True)
    self.mqttClient.subscribe(f'{MQTT_PREFIX_JMRI}/#', options=options)
    self.mqttClient.loop_forever()

  def onAuth(self, loco):
    nice = ' '.join(loco.fields)
    logging.warning(f"New Loco: v{loco.version} {MQTT_PREFIX_WEB}/{loco.addr}/fileds - {loco.name} {nice}")
    self.mqttClient.publish(f"{MQTT_PREFIX_WEB}/{loco.addr}/fileds", f"{loco.name} {nice}", retain=True)

  def onSetFunction(self, loco, functionId, activate):
    activate = "ON" if activate else "OFF"
    logging.warning(f"Function Set: {MQTT_PREFIX_JMRI}/{loco.addr}/function/{functionId} {activate}")
    self.mqttClient.publish(f"{MQTT_PREFIX_JMRI}/{loco.addr}/function/{functionId}", f"{activate}")

  def onSetValue(self, loco, key, value):
    logging.warning(f"Value Set: {MQTT_PREFIX_JMRI}/{loco.addr}/value/{key} {value}")
    self.mqttClient.publish(f"{MQTT_PREFIX_JMRI}/{loco.addr}/value/{key}", f"{value}")

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
          loco.push(struct.pack('<BB', ord(CMD_THROTTLE), toInt(payload)))
        elif subTopic == 'direction':
          if payload == 'FORWARD' or payload == '1':
            loco.push(struct.pack('<BB', ord(CMD_DIRECTION), 1))
          elif payload == 'REVERSE' or payload == '0':
            loco.push(struct.pack('<BB', ord(CMD_DIRECTION), 0))
          elif payload == 'STOP' or payload == '2':
            loco.push(struct.pack('<BB', ord(CMD_DIRECTION), 2))
          elif payload == 'NEUTRAL' or payload == '3':
            loco.push(struct.pack('<BB', ord(CMD_DIRECTION), 3))
        elif subTopic.startswith('function/get'):
          functionId = toInt(payload)
          loco.push(struct.pack('<BB', ord(CMD_GET_FUNCTION), functionId))
        elif subTopic.startswith('function/'):
          functionId = toInt(subTopic[len('function/'):])
          if payload == 'ON':
            loco.push(struct.pack('<BB', ord(CMD_SET_FUNCTION), (1 << 7) | functionId))
          else:
            loco.push(struct.pack('<BB', ord(CMD_SET_FUNCTION), functionId))
        elif subTopic.startswith('value/get'):
          key = payload.encode()
          k = len(key)
          loco.push(struct.pack(f'<BB{k}sB', ord(CMD_GET_VALUE), k, key, 0))
        elif subTopic.startswith('value/list'):
          loco.push(struct.pack('<BB', ord(CMD_LIST_VALUE), 0))
        elif subTopic.startswith('value/'):
          key = subTopic[len('value/'):].encode()
          value = payload.encode()
          k = len(key)
          v = len(value)
          packet = struct.pack(f'<BB{k}sB{v}sB', ord(CMD_SET_VALUE), len(key), key, 0, value, 0)
          loco.push(packet)
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
comms.onSetFunction = cm.onSetFunction 
comms.onSetValue = cm.onSetValue 

comms.start()
cm.loop_forever()

comms.stop()
logging.error('Stop')

