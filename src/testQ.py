import re

MQ_MESSAGE = re.compile("cab/(.*?)/(.*)")
MQ_DIRECTIONS = ["REVERSE", "FORWARD", "STOP", "NEUTRAL"]




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

def introToNr(x):
    t.processIntro(x)
    return x

def introToMq(k, v):
    t.processIntro(x)
    return '', v.decode()



class RouteEntry:
    def __init__(self, nrTopic, nrMessage, mqTopic, mqMessage):
        self.nrf = [nrTopic, nrMessage, self.toRe(nrMessage)]
        self.mq = [mqTopic, mqMessage, self.toRe(mqTopic)]

    def toRe(self, value):
        if type(value) == str:
            value = value.replace('{key}', '(?P<key>.*)').replace('{value}', '(?P<value>.*)')
            return re.compile(value)

PROTO_MAP = [ \
    RouteEntry('A',  introToNr,         'intro',             introToMq         ),
    # RouteEntry('B',  None,              '',                  subMq             ),
    # RouteEntry('C',  None,              '',                  listCabsMq        ),
    # RouteEntry('H',  heartbeatToNr,     'heartbeat/values',  heartbeatToMq     ),
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






def getKey(keyMatch):
    if keyMatch:
        d = keyMatch.groupdict()
        return d.get('key', '')
    return ''

def getKeyValue(inputRe, inputData):
    match = inputRe.match(inputData)
    if match:
        d = match.groupdict()
        return d.get('key', ''), d.get('value', '')
    return '', ''    

def fromMq(action, message):
    for entry in PROTO_MAP:
        a = entry.mq[2].match(action)
        if a:
            key = getKey(a)
            nrf = buildNrf(entry, key, message)
            if nrf:
                return nrf

def buildNrf(entry, key, value):
    output = entry.nrf[1]
    if callable(output):
        return bytes(entry.nrf[0], 'utf-8') + bytes(output(key, value))
    elif output == '{intvalue}':
        return bytes(entry.nrf[0], 'utf-8') + bytes([int(value)])
    else:
        output = output.replace('{key}', key).replace('{value}', value)
        return bytes(entry.nrf[0], 'utf-8') + bytes(output, 'utf-8')


def fromNrf(action, message):
    for entry in PROTO_MAP:
        if ord(entry.nrf[0]) == action:
            nrf = buildMq(entry, message)
            if nrf:
                return nrf

def buildMq(entry, value):
    output = entry.mq[1]
    if callable(output):
        key, value = output(value)
        return entry.mq[0].replace('{key}', key) + '+' + value
    elif output == '{intvalue}':
        value = ord(value)
        return entry.mq[0] + '+' + str(value)
    else:
        key, value = getKeyValue(entry.nrf[2], value.decode())
        return entry.mq[0].replace('{key}', key) + '+' + entry.mq[1].replace('{value}', value)
    return None


class Translator:
    def __init__(self,):
        self.theMap = ''

    def processIntro(self, message):
        print(">>>>>>>>", message)
        # fields = message.split()
        # m = { "Type": fields[0], "Addr": fields[1], "Name": fields[2], "Version": fields[3] }
        # if len(fields) > 4:
        #     m["Format"] = fields[4]
        # self.known[addr] = m

t = Translator()






testProtocolData = [
('cab/3/throttle+99',       b'Tc'),
('cab/3/function/get+2',    b'P\x02'),
('cab/3/function/3+ON',     b'F\x83'),
('cab/3/function/3+OFF',    b'F\x03'),
('cab/3/value/get+zupa',    b'Gzupa'),
('cab/3/value/zupa+abc',    b'Szupa abc'),
('cab/3/value/list+',       b'L'),
('cab/3/direction+FORWARD', b'D\x01')
]



def testToNrf(incoming):
    topic, message = incoming.split('+')
    topic = MQ_MESSAGE.match(topic)
    addr, action = topic.groups()
    return fromMq(action, message)

def testToMq(incoming):
    action, message = (incoming[0], incoming[1:])
    return 'cab/3/' + fromNrf(action, message)

def testResult(incoming, outgoing, expected):
    line = f'{incoming}'.ljust(25)
    line += f' ->   {outgoing}'.ljust(38)
    print(line, end='')
    if outgoing == expected:
        print('ok')
    else:
        print('FAIL')

for mq, nrf in testProtocolData:
    nrfAct = testToNrf(mq)
    testResult(mq, nrfAct, nrf)
    mqAct = testToMq(nrf)
    testResult(nrf, mqAct, mq)
