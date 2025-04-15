import re
import sys
import time
import struct
import logging
import Wireless
import paho.mqtt.client as mqtt
from paho.mqtt.subscribeoptions import SubscribeOptions
#from Config import MQTT_PREFIX_WEB, MQTT_PREFIX_JMRI

# packetLocoAuth = 'r'
# packetLocoNorm = 'n'
# packetThrAuth = 'q'
# packetThrSub = 's'
# packetThrNorm = 'p'


# commandThrottle  = 't'
# commandDirection = 'd'
# commandLight     = '@'







"""
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

"""

mqMessage = re.compile("cab/(.*?)/(.*)")
mqPrefix = "cab"
mqIntro = "intro"
mqSetThrottle = "throttle";
mqSetDirection = "direction";
mqHeartbeatValues = "heartbeat/values"
mqGetFunction = "function/get"
mqSetFunction = "function"
mqGetValue = "value/get"
mqListValue = "value/list"
mqSetValue = "value"
mqKeysValue = "cab/{0}/value/keys"

directions = ["REVERSE", "FORWARD", "STOP", "NEUTRAL"];
functionON = "ON";


CMD_INTRO = 'A';
CMD_HEARTBEAT = 'H';

CMD_THROTTLE = 'T';
CMD_DIRECTION = 'D';
CMD_SET_FUNCTION = 'F';
CMD_GET_FUNCTION = 'P';
CMD_SET_VALUE = 'S';
CMD_GET_VALUE = 'G';
CMD_LIST_VALUE = 'L';


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
        self.run = True
        self.known = {}
        self.subscription = {}
        self.wireless = Wireless.Wireless(*NRF_PINS)
        self.wireless.onReceive = self.onReceive

    def write(self, addr, message):
        logging.debug(f"[NF] >: {addr}: {message}")
        self.wireless.write(addr, message)

    def writeToSubsribed(self, addr, message):
        subscribed = self.subscription.get(addr, None)
        if subscribed:
            self.write(subscribed, message)

    def askToIntro(self, addr):
        self.write(addr, struct.pack('<BB', ord(CMD_INTRO), 0))

    def parseIntro(self, message):
        fields = message.split()
        return {"Version": fields[0], "Format" : fields[1]}

    def setThrottle(self, addr, value):
        p = struct.pack('<BB', ord(CMD_THROTTLE), value)
        self.write(addr, p)
        self.writeToSubsribed(addr, p)

    def setDirection(self, addr, value):
        p = struct.pack('<BB', ord(CMD_DIRECTION), value)
        self.write(addr, p)
        self.writeToSubsribed(addr, p)

    def getFunction(self, addr, value):
        p = struct.pack('<BB', ord(CMD_GET_FUNCTION), int(value))
        self.write(addr, p)

    def setFunction(self, addr, functionId, activate):
        value = int(functionId) & 0x7F
        if activate:
            value |= (1 << 7)
        p = struct.pack('<BB', ord(CMD_GET_FUNCTION), value)
        self.write(addr, p)

    def getValue(self, addr, value):
        key = value.encode()
        k = len(key)        
        p = struct.pack(f'<BB{k}sB', ord(CMD_GET_VALUE), k, key, 0)
        self.write(addr, p)
    
    def listValue(self, addr):
        p = struct.pack('<BB', ord(CMD_LIST_VALUE), 0)
        self.write(addr, p)
    
    def setValue(self, addr, key, value):
        key = key.encode()
        value = value.encode()
        k = len(key)
        v = len(value)
        p = struct.pack(f'<BB{k}sB{v}sB', ord(CMD_SET_VALUE), len(key), key, 0, value, 0)
        self.write(addr, p)
        

    def start(self):
        self.wireless.start()

    def onReceive(self, addr, message):
        if len(message) < 2:
            return

        logging.debug(f"[NF] <: {addr}/{message}")
        packetType = chr(message[0])

        if packetType == CMD_INTRO:
            m = str(message[2:], 'utf-8')
            self.known[addr] = self.parseIntro(m)
            mq.processIntro(addr, m)
        elif addr not in self.known:
            self.askToIntro(addr)
        elif packetType == CMD_HEARTBEAT:
            fmt = '<' + self.known[addr]["Format"];
            size = struct.calcsize(fmt)
            if len(message) == size:
                unpacked = struct.unpack(fmt, message)[1:]
                nice = ' '.join( [f'{x}' for x in unpacked] ) 
                mq.processHeartBeat(addr, nice)
                self.writeToSubsribed(addr, message)
        elif packetType == CMD_THROTTLE:
            self.writeToSubsribed(addr, message)
            mq.setThrottle(addr, message[1])
        elif packetType == CMD_DIRECTION:
            self.writeToSubsribed(addr, message)
            mq.setDirection(addr, message[1])
        elif packetType == CMD_GET_FUNCTION:
            self.writeToSubsribed(addr, message)
            mq.getFunction(addr, message[1])
        elif packetType == CMD_SET_FUNCTION:
            self.writeToSubsribed(addr, message)
            functionId = message[1] & 0x7F
            activate = message[1] & 0x80
            mq.setFunction(addr, functionId, activate)
        elif packetType == CMD_GET_VALUE:
            self.writeToSubsribed(addr, message)
            mq.getValue(addr, message[1])
        elif packetType == CMD_GET_VALUE:
            self.writeToSubsribed(addr, message)
            k = len(message) - 3
            unpacked = struct.unpack(f'<BB{k}sB', message)
            key = unpacked[2].decode()
            mq.getValue(addr, key)
        elif packetType == CMD_SET_VALUE:
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

    def start(self):
        self.mqttClient.connect(MQTT_BROKER)
        options = SubscribeOptions(noLocal = True)
        self.mqttClient.subscribe(f'{mqPrefix}/#', options=options)
        self.mqttClient.loop_forever()

    def write(self, topic, message, retain = False):
        logging.info(f"[MQ] >: {topic} {message}")
        self.mqttClient.publish(topic, message, retain)

    def processIntro(self, addr, message):
        topic = f"{mqPrefix}/{addr}/{mqIntro}"
        self.write(topic, message, retain = True)

    def processHeartBeat(self, addr, message):
        topic = f"{mqPrefix}/{addr}/{mqHeartbeatValues}"
        self.write(topic, message)

    def setThrottle(self, addr, value):
        topic = f"{mqPrefix}/{addr}/{mqSetThrottle}"
        self.write(topic, value)

    def setDirection(self, addr, value):
        topic = f"{mqPrefix}/{addr}/{mqSetDirection}"
        if value < len(directions):
            value = directions[value]
            self.write(topic, value)

    def getFunction(self, addr, functionId):
        topic = f"{mqPrefix}/{addr}/{mqGetFunction}"
        self.write(topic, functionId)

    def setFunction(self, addr, functionId, activate):
        topic = f"{mqPrefix}/{addr}/{mqSetFunction}/{functionId}"
        activate = "ON" if activate else "OFF"
        self.write(topic, activate)

    def getValue(self, addr, key):
        topic = f"{mqPrefix}/{addr}/{mqGetValue}"
        self.write(topic, key)

    def listValue(self, addr):
        topic = f"{mqPrefix}/{addr}/{mqListValue}"
        self.write(topic, "")
    
    def setValue(self, addr, key, value):
        topic = f"{mqPrefix}/{addr}/{mqSetValue}/{key}"
        self.write(topic, value)


    def onReceive(self, client, userdata, msg):
        topic = mqMessage.match(msg.topic)
        if (topic is None):
            return

        message = str(msg.payload, 'UTF-8')
        logging.debug(f"[MQ] <: {msg.topic} {message}")
        addr, action = topic.groups()

        if action == mqSetThrottle:
            nrf.setThrottle(addr, toInt(message))
        elif action == mqSetDirection:
            for i, s in enumerate(directions):
                if message == s or message == str(i):
                    nrf.setDirection(addr, i)
                    break
        elif action == mqGetFunction:
            nrf.getFunction(addr, message)
        elif action.startswith(mqSetFunction):
            nrf.setFunction(addr, action.split('/')[1], message == "ON")
        elif action == mqGetValue:
            nrf.getValue(addr, message)
        elif action == mqListValue:
            nrf.listValue(addr)
        elif action.startswith(mqSetValue):
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


# w = Wireless.Wireless(25, 8)
# comms = Comms(w)
# cm = CommsMqtt(comms)
# comms.onAuth = cm.onAuth
# comms.onData = cm.onData
# comms.onSetFunction = cm.onSetFunction 
# comms.onSetValue = cm.onSetValue 

# comms.start()
# cm.loop_forever()

# comms.stop()
# logging.error('Stop')

