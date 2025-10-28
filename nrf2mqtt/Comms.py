#
# Copyright (c) 2024-2025 Volodymyr "Vova" Tymoshchuk
# Distributed under MIT licence, https://github.com/vova-tymosh/RCC/blob/main/LICENSE
# For more details go to https://github.com/vova-tymosh/RCC
#
# The above copyright notice shall be included in all
# copies or substantial portions of the Software.
#

import re
import time
import struct
import logging
import paho.mqtt.client as mqtt
from paho.mqtt.subscribeoptions import SubscribeOptions

#
# User config, depends on your HW and Network config
#
MQTT_BROKER = '127.0.0.1'
NRF_PINS = (25, 0)
MQTT_NODE_NAME = 'RCC_Station'

#
# NRF & MQTT protocol definition
#
MQ_MESSAGE = re.compile('cab/(.*?)/(.*)')
MQ_PREFIX = 'cab'
MQ_DIRECTIONS = ['REVERSE', 'FORWARD', 'STOP', 'NEUTRAL']
NRF_SEPARATOR = ','
NRF_TYPE_LOCO = 'L'
NRF_TYPE_KEYPAD = 'K'
NRF_INTRO = 'A'
NRF_SUB = 'B'
NRF_LIST_CAB = 'C'
NRF_HEARTBEAT = 'H'
NRF_PING = '0'
MQ_INTRO = 'intro'
MQ_INTRO_REQ = 'intro/req'

#
# NRF to MQTT and back translation table.
#    First column - Nrf topic (single char)
#    Second column - conversion function with signature (bool toNrf, key, value)
#                    key - present for set commands like setFunction or setValue (name/key of the thing to set). Otherwise empty str
#                    value - a main argument of the command
#    Third column - the MQTT topic suffix (after cab/{addr}/).
#
def buildTrasnlationMap():
    return [
        RouteEntry('A',  translateIntro,        'intro',            ),
        RouteEntry('K',  translateStr,          'heartbeat/keys',   ),
        RouteEntry('H',  translateHeartbeat,    'heartbeat/values', ),
        RouteEntry('H',  translateHeartbeat,    'heartbeat',        ),
        RouteEntry('T',  translateInt,          'throttle',         ),
        RouteEntry('D',  translateDirection,    'direction',        ),
        RouteEntry('U',  translateStr,          'function/list/req',),
        RouteEntry('V',  translateStr,          'function/list',    ),
        RouteEntry('M',  translateValueSet,     'function/name',    ),
        RouteEntry('P',  translateInt,          'function/get',     ),
        RouteEntry('F',  translateFunctionSet,  'function/',        ),
        RouteEntry('L',  translateStr,          'value/list/req',   ),
        RouteEntry('J',  translateStr,          'value/list',       ),
        RouteEntry('G',  translateStr,          'value/get',        ),
        RouteEntry('S',  translateValueSet,     'value/',           ),
    ]

#
# Translation functions, for Nrf returs list of ints, for mqtt a pair of strings (topic suffix and message).
#
def translateIntro(toNrf, k, v):
    if toNrf:
        if k != '/req':
            broker.processIntro(v, 'MQ')
        return bytes(v, 'utf-8')
    else:
        broker.processIntro(v.decode(), 'NRF')
        return '', v.decode()

def translateHeartbeat(toNrf, k, v):
    fmt = broker.getHeartbeatFmt()
    if toNrf:
        if fmt is None or len(v) == 0:
            return bytes([0])
        v = v.split(NRF_SEPARATOR)
        unpacked = [int(i) for i in v]
        return struct.pack(fmt, *unpacked)
    else:
        if fmt is None or struct.calcsize(fmt) != len(v):
            return '', ''
        unpacked = struct.unpack(fmt, v)
        return '', NRF_SEPARATOR.join( [f'{i}' for i in unpacked] )

def translateDirection(toNrf, k, v):
    if toNrf:
        for i, s in enumerate(MQ_DIRECTIONS):
            if v == s or v == str(i):
                return [i]
    else:
        i = int(v[0])
        if i < len(MQ_DIRECTIONS):
            return '', MQ_DIRECTIONS[i]

