import re
import struct
import logging
import Wireless
import paho.mqtt.client as mqtt
from paho.mqtt.subscribeoptions import SubscribeOptions




MQ_MESSAGE = re.compile("cab/(.*?)/(.*)")
MQ_PREFIX = "cab"
MQ_INTRO = "intro"
MQ_SET_THROTTLE = "throttle";
MQ_SET_DIRECTION = "direction";
MQ_HEARTBEAT_VALUES = "heartbeat/values"
MQ_GET_FUNCTION = "function/get"
MQ_SET_FUNCTION = "function/"
MQ_GET_VALUE = "value/get"
MQ_LIST_VALUE = "value/list"
MQ_SET_VALUE = "value/"

MQ_DIRECTIONS = ["REVERSE", "FORWARD", "STOP", "NEUTRAL"]
MQ_ON = "ON"
MQ_OFF = "OFF"


NRF_INTRO = 'A'
NRF_SUB = 'B'
NRF_LIST_CAB = 'C'
NRF_HEARTBEAT = 'H'

NRF_THROTTLE = 'T'
NRF_DIRECTION = 'D'
NRF_SET_FUNCTION = 'F'
NRF_GET_FUNCTION = 'P'
NRF_SET_VALUE = 'S'
NRF_GET_VALUE = 'G'
NRF_LIST_VALUE = 'L'

MQTT_NODE_NAME = 'RCC_Station'
MQTT_BROKER = '127.0.0.1'
NRF_PINS = (25, 8)


def toInt(value):
    try:
        return int(value)
    except:
        return 0


class TransportNrf:
    def __init__(self):
        self.known = {}
        self.subscription = {}
        self.wireless = Wireless.Wireless(*NRF_PINS)
        self.wireless.onReceive = self.onReceive

    def write(self, addr, message):
        logging.debug(f"[NF] >: {addr}/{message}")
        self.wireless.write(addr, message)

    def writeToSubsribed(self, addr, message):
        subscribed = self.subscription.get(addr, None)
        if subscribed:
            self.write(subscribed, message)

    def askToIntro(self, addr):
        self.write(addr, struct.pack('<BB', ord(NRF_INTRO), 0))

    def parseIntro(self, message):
        fields = message.split()
        m = { "Type": fields[0], "Addr": fields[1], "Name": fields[2], "Version": fields[3] }
        if len(fields) > 4:
            m["Format"] = fields[4]
        return m

    def processListCab(self, addr):
        p = ' '.join( [f'{fields["Type"]} {fields["Addr"]} {fields["Name"]}' for addr, fields in self.known.items()] )
        p = struct.pack(f'<B{len(p)}s', ord(NRF_LIST_CAB), p.encode())
        self.write(addr, p)        

    def processSub(self, addr, subTo):
        addr = int(addr)
        subTo = int(subTo)
        self.subscription[addr] = subTo
        self.subscription[subTo] = addr

    def setThrottle(self, addr, value):
        p = struct.pack('<BB', ord(NRF_THROTTLE), value)
        self.write(addr, p)
        self.writeToSubsribed(addr, p)

    def setDirection(self, addr, value):
        p = struct.pack('<BB', ord(NRF_DIRECTION), value)
        self.write(addr, p)
        self.writeToSubsribed(addr, p)

    def getFunction(self, addr, value):
        p = struct.pack('<BB', ord(NRF_GET_FUNCTION), int(value))
        self.write(addr, p)

    def setFunction(self, addr, functionId, activate):
        value = int(functionId) & 0x7F
        if activate:
            value |= (1 << 7)
        p = struct.pack('<BB', ord(NRF_SET_FUNCTION), value)
        self.write(addr, p)

    def getValue(self, addr, value):
        key = value.encode()
        k = len(key)        
        p = struct.pack(f'<BB{k}sB', ord(NRF_GET_VALUE), k, key, 0)
        self.write(addr, p)
    
    def listValue(self, addr):
        p = struct.pack('<BB', ord(NRF_LIST_VALUE), 0)
        self.write(addr, p)
    
    def setValue(self, addr, key, value):
        key = key.encode()
        value = value.encode()
        k = len(key)
        v = len(value)
        p = struct.pack(f'<BB{k}sB{v}sB', ord(NRF_SET_VALUE), len(key), key, 0, value, 0)
        self.write(addr, p)

    def start(self):
        self.wireless.start()

    def onReceive(self, addr, message):
        if len(message) < 2:
            return

        logging.debug(f"[NF] <: {addr}/{message}")
        packetType = chr(message[0])

        if packetType == NRF_INTRO:
            m = str(message[2:], 'utf-8')
            self.known[addr] = self.parseIntro(m)
            mq.processIntro(addr, m)
        elif addr not in self.known:
            self.askToIntro(addr)
        elif packetType == NRF_LIST_CAB:
            self.processListCab(addr)
        elif packetType == NRF_SUB:
            self.processSub(addr, message[1])
        elif packetType == NRF_HEARTBEAT:
            fmt = '<' + self.known[addr]["Format"];
            size = struct.calcsize(fmt)
            if len(message) == size:
                unpacked = struct.unpack(fmt, message)[1:]
                nice = ' '.join( [f'{x}' for x in unpacked] ) 
                mq.processHeartBeat(addr, nice)
                self.writeToSubsribed(addr, message)
        elif packetType == NRF_THROTTLE:
            self.writeToSubsribed(addr, message)
            mq.setThrottle(addr, message[1])
        elif packetType == NRF_DIRECTION:
            self.writeToSubsribed(addr, message)
            mq.setDirection(addr, message[1])
        elif packetType == NRF_GET_FUNCTION:
            self.writeToSubsribed(addr, message)
            mq.getFunction(addr, message[1])
        elif packetType == NRF_SET_FUNCTION:
            self.writeToSubsribed(addr, message)
            functionId = message[1] & 0x7F
            activate = message[1] & 0x80
            mq.setFunction(addr, functionId, activate)
        elif packetType == NRF_GET_VALUE:
            self.writeToSubsribed(addr, message)
            mq.getValue(addr, message[1])
        elif packetType == NRF_GET_VALUE:
            self.writeToSubsribed(addr, message)
            k = len(message) - 3
            unpacked = struct.unpack(f'<BB{k}sB', message)
            key = unpacked[2].decode()
            mq.getValue(addr, key)
        elif packetType == NRF_SET_VALUE:
            self.writeToSubsribed(addr, message)
            unpacked = struct.unpack('<BB', message[:2])
            k = toInt(unpacked[1])
            v = len(message) - 2 - k - 2
            unpacked = struct.unpack(f'<BB{k}sB{v}sB', message)
            key = unpacked[2].decode()
            value = unpacked[4].decode()            
            mq.setValue(addr, key, value)
        else:
            logging.error(f"Unknown packet type: {packetType}")

