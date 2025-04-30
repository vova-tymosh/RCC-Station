import re
import struct
import logging
import Wireless
import paho.mqtt.client as mqtt
from paho.mqtt.subscribeoptions import SubscribeOptions



MQ_MESSAGE = re.compile("cab/(.*?)/(.*)")
MQ_PREFIX = "cab"
MQ_INTRO = "intro"
MQ_HEARTBEAT_VALUES = "heartbeat/values"

MQ_SET_THROTTLE = "throttle";
MQ_SET_DIRECTION = "direction";
MQ_GET_FUNCTION = "function/get"
MQ_SET_FUNCTION = "function/"
MQ_GET_VALUE = "value/get"
MQ_SET_VALUE = "value/"
MQ_LIST_VALUE_ASK = "value/list"
MQ_LIST_VALUE_RES = "keys"

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
NRF_LIST_VALUE_ASK = 'L'
NRF_LIST_VALUE_RES = 'J'

NRF_SEPARATOR = ' '
NRF_TYPE_LOCO = 'L'
NRF_TYPE_KEYPAD = 'K'

MQTT_NODE_NAME = 'RCC_Station'
MQTT_BROKER = '127.0.0.1'
NRF_PINS = (25, 8)


def toInt(value):
    try:
        return int(value)
    except:
        return 0

def toStr(value):
    try:
        return str(value, 'utf-8')
    except:
        return ''

class TransportNrf:
    def __init__(self):
        self.known = {}
        self.subscription = {}
        self.wireless = Wireless.Wireless(*NRF_PINS)
        self.wireless.onReceive = self.onReceive

    def write(self, addr, message):
        addr = int(addr)
        logging.debug(f"[NF] >: {addr}/{message}")
        self.wireless.write(addr, message)

    def getSubsribed(self, addr):
        addr = int(addr)
        return self.subscription.get(addr, 0)

    def getProperForward(self, addr):
        k = self.known.get(addr, 0)
        sub = self.getSubsribed(addr)
        if k:
            if k["Type"] == NRF_TYPE_KEYPAD:
                return sub
            else:
                return addr

    def writeToSubsribed(self, addr, message):
        addr = int(addr)
        subscribed = self.subscription.get(addr, None)
        if subscribed:
            self.write(subscribed, message)

    def askToIntro(self, addr):
        self.write(addr, struct.pack('<BB', ord(NRF_INTRO), 0))

    def processIntro(self, addr, message):
        fields = message.split()
        m = { "Type": fields[0], "Addr": fields[1], "Name": fields[2], "Version": fields[3] }
        if len(fields) > 4:
            m["Format"] = fields[4]
        self.known[addr] = m

    def processListCab(self, addr):
        p = NRF_SEPARATOR.join( [f'{fields["Type"]} {fields["Addr"]} {fields["Name"]}' for addr, fields in self.known.items()] )
        p = struct.pack(f'<B{len(p)}s', ord(NRF_LIST_CAB), p.encode())
        self.write(addr, p)

    def processSub(self, addr, subTo):
        addr = int(addr)
        subTo = int(subTo)
        self.subscription[addr] = subTo
        self.subscription[subTo] = addr

    def processHeartbeat(self, addr, items):
        fmt = '<' + self.known[addr]["Format"]
        unpacked = [ord(NRF_HEARTBEAT)]
        for i in items:
            unpacked.append(int(i))
        p = struct.pack(fmt, *unpacked)
        self.writeToSubsribed(addr, p)

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
        p = struct.pack(f'<B{k}s', ord(NRF_GET_VALUE), key)
        self.write(addr, p)

    def listValueAsk(self, addr):
        p = struct.pack('<BB', ord(NRF_LIST_VALUE_ASK), 0)
        self.write(addr, p)

    def listValueRes(self, addr, value):
        value = value.encode()
        s = len(value)
        p = struct.pack(f'<B{s}s', ord(NRF_LIST_VALUE_RES), value)
        self.write(addr, p)

    def setValue(self, addr, key, value):
        key = key.encode()
        value = value.encode()
        k = len(key)
        v = len(value)
        p = struct.pack(f'<B{k}sB{v}s', ord(NRF_SET_VALUE), key, ord(NRF_SEPARATOR), value)
        self.write(addr, p)

    def start(self):
        self.wireless.start()

    def onReceive(self, addr, message):
        if len(message) < 2:
            return

        logging.debug(f"[NF] <: {addr}/{message}")
        packetType = chr(message[0])

        if packetType == NRF_INTRO:
            m = toStr(message[1:])
            self.processIntro(addr, m)
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
                mq.processHeartbeat(addr, unpacked)
                self.writeToSubsribed(addr, message)
        elif packetType == NRF_THROTTLE:
            sub = self.getSubsribed(addr)
            if sub:
                self.write(sub, message)
                mq.setThrottle(sub, message[1])
        elif packetType == NRF_DIRECTION:
            sub = self.getSubsribed(addr)
            if sub:
                self.write(sub, message)
                mq.setDirection(sub, message[1])
        elif packetType == NRF_GET_FUNCTION:
            sub = self.getSubsribed(addr)
            if sub:
                self.write(sub, message)
            if sub:
                mq.getFunction(sub, message[1])
        elif packetType == NRF_SET_FUNCTION:
            sub = self.getSubsribed(addr)
            if sub:
                self.write(sub, message)
            functionId = message[1] & 0x7F
            activate = message[1] & 0x80
            fwd = self.getProperForward(addr)
            mq.setFunction(fwd, functionId, activate)
        elif packetType == NRF_LIST_VALUE_ASK:
            sub = self.getSubsribed(addr)
            if sub:
                self.write(sub, message)
                mq.listValueAsk(sub)
        elif packetType == NRF_LIST_VALUE_RES:
            m = toStr(message[1:])
            self.writeToSubsribed(addr, message)
            mq.listValueRes(addr, m)
        elif packetType == NRF_GET_VALUE:
            sub = self.getSubsribed(addr)
            if sub:
                self.write(sub, message)
            if sub:
                k = len(message) - 1
                unpacked = struct.unpack(f'<B{k}s', message)
                key = toStr(unpacked[1])
                mq.getValue(sub, key)
        elif packetType == NRF_SET_VALUE:
            sub = self.getSubsribed(addr)
            if sub:
                self.write(sub, message)
            s = len(message) - 1
            unpacked = struct.unpack(f'<B{s}s', message)
            unpacked = toStr(unpacked[1])
            key, value = unpacked.split(NRF_SEPARATOR)
            fwd = self.getProperForward(addr)
            mq.setValue(fwd, key, value)
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

    def processHeartbeat(self, addr, items):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_HEARTBEAT_VALUES}"
        message = NRF_SEPARATOR.join( [f'{x}' for x in items] )
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

    def listValueAsk(self, addr):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_LIST_VALUE_ASK}"
        self.write(topic, "")

    def listValueRes(self, addr, value):
        topic = f"{MQ_PREFIX}/{addr}/{MQ_LIST_VALUE_RES}"
        self.write(topic, value)

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


        if action == MQ_INTRO:
            nrf.processIntro(addr, message)
        elif action == MQ_HEARTBEAT_VALUES:
            nrf.processHeartbeat(addr, message.split(NRF_SEPARATOR))
        elif action == MQ_SET_THROTTLE:
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
        elif action == MQ_LIST_VALUE_ASK:
            nrf.listValueAsk(addr)
        elif action == MQ_LIST_VALUE_RES:
            nrf.listValueRes(addr, message)
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
