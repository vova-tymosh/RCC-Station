from testQ import *


testProtocolBoth = [
('cab/3/throttle+99',           b'Tc'),
('cab/3/function/get+2',        b'P\x02'),
('cab/3/function/3+ON',         b'F\x83'),
('cab/3/function/3+OFF',        b'F\x03'),
('cab/3/value/get+zupa',        b'Gzupa'),
('cab/3/value/zupa+abc',        b'Szupa abc'),
('cab/3/value/list+',           b'L'),
('cab/3/direction+FORWARD',     b'D\x01'),
('cab/3/direction+REVERSE',     b'D\x00'),
('cab/3/direction+STOP',        b'D\x02'),
('cab/3/direction+NEUTRAL',     b'D\x03'),
('cab/3/intro+L 3 Rcc 0.9 B',   b'AL 3 Rcc 0.9 B'),
# ('cab/3/heartbeat/values+1 2',  b'H\x01\x02'),
]

testProtocolMqNegative = [
('cab/3/throttle+a',            None),
('cab/3/throttle+-1',           b'T\x01'),
('cab/3/function/get+a',        None),
('cab/3/value/get+',            b'G'),
('cab/3/value/list+a',          b'La'),
('cab/3/direction+FOR',         None),
]

class Broker:
    def getHeartbeatFmt(self):
        return 'B'

translator = Translator()
broker = Broker()

def testToNrf(incoming):
    topic, message = incoming.split('+')
    topic = MQ_MESSAGE.match(topic)
    addr, action = topic.groups()
    return translator.toNrf(action, message)

def testToMq(incoming):
    action, message = (chr(incoming[0]), incoming[1:])
    traslated = translator.toMq(action, message)
    if traslated:
        topic, msg = traslated
        return 'cab/3/' + topic + '+' + msg

def testResult(incoming, outgoing, expected):
    line = f'{incoming}'.ljust(28)
    line += f' ->   {outgoing}'.ljust(38)
    print(line, end='')
    if outgoing == expected:
        print('ok')
    else:
        print(f'FAIL {expected}')

for mq, nrf in testProtocolBoth:
    nrfAct = testToNrf(mq)
    testResult(mq, nrfAct, nrf)
for mq, nrf in testProtocolBoth:
    mqAct = testToMq(nrf)
    testResult(nrf, mqAct, mq)

for mq, nrf in testProtocolMqNegative:
    nrfAct = testToNrf(mq)
    testResult(mq, nrfAct, nrf)