def translateFunctionSet(toNrf, k, v):
    if toNrf:
        return [(int(k) & 0x7F) | (1 << 7 if v == 'ON' else 0)]
    else:
        return str(ord(v) & 0x7F), ('ON' if ord(v) & 0x80 else 'OFF')

def translateValueSet(toNrf, k, v):
    if toNrf:
        return bytes(f'{k}{NRF_SEPARATOR}{v}', 'utf-8')
    else:
        return v.decode().split(NRF_SEPARATOR)

def translateInt(toNrf, k, v):
    if toNrf:
        try:
            return [abs(int(v))]
        except:
            return None
    else:
        return '', str(ord(v))

def translateStr(toNrf, k, v):
    if toNrf:
        return bytes(v, 'utf-8')
    else:
        return '', v.decode()


#
# Object to store/represent a translation entry (see the translation table abobe)
#
class RouteEntry:
    def __init__(self, nrfTopic, traslateFunc, mqTopic):
        self.nrfTopic = nrfTopic
        self.mqTopic = mqTopic
        self.traslateFunc = traslateFunc

#
# Tranlator mechanism, takes one protocol and translate into another
#
class Translator:
    def __init__(self):
        self.proto_map = buildTrasnlationMap()

    def toNrf(self, action, message):
        for entry in self.proto_map:
            if action.startswith(entry.mqTopic):
                k = action.removeprefix(entry.mqTopic)
                t = entry.traslateFunc(True, k, message)
                if t != None:
                    t = bytes(entry.nrfTopic, 'utf-8') + bytes(t)
                return t

    def toMq(self, action, message):
        for entry in self.proto_map:
            if action == entry.nrfTopic:
                t = entry.traslateFunc(False, '', message)
                if t != None:
                    topic, messageOut = t
                    if entry.mqTopic == 'heartbeat/values' and len(messageOut) == 0:
                        return 'heartbeat', messageOut
                    else:
                        return entry.mqTopic + topic, messageOut

#
# Broker uses tranlator and adds routing capability (which address on Nrf & Mqtt side to route the packet).
#  Also manages intro's and subscriptions of keypads to locos (as part of routing).
#  Expects Nrf data arrive as char for action/topic and bytes for message
#  Expects Mqtt adat to arrive string for both action/topic and message
#
class Broker:
    def __init__(self):
        self.known = {}
        self.subscription = {}

    def updateFmt(self, fmt):
        return '<' + fmt[1:]

    def processIntro(self, message, proto):
        fields = message.split(NRF_SEPARATOR)
        if len(fields) < 4:
            return
        m = { 'Type': fields[0], 'Addr': fields[1], 'Name': fields[2], 'Version': fields[3], 'Proto': proto}
        if len(fields) > 4:
            m['Format'] = self.updateFmt(fields[4])
        if self.addr not in self.known:
            self.known[self.addr] = {}
        self.known[self.addr].update(m)
        logging.info(f'New entry: {self.known[self.addr]}')

    def subscribe(self, addr, subTo):
        subTo = int(subTo)
        if addr in self.subscription and subTo in self.subscription and self.subscription[addr] == subTo and self.subscription[subTo] == addr:
            logging.info(f'Already subscribed: {addr} and {subTo}')
        else:
            self.unsubscribe(addr)
            self.subscription[addr] = subTo
            self.subscription[subTo] = addr
            logging.info(f'Subscribe: {addr} and {subTo}')

    def forget(self, addr):
        logging.info(f'Forget: {addr}')
        if addr in self.known:
            del self.known[addr]

    def unsubscribe(self, addr):
        if addr in self.subscription:
            logging.info(f'Unsubscribe: {addr} and {self.subscription[addr]}')
            subTo = self.subscription[addr]
            del self.subscription[addr]
            if subTo in self.subscription:
                del self.subscription[subTo]

    def processListCab(self, addr):
        p = NRF_LIST_CAB + NRF_SEPARATOR.join( [f"{fields['Type']}{NRF_SEPARATOR}{fields['Addr']}{NRF_SEPARATOR}{fields['Name']}" for addr, fields in self.known.items()] )
        p = bytes(p, 'utf-8')
        nrf.write(addr, p)

    def processPing(self, addr, message):
        p = NRF_PING
        p = bytes(p, 'utf-8') + message
        nrf.write(addr, p)

    def getHeartbeatFmt(self):
        if 'Format' in self.known[self.addr]:
            return self.known[self.addr]['Format']

    def getForwardNrf(self, addr):
        return self.subscription.get(int(addr), 0)

    def getForwardMq(self, addr):
        k = self.known.get(addr, 0)
        if k['Type'] == NRF_TYPE_LOCO:
            return addr
        else:
            sub = self.subscription.get(int(addr), 0)
            return addr if sub == 0 else sub

    def receiveNrf(self, addr, action, message):
        addr = int(addr)
        if addr not in self.known and action != NRF_INTRO:
            nrf.write(addr, bytes([ord(NRF_INTRO), 0]))
            return
        if action == NRF_SUB:
            self.subscribe(addr, message[0])
            return
        if action == NRF_LIST_CAB:
            self.processListCab(addr)
            return
        if action == NRF_PING:
            self.processPing(addr, message)
            return


        self.addr = addr
        fwdPacket = translator.toMq(action, message)
        if fwdPacket is None:
            return
        fwdMqAddr = self.getForwardMq(addr)
        mq.write(fwdMqAddr, fwdPacket)
        fwdNrfAddr = self.getForwardNrf(addr)
        if fwdNrfAddr and self.known[fwdNrfAddr]['Proto'] == 'NRF':
            nrf.write(fwdNrfAddr, bytes(action, 'utf-8') + message)

    def receiveMq(self, addr, action, message):
        addr = int(addr)
        if addr not in self.known and action != MQ_INTRO:
            mq.write(addr, (MQ_INTRO_REQ, ''))
            return
        self.addr = addr
        fwdPacket = translator.toNrf(action, message)
        if fwdPacket is not None:
            if self.known[addr]['Proto'] == 'NRF':
                nrf.write(addr, fwdPacket)
            fwdNrfAddr = self.getForwardNrf(addr)
            if fwdNrfAddr:
                nrf.write(fwdNrfAddr, fwdPacket)

