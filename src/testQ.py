import re
import struct
import logging
import Wireless
import paho.mqtt.client as mqtt
from paho.mqtt.subscribeoptions import SubscribeOptions

MQTT_BROKER = '127.0.0.1'
MQTT_NODE_NAME = 'RCC_Station'
NRF_PINS = (25, 8)

MQ_MESSAGE = re.compile("cab/(.*?)/(.*)")
MQ_PREFIX = "cab"
MQ_DIRECTIONS = ["REVERSE", "FORWARD", "STOP", "NEUTRAL"]
NRF_SEPARATOR = ' '
NRF_TYPE_LOCO = 'L'
NRF_TYPE_KEYPAD = 'K'
NRF_INTRO = 'A'
NRF_SUB = 'B'
NRF_LIST_CAB = 'C'

def functionToNrf(k, v):
    return [(int(k) & 0x7F) | (1 << 7 if v == 'ON' else 0)]

def functionToMq(x):
    return str(ord(x) & 0x7F), ('ON' if ord(x) & 0x80 else 'OFF')

def directionToNrf(k, v):
    for i, s in enumerate(MQ_DIRECTIONS):
        if v == s or v == str(i):
            return [i]
    return [1]

def directionToMq(x):
    i = int(x[0])
    if i < len(MQ_DIRECTIONS):
        return '', MQ_DIRECTIONS[i]
    return '', str(x)

def heartbeatToNrf(k, v):
    fmt = '<' + broker.getHeartbeatFmt()
    unpacked = [int(i) for i in v.split()]
    return struct.pack(fmt, *unpacked)

def heartbeatToMq(v):
    fmt = '<' + broker.getHeartbeatFmt()
    size = struct.calcsize(fmt)
    if len(v) == size:
        unpacked = struct.unpack(fmt, v)
        return '', NRF_SEPARATOR.join( [f'{i}' for i in unpacked] )


class RouteEntry:
    def __init__(self, nrTopic, nrMessage, mqTopic, mqMessage):
        self.nrf = [nrTopic, nrMessage, self.toRe(nrMessage)]
        self.mq = [mqTopic, mqMessage, self.toRe(mqTopic)]

    def toRe(self, value):
        if type(value) == str:
            value = value.replace('{key}', '(?P<key>.*)').replace('{value}', '(?P<value>.*)')
            return re.compile(value)

PROTO_MAP = [ \
    RouteEntry('A',  '{value}',         'intro',             '{value}'         ),
    RouteEntry('H',  heartbeatToNrf,    'heartbeat/values',  heartbeatToMq     ),
    RouteEntry('J',  '{value}',         'keys',              '{value}'         ),
    RouteEntry('T',  '{intvalue}',      'throttle',          '{intvalue}',     ),
    RouteEntry('D',  directionToNrf,    'direction',         directionToMq     ),
    RouteEntry('P',  '{intvalue}',      'function/get',      '{intvalue}'      ),
    RouteEntry('F',  functionToNrf,     'function/{key}',    functionToMq,     ),
    RouteEntry('L',  lambda x,y: 0,     'value/list',        lambda x: ('','') ),
    RouteEntry('J',  '{value}',         'keys',              '{value}'         ),
    RouteEntry('G',  '{value}',         'value/get',         '{value}'         ),
    RouteEntry('S',  '{key} {value}',   'value/{key}',       '{value}'         ),
]




class Translator:
    def toInt(self, x):
        try:
            return abs(int(x))
        except:
            return 0

    def getKey(self, keyMatch):
        if keyMatch:
            d = keyMatch.groupdict()
            return d.get('key', '')
        return ''

    def getKeyValue(self, inputRe, inputData):
        match = inputRe.match(inputData)
        if match:
            d = match.groupdict()
            return d.get('key', ''), d.get('value', '')
        return '', ''

    def buildNrf(self, entry, key, value):
        output = entry.nrf[1]
        if callable(output):
            return bytes(entry.nrf[0], 'utf-8') + bytes(output(key, value))
        elif output == '{intvalue}':
            return bytes(entry.nrf[0], 'utf-8') + bytes([self.toInt(value)])
        else:
            output = output.replace('{key}', key).replace('{value}', value)
            return bytes(entry.nrf[0], 'utf-8') + bytes(output, 'utf-8')

    def buildMq(self, entry, value):
        output = entry.mq[1]
        if callable(output):
            key, value = output(value)
            return entry.mq[0].replace('{key}', key), value
        elif output == '{intvalue}':
            value = ord(value)
            return entry.mq[0], str(value)
        else:
            key, value = self.getKeyValue(entry.nrf[2], value.decode())
            return entry.mq[0].replace('{key}', key), entry.mq[1].replace('{value}', value)
        return None

    def toNrf(self, action, message):
        for entry in PROTO_MAP:
            a = entry.mq[2].match(action)
            if a:
                key = self.getKey(a)
                nrf = self.buildNrf(entry, key, message)
                if nrf:
                    return nrf

    def toMq(self, action, message):
        for entry in PROTO_MAP:
            if ord(entry.nrf[0]) == action:
                nrf = self.buildMq(entry, message)
                if nrf:
                    return nrf


