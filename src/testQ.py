import re, struct

MQ_MESSAGE = re.compile("cab/(.*?)/(.*)")
MQ_DIRECTIONS = ["REVERSE", "FORWARD", "STOP", "NEUTRAL"]

NRF_SEPARATOR = ' '
NRF_TYPE_LOCO = 'L'
NRF_TYPE_KEYPAD = 'K'
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

def introToNrf(k, v):
    t.processIntro(v)
    return bytes(v, 'utf-8')

def introToMq(x):
    x = x.decode()
    t.processIntro(x)
    return '', x

def heartbeatToNrf(k, v):
    fmt = '<' + t.getHeartbeatFmt()
    unpacked = [int(i) for i in v.split()]
    return struct.pack(fmt, *unpacked)

def heartbeatToMq(v):
    fmt = '<' + t.getHeartbeatFmt()
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
    RouteEntry('A',  introToNrf,        'intro',             introToMq         ),
    RouteEntry('H',  heartbeatToNrf,    'heartbeat/values',  heartbeatToMq     ),
    RouteEntry('J',  '{value}',         'keys',              '{value}'         ),
    RouteEntry('T',  '{intvalue}',      'throttle',          '{intvalue}',     ),
    RouteEntry('D',  directionToNrf,    'direction',         directionToMq     ),
    RouteEntry('P',  '{intvalue}',      'function/get',      '{intvalue}'         ),
    RouteEntry('F',  functionToNrf,     'function/{key}',    functionToMq,     ),
    RouteEntry('L',  lambda x,y: 0,     'value/list',        lambda x: ('','') ),
    RouteEntry('J',  '{value}',         'keys',              '{value}'         ),
    RouteEntry('G',  '{value}',         'value/get',         '{value}'         ),
    RouteEntry('S',  '{key} {value}',   'value/{key}',       '{value}'         ),
]




class Translator:
    def __init__(self,):
        self.addr = 0

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
            return bytes(entry.nrf[0], 'utf-8') + bytes([int(value)])
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

    def toNrf(self, addr, action, message):
        for entry in PROTO_MAP:
            a = entry.mq[2].match(action)
            if a:
                key = self.getKey(a)
                nrf = self.buildNrf(entry, key, message)
                if nrf:
                    return nrf

    def toMq(self, action, message):
        if action == NRF_SUB:
            t.processSub(message)
        elif action == NRF_LIST_CAB:
            t.processListCab(message)
        else:
            for entry in PROTO_MAP:
                if ord(entry.nrf[0]) == action:
                    nrf = self.buildMq(entry, message)
                    if nrf:
                        return nrf




    def processIntro(self, message):
        pass
        # print(">>>>>>>1>", message.split(' '))
        # fields = message.split()
        # m = { "Type": fields[0], "Addr": fields[1], "Name": fields[2], "Version": fields[3] }
        # if len(fields) > 4:
        #     m["Format"] = fields[4]
        # self.known[addr] = m

    def processSub(self, message):
        print(">>>>>>>2>", message)

    def processListCab(self, message):
        print(">>>>>>>3>", message)

    def getHeartbeatFmt(self):
        # return self.known[addr]["Format"]
        return 'BB'


t = Translator()






testProtocolData = [
('cab/3/throttle+99',           b'Tc'),
('cab/3/function/get+2',        b'P\x02'),
('cab/3/function/3+ON',         b'F\x83'),
('cab/3/function/3+OFF',        b'F\x03'),
('cab/3/value/get+zupa',        b'Gzupa'),
('cab/3/value/zupa+abc',        b'Szupa abc'),
('cab/3/value/list+',           b'L'),
('cab/3/direction+FORWARD',     b'D\x01'),
('cab/3/direction+REVERSE',     b'D\x00'),
('cab/3/direction+NEUTRAL',     b'D\x03'),
('cab/3/intro+L 3 Rcc 0.9 B',   b'AL 3 Rcc 0.9 B'),
('cab/3/heartbeat/values+1 2',  b'H\x01\x02'),
]



def testToNrf(incoming):
    topic, message = incoming.split('+')
    topic = MQ_MESSAGE.match(topic)
    addr, action = topic.groups()
    return t.toNrf(addr, action, message)

def testToMq(incoming):
    action, message = (incoming[0], incoming[1:])
    topic, msg = t.toMq(action, message)
    return 'cab/3/' + topic + '+' + msg

def testResult(incoming, outgoing, expected):
    line = f'{incoming}'.ljust(28)
    line += f' ->   {outgoing}'.ljust(38)
    print(line, end='')
    if outgoing == expected:
        print('ok')
    else:
        print('FAIL')

for mq, nrf in testProtocolData:
    nrfAct = testToNrf(mq)
    testResult(mq, nrfAct, nrf)

for mq, nrf in testProtocolData:
    mqAct = testToMq(nrf)
    testResult(nrf, mqAct, mq)