#
# Phisical connection to Nrf
#
class TransportNrf:
    def __init__(self):
        self.wireless = Wireless.Wireless(*NRF_PINS)
        self.wireless.onReceive = self.onReceive

    def start(self):
        self.wireless.start()

    def stop(self):
        self.wireless.stop()

    def write(self, addr, packet):
        addr = int(addr)
        logging.debug(f'[NF] >: {addr}/{packet}')
        self.wireless.write(addr, packet)

    def onReceive(self, addr, packet):
        packet = bytes(packet)
        if len(packet) < 1:
            return
        logging.debug(f'[NF] <: {addr}/{packet}')
        broker.receiveNrf(addr, chr(packet[0]), packet[1:])

#
# Phisical connection to Mqtt
#
class TransportMqtt:
    def __init__(self):
        self.mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTProtocolVersion.MQTTv5,
            client_id = MQTT_NODE_NAME)
        self.mqttClient.on_message = self.onReceive

    def start(self):
        self.mqttClient.connect(MQTT_BROKER)
        options = SubscribeOptions(qos = 1, noLocal = True)
        self.mqttClient.subscribe(f'{MQ_PREFIX}/#', options = options)
        self.mqttClient.loop_start()

    def stop(self):
        self.mqttClient.loop_stop()

    def write(self, addr, packet, retain = False):
        topic = f'{MQ_PREFIX}/{addr}/{packet[0]}'
        message = packet[1]
        logging.debug(f'[MQ] >: {topic} {message}')
        self.mqttClient.publish(topic, message, retain)

    def onReceive(self, client, userdata, msg):
        topic = msg.topic
        message = str(msg.payload, 'utf-8')
        topicRe = MQ_MESSAGE.match(topic)
        if topicRe is None:
            return
        logging.debug(f'[MQ] <: {topic} {message}')
        addr, action = topicRe.groups()
        broker.receiveMq(addr, action, message)


translator = Translator()
broker = Broker()

if __name__ == '__main__':
    import Wireless

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(message)s',
                        filename='comms.log',
                        filemode='a')
    logging.error('Start')

    nrf = TransportNrf()
    mq = TransportMqtt()

    nrf.start()
    mq.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        nrf.stop()
        mq.stop()

    logging.error('Stop')