class TransportMqtt:
    def __init__(self):
        self.mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, MQTT_NODE_NAME)
        self.mqttClient.on_message = self.onReceive
        self.cache = ""

    def start(self):
        self.mqttClient.connect(MQTT_BROKER)
        options = SubscribeOptions(qos = 1, noLocal = True)
        self.mqttClient.subscribe(f'{MQ_PREFIX}/#', options=options)
        self.mqttClient.loop_forever()

    def write(self, topic, message, retain = False):
        logging.info(f"[MQ] >: {topic} {message}")
        self.cache = f"{topic} {message}"
        self.mqttClient.publish(topic, message, retain)

    def processIntro(self, addr, message):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_INTRO}"
        self.write(topic, message, retain = True)

    def processHeartBeat(self, addr, message):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_HEARTBEAT_VALUES}"
        self.write(topic, message)

    def setThrottle(self, addr, value):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_SET_THROTTLE}"
        self.write(topic, value)

    def setDirection(self, addr, value):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_SET_DIRECTION}"
        if value < len(MQ_DIRECTIONS):
            value = MQ_DIRECTIONS[value]
            self.write(topic, value)

    def getFunction(self, addr, functionId):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_GET_FUNCTION}"
        self.write(topic, functionId)

    def setFunction(self, addr, functionId, activate):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_SET_FUNCTION}{functionId}"
        activate = MQ_ON if activate else MQ_OFF
        self.write(topic, activate)

    def getValue(self, addr, key):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_GET_VALUE}"
        self.write(topic, key)

    def listValue(self, addr):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_LIST_VALUE}"
        self.write(topic, "")
    
    def setValue(self, addr, key, value):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_SET_VALUE}{key}"
        self.write(topic, value)


    def onReceive(self, client, userdata, msg):
        topic = MQ_MESSAGE.match(msg.topic)
        if (topic is None):
            return

        message = str(msg.payload, 'UTF-8')
        cache = f"{msg.topic} {message}"
        if cache == self.cache:
            return
        logging.debug(f"[MQ] <: {msg.topic} {message}")
        addr, action = topic.groups()

        if action == MQ_SET_THROTTLE:
            nrf.setThrottle(addr, toInt(message))
        elif action == MQ_SET_DIRECTION:
            for i, s in enumerate(MQ_DIRECTIONS):
                if message == s or message == str(i):
                    nrf.setDirection(addr, i)
                    break
        elif action == MQ_GET_FUNCTION:
            nrf.getFunction(addr, message)
        elif action.startswith(MQ_SET_FUNCTION):
            functionId = toInt(action.split('/')[1])
            nrf.setFunction(addr, functionId, message == MQ_ON)
        elif action == MQ_GET_VALUE:
            nrf.getValue(addr, message)
        elif action == MQ_LIST_VALUE:
            nrf.listValue(addr)
        elif action.startswith(MQ_SET_VALUE):
            nrf.setValue(addr, action.split('/')[1], message)





logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    filename='comms.log',
                    filemode='a')
logging.error('Start')

nrf = TransportNrf()
mq = TransportMqtt()

nrf.start()
mq.start()
