import sys
import time
import logging
import threading
import paho.mqtt.client as mqtt
from Config import MQTT_PREFIX_WEB, MQTT_PREFIX_JMRI


class Loco:
  def __init__(self, addr, name, fields):
    self.addr = addr
    self.name = name
    self.fields = fields
    self.throttle = 0
    self.direction = 0
    self.data = []
    self.mqttClient = None
    nice = ' '.join(fields)
    logging.info(f"New loco Addr: {addr}, Name: {name}, Fields: {nice}")

  def setDirection(self, value):
    self.direction = value
    self.mqttClient.publish(f"{MQTT_PREFIX_JMRI}/{self.addr}/direction", self.direction)
    logging.info(f"{MQTT_PREFIX_JMRI}/{self.addr}/direction - {self.direction}")

  def getDirection(self):
    return self.direction

  def setThrottle(self, value):
    self.throttle = value
    self.mqttClient.publish(f"{MQTT_PREFIX_JMRI}/{self.addr}/throttle", self.throttle)

  def getThrottle(self):
    return self.throttle

  def setFunction(self, func, value):
    self.mqttClient.publish(f"{MQTT_PREFIX_JMRI}/{self.addr}/function/{func}", value)

  def setCommand(self, cmd, value):
    self.mqttClient.publish(f"{MQTT_PREFIX_JMRI}/{self.addr}/command", f"{cmd}{value}")

  def getFieldNames(self):
    return self.fields

  def updateData(self, data):
    self.data = data


class Command(object):
  _instance = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super(Command, cls).__new__(cls)
    return cls._instance        

  def __init__(self):
    self.locoMap = {}
    self.current = None
    self.mqttClient = None

  def get(self, addr = None):
    if addr == None or addr not in self.locoMap:
      addr = self.current
    if addr:
      return self.locoMap[addr]

  def getLocoMap(self):
    return self.locoMap

  def set(self, addr):
    if addr in self.locoMap:
      self.current = addr

  def add(self, loco):
    logging.error(f'Add = {loco}')
    self.locoMap[loco.addr] = loco
    loco.mqttClient = self.mqttClient
    if self.current == None:
      self.current = loco.addr
      logging.error(f'Current = {self.current}')

  def start(self):
    logging.error('Command Start')
    self.mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "RRPop")
    self.mqttClient.on_message = self.on_message
    self.mqttClient.connect('127.0.0.1')
    self.mqttClient.subscribe(f'{MQTT_PREFIX_WEB}/#')
    self.mqttClient.loop_start()

  def stop(self):
    self.mqttClient.loop_stop()

  def on_message(self, client, userdata, msg):
      payload = str(msg.payload, 'UTF-8')
      subTopic = msg.topic[len(MQTT_PREFIX_WEB + '/'):]
      locoAddr, subTopic = subTopic.split('/', 1)

      # logging.info(f"MQTT GET {locoAddr}/{subTopic}: {payload}")
      if subTopic == 'fileds':
        payload = payload.split()
        loco = Loco(locoAddr, payload[0], payload[1:])
        self.add(loco)
      elif subTopic == 'data':
        loco = self.get(locoAddr)
        if loco:
          loco.updateData(payload.split())


command = Command()