class Broker:

    def __init__(self):
        self.known = {}
        self.subscription = {}

    def askToIntro(self, addr):
        nrf.write(addr, struct.pack('<BB', ord(NRF_INTRO), 0))

    def processIntro(self, addr, message):
        fields = message.split()
        m = { "Type": fields[0], "Addr": fields[1], "Name": fields[2], "Version": fields[3] }
        if len(fields) > 4:
            m["Format"] = fields[4]
        self.known[addr] = m

    def processSub(self, addr, subTo):
        addr = int(addr)
        subTo = int(subTo)
        self.subscription[addr] = subTo
        self.subscription[subTo] = addr

    def processListCab(self, message):
        p = NRF_SEPARATOR.join( [f'{fields["Type"]} {fields["Addr"]} {fields["Name"]}' for addr, fields in self.known.items()] )
        p = struct.pack(f'<B{len(p)}s', ord(NRF_LIST_CAB), p.encode())
        nrf.write(addr, p)

    def getHeartbeatFmt(self):
        return self.known[self.addr]["Format"]

    def getForwardNrf(self, addr):
        addr = int(addr)
        return self.subscription.get(addr, 0)

    def getForwardMq(self, addr):
        k = self.known.get(addr, 0)
        sub = self.getForwardNrf(addr)
        if k:
            return sub if k["Type"] == NRF_TYPE_KEYPAD else addr

    def receiveNrf(self, addr, action, message):
        if addr not in self.known and action != NRF_INTRO:
            self.askToIntro(addr)
            return
        if action == NRF_SUB:
            self.processSub(addr, message[1])
            return
        if action == NRF_LIST_CAB:
            self.processListCab(message)
            return

        if action == NRF_INTRO:
            self.processIntro(addr, message)
        self.addr = addr
        fwdPacket = translator.toMq(action, message)
        fwdMqAddr = self.getForwardMq(addr)
        mq.write(fwdMqAddr, fwdPacket)
        fwdNrfAddr = self.getForwardNrf(addr)
        if fwdNrfAddr:
            nrf.write(fwdNrfAddr, message)

    def receiveMq(self, addr, action, message):
        self.addr = addr
        fwdPacket = translator.toNrf(action, message)
        fwdNrfAddr = self.getForwardNrf(addr)
        if fwdNrfAddr:
            nrf.write(fwdNrfAddr, fwdPacket)



class TransportNrf:
    def __init__(self):
        self.wireless = Wireless.Wireless(*NRF_PINS)
        self.wireless.onReceive = self.onReceive

    def start(self):
        self.wireless.start()

    def write(self, addr, message):
        addr = int(addr)
        logging.debug(f"[NF] >: {addr}/{message}")
        self.wireless.write(addr, message)

    def onReceive(self, addr, packet):
        if len(message) < 2:
            return
        logging.debug(f"[NF] <: {addr}/{message}")
        broker.receiveNrf(addr, chr(packet[0]), packet[1:])


class TransportMqtt:
    def __init__(self):
        self.mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, MQTT_NODE_NAME)
        self.mqttClient.on_message = self.onReceive
        self.cache = ''

    def start(self):
        self.mqttClient.connect(MQTT_BROKER)
        options = SubscribeOptions(qos = 1, noLocal = True)
        self.mqttClient.subscribe(f'{MQ_PREFIX}/#', options = options)
        self.mqttClient.loop_forever()

    def write(self, topic, message, retain = False):
        logging.info(f"[MQ] >: {topic} {message}")
        self.cache = f"{topic} {message}"
        self.mqttClient.publish(topic, message, retain)

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
        broker.receiveMq(addr, action, message)


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    filename='comms.log',
                    filemode='a')
logging.error('Start')

translator = Translator()
broker = Broker()
nrf = TransportNrf()
mq = TransportMqtt()

nrf.start()
mq.start()
