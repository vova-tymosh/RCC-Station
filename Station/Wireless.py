import sys
import time
import struct
import logging
import threading
import pigpio
import queue
from nrf24 import *

CE_PIN = 25


RF_POWER = RF24_PA.HIGH
RF_BITRATE = RF24_DATA_RATE.RATE_250KBPS

# https://github.com/bjarne-hansen/py-nrf24
#   pip install nrf24
# https://abyz.me.uk/rpi/pigpio/download.html
#   sudo apt-get install pigpio python3-pigpio

class Wireless:
  def __init__(self, cePin):
    self.gpio = pigpio.pi(host = 'localhost', port = 8888)
    if not self.gpio.connected:
      print("Not connected to Raspberry Pi ... goodbye.")
      sys.exit()
    self.radio = NRF24(self.gpio, ce=cePin, payload_size=RF24_PAYLOAD.DYNAMIC, data_rate=RF_BITRATE, pa_level=RF_POWER)
    self.clientIndex = 1

  def startClient(self, clientAddr):
    self.radio.open_reading_pipe(self.clientIndex, clientAddr, size=RF24_PAYLOAD.ACK)
    self.radio.ack_payload(self.clientIndex, struct.pack('<bf', 0, 0))
    self.clientIndex += 1

  def stop(self):
    self.radio.power_down()
    self.gpio.stop()

class Client:
  def __init__(self, name):
    self.cmd = '0'
    self.value = 0.0
    self.data = []
    self.name = name
    self.queue = queue.Queue()

  def toFloat(self, value):
    try:
      return float(value)
    except:
      return 0.0

  def command(self, cmd, value):
    self.queue.put( (cmd, self.toFloat(value)) )

  def getQueued(self):
    try:
      self.cmd, self.value = self.queue.get(False)
    except queue.Empty:
      pass
    return self.cmd, self.value

class Command:
  def __init__(self, radioCePin, codeBase):
    self.run = True
    self.codeBase = codeBase
    self.clientIndex = 0
    self.clients = []
    self.wireless = Wireless(radioCePin)
    self.thread = threading.Thread(target=self.commThread)
    self.fieldNames = []

  def dumpFields(self, clientIndex, client):
    nice = [F'{x:.2f}' for x in client.data]
    nice = ', '.join(nice)
    logging.info(f"Loco[{clientIndex}]: {client.cmd}/{client.value:.2f} {nice}")

  def dumpNames(self, names):
    nice = [x.decode() for x in names]
    self.fieldNames = nice
    nice = ', '.join(nice)
    logging.info(f"Field Names: {nice}")

  def addClient(self, name, code = 'T'):
    if len(code) == 0:
      code = 'T'
    elif len(code) > 1:
      code = code[0]
    self.clients.append(Client(name))
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

          if len(payload) > 0:
            packetId = payload[0]
            payload = payload[1:]
            if packetId == 0x00:
              lenInFloats = int(len(payload) / 7)
              fmt = '<' + '7s'*lenInFloats
              unpacked = self.unpack(fmt, payload)
              if unpacked:
                names = unpacked
                self.dumpNames(names)
            elif packetId == 0x80:
              lenInFloats = int(len(payload) / 4)
              fmt = '<' + 'f'*lenInFloats
              if client:
                unpacked = self.unpack(fmt, payload)
                if unpacked:
                  client.data = unpacked
                  self.dumpFields(pipe-1, client)
        time.sleep(0.05)
    finally:
      self.wireless.stop()


command = Command(CE_PIN, 'ZWWW')


