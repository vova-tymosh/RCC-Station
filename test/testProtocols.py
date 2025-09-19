import sys
sys.path.append("../src")
from Comms import *


#
# Test to cover protocol conversion.
#   Should be excuted in the same folder as the Comms.py on a machine with RF24 & Paho Mqtt installed
#

testProtocolBoth = [
('cab/3/throttle+99',                b'Tc'),
('cab/3/function/get+2',             b'P\x02'),
('cab/3/function/3+ON',              b'F\x83'),
('cab/3/function/3+OFF',             b'F\x03'),
('cab/3/value/get+zupa',             b'Gzupa'),
('cab/3/value/zupa+abc',             b'Szupa,abc'),
('cab/3/value/list+',                b'L'),
('cab/3/direction+FORWARD',          b'D\x01'),
('cab/3/direction+REVERSE',          b'D\x00'),
('cab/3/direction+STOP',             b'D\x02'),
('cab/3/direction+NEUTRAL',          b'D\x03'),
('cab/3/heartbeat+',                 b'H\x00'),
('cab/3/heartbeat/values+1,2,65536', b'H\x01\x02\x00\x00\x01\x00'),
('cab/3/heartbeat/keys+Time,Spd',    b'KTime,Spd'),
]

testProtocolToNrf = [
('cab/3/throttle+a',                 None),
('cab/3/throttle+-1',                b'T\x01'),
('cab/3/function/get+a',             None),
('cab/3/value/get+',                 b'G'),
('cab/3/value/list+a',               b'La'),
('cab/3/direction+FOR',              None),
]

testProtocolToMq = []

testIntro = [
('cab/4/intro+L,4,Rcc,0.9,BBB',        b'AL,5,Rcc,0.9,BBB'),
]

broker.addr = 0
broker.known[broker.addr] = {'Format': broker.updateFmt('BBBI')}

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

def testResult(incoming, outgoing, expected, insteadOutgoing = None):
    line = f'{incoming}'.ljust(35)
    if insteadOutgoing == None:
        line += f' ->   {outgoing}'.ljust(42)
    else:
        line += f' ->   {insteadOutgoing}'.ljust(42)
    print(line, end='')
    if outgoing == expected:
        print('ok')
    else:
        print(f'FAIL {expected}')


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    filename='test.log',
                    filemode='a')

for mq, nrf in testProtocolBoth + testProtocolToNrf:
    nrfAct = testToNrf(mq)
    testResult(mq, nrfAct, nrf)
for mq, nrf in testProtocolBoth + testProtocolToMq:
    mqAct = testToMq(nrf)
    testResult(nrf, mqAct, mq)

for mq, nrf in testIntro:
    broker.addr = 4
    nrfAct = testToNrf(mq)
    testResult(mq, str(broker.known[4]), "{'Type': 'L', 'Addr': '4', 'Name': 'Rcc', 'Version': '0.9', 'Proto': 'MQ', 'Format': '<BB'}", "map")
    broker.addr = 5
    mqAct = testToMq(nrf)
    testResult(nrf, str(broker.known[5]), "{'Type': 'L', 'Addr': '5', 'Name': 'Rcc', 'Version': '0.9', 'Proto': 'NRF', 'Format': '<BB'}", "map")


