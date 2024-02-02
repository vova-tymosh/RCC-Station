import sys
import time
import struct
import logging
import threading
import queue
from Wireless import Wireless

CE_PIN = 25

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Client:
  def __init__(self, index, name):
    self.cmd = '0'
    self.value = 0.0
    self.data = []
    self.name = name
    self.index = index
    self.fieldNames = []
    self.queue = queue.Queue()
    self.gear = 0
    self.throttle = 0

  def toFloat(self, value):
    try:
      return float(value)
    except:
      return 0.0

  def command(self, cmd, value):
    value = self.toFloat(value)
    self.queue.put( (cmd, value) )
    if cmd == 'g':
      self.gear = value
    elif cmd == 't':
      self.throttle = value

  def getQueued(self):
    try:
      self.cmd, self.value = self.queue.get(False)
    except queue.Empty:
      pass
    return self.cmd, self.value

  def getFieldIndex(self, fieldName):
    try:
      return self.fieldNames.index(fieldName)
    except:
      return -1

  def updateData(self, data):
    self.data = data
    nice = [F'{x:.2f}' for x in self.data]
    nice = ', '.join(nice)
    logger.info(f"Loco[{self.index}]: {self.cmd}/{self.value:.2f} {nice}")

  def updateFieldName(self, index, name):
    for i in range(len(self.fieldNames), index+1):
      self.fieldNames.append('')
    name = name.decode()
    self.fieldNames[index] = name
    nice = ', '.join(self.fieldNames)
    logger.info(f"Field Names[{self.index}]: {nice}")

  def getFieldNames(self):
    return self.fieldNames

  def getGear(self):
    return self.gear

  def getThrottle(self):
    return self.throttle


class Command:
  def __init__(self, radioCePin, codeBase):
    self.run = True
    self.codeBase = codeBase
    self.clientIndex = 0
    self.clients = []
    self.wireless = Wireless(radioCePin)
    self.thread = threading.Thread(target=self.commThread)

  def addClient(self, name, code = 'T'):
    if len(code) == 0:
      code = 'T'
    elif len(code) > 1:
      code = code[0]
    index = len(self.clients)
    self.clients.append(Client(index, name))
    self.wireless.startClient(code + self.codeBase)

  def getClientList(self):
    return self.clients

  def getClient(self):
    return self.clients[self.clientIndex]

  def setClient(self, index):
    index = int(index)
    if index >= 0 and index < len(self.clients):
      self.clientIndex = index

  def start(self):
    self.thread.start()

  def stop(self):
    self.run = False
    self.thread.join()

  def process(self, line):
    if len(line) > 0:
      client = self.getClient()
      cmd = line[0]
      value = line[1:]
      if cmd == 'q':
        self.run = False
      elif cmd == 'p':
        nice = [F'{x:.2f}' for x in client.data]
        nice = ', '.join(nice)
        print(F'[{client.name}]: {nice}')
      elif cmd == 'c':
        try:
          value = int(value)
        except:
          value = 0
        self.setClient(value)
      else:
        client.command(cmd, value)


  def unpack(self, fmt, payload):
    try:
      return struct.unpack(fmt, payload)
    except:
      return None

  def commThread(self):
    namesMask = 0x80
    indexMask = 0x0F
    try:
      while self.run:
        available, pipe = self.wireless.radio.data_ready_pipe()
        if available:
          payload = self.wireless.radio.get_payload()
          if pipe <= len(self.clients):
            client = self.clients[pipe - 1]
            cmd, value = client.getQueued()
            ackData = struct.pack('<bf', ord(cmd), value)
            self.wireless.radio.ack_payload(pipe, ackData)
          else:
            client = None

          if client and len(payload):
            packetId = payload[0]
            payload = payload[1:]
            if (packetId & namesMask):
              size = len(payload)
              fmt = f'<{size}s'
              unpacked = self.unpack(fmt, payload)
              if unpacked:
                index = packetId & indexMask
                client.updateFieldName(index, unpacked[0])
            else:
              lenInFloats = int(len(payload) / 4)
              fmt = '<' + 'f'*lenInFloats
              unpacked = self.unpack(fmt, payload)
              if unpacked:
                client.updateData(unpacked)
        time.sleep(0.05)
    finally:
      self.wireless.stop()


command = Command(CE_PIN, 'ZWWW')


