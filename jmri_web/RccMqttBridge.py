"""
RCC MQTT Bridge for JMRI
Connects to MQTT and stores RCC locomotive data in JMRI memory variables
Run this from JMRI: Scripting -> Script Entry -> Load this file -> Execute
"""

import jmri
import java
import json
import time
from org.eclipse.paho.client.mqttv3 import MqttClient, MqttConnectOptions, MqttCallback, MqttMessage

class RccMqttBridge(MqttCallback):
    def __init__(self):
        self.mqtt_broker = "tcp://localhost:1883"
        self.client_id = "JMRI_RCC_Bridge"
        self.mqtt_client = None
        self.locomotives = {}
        self.locomotive_keys = {}
        self.memory_manager = jmri.InstanceManager.getDefault(jmri.MemoryManager)
        
        print("=" * 60)
        print("RCC MQTT Bridge for JMRI")
        print("=" * 60)
        self.connect_mqtt()
        
    def connect_mqtt(self):
        try:
            print("Connecting to MQTT broker: " + self.mqtt_broker)
            self.mqtt_client = MqttClient(self.mqtt_broker, self.client_id)
            self.mqtt_client.setCallback(self)
            
            options = MqttConnectOptions()
            options.setCleanSession(True)
            options.setConnectionTimeout(10)
            options.setKeepAliveInterval(60)
            options.setAutomaticReconnect(True)
            
            self.mqtt_client.connect(options)
            self.mqtt_client.subscribe("cab/+/heartbeat/values")
            self.mqtt_client.subscribe("cab/+/heartbeat/keys")
            self.mqtt_client.subscribe("cab/+/intro")
            self.mqtt_client.subscribe("cab/+/function/list")
            
            print("[OK] Connected to MQTT broker")
            print("[OK] Subscribed to RCC topics")
            self.set_memory("RCC_STATUS", "CONNECTED")
            
            # Create command memory variable
            self.set_memory("RCC_CMD", "")
            
            # Start command monitoring
            self.start_command_monitor()
            print("[OK] Bridge ready - /web/rcc-plotter.html")
            print("=" * 60)
            
        except Exception as e:
            print("[ERROR] Failed to connect: " + str(e))
            self.set_memory("RCC_STATUS", "DISCONNECTED")
    
    def connectionLost(self, cause):
        print("[ERROR] MQTT connection lost: " + str(cause))
        self.set_memory("RCC_STATUS", "DISCONNECTED")
        print("Attempting to reconnect...")
        try:
            self.connect_mqtt()
        except Exception as e:
            print("Reconnection failed: " + str(e))
    
    def messageArrived(self, topic, message):
        try:
            # Handle payload conversion - convert byte array to string
            payload_bytes = message.getPayload()
            
            # In Jython, getPayload() returns a byte array
            # Convert it properly to a Python string
            from java.lang import String
            java_string = String(payload_bytes, "UTF-8")
            payload = str(java_string)  # Convert to Python string
            
            topic_str = str(topic)
            
            if "/heartbeat/values" in topic_str:
                self.process_heartbeat(topic_str, payload)
            elif "/heartbeat/keys" in topic_str:
                self.process_keys(topic_str, payload)
            elif "/intro" in topic_str:
                self.process_intro(topic_str, payload)
            elif "/function/list" in topic_str:
                self.process_function_list(topic_str, payload)
                
        except Exception as e:
            import traceback
            print("Error processing message: " + str(e))
            print("Topic: " + str(topic))
            print("Traceback:")
            traceback.print_exc()
    
    def deliveryComplete(self, token):
        pass
    
    def process_heartbeat(self, topic, payload):
        try:
            # Extract loco ID from topic: cab/3/heartbeat/values
            topic_parts = topic.split("/")
            if len(topic_parts) < 2:
                return
            loco_id = topic_parts[1]
            
            # Parse CSV values
            values = payload.strip().split(",")
            keys = self.locomotive_keys.get(loco_id, 
                ["Time", "Distance", "Bitstate", "Speed", "Lost", "Throttle", "ThrOut", "Battery", "Temp", "Psi", "Current"])
            
            if len(values) != len(keys):
                return
            
            # Create telemetry dict
            telemetry = {}
            bitstate = 0
            for i in range(len(keys)):
                try:
                    key = keys[i].strip().lower()
                    value = float(values[i].strip())
                    telemetry[key] = value
                    if key == 'bitstate':
                        bitstate = int(value)
                except Exception as e:
                    pass
            
            # Extract direction from bitstate (2 highest bits)
            # 0 = REVERSE, 1 = FORWARD, 2 = STOP
            direction_bits = (bitstate >> 30) & 0x3
            direction_map = {0: 'REVERSE', 1: 'FORWARD', 2: 'STOP'}
            direction = direction_map.get(direction_bits, 'UNKNOWN')
            telemetry['direction'] = direction
            
            # Extract function states from bitstate (lower 29 bits)
            # Each bit represents a function F0-F28
            function_states = {}
            for i in range(29):
                bit_value = (bitstate >> i) & 0x1
                function_states['F' + str(i)] = bit_value
            telemetry['functions'] = function_states
            
            # Update locomotive data
            if loco_id not in self.locomotives:
                self.locomotives[loco_id] = {
                    'id': loco_id,
                    'name': 'Loco ' + loco_id,
                    'address': loco_id
                }
            
            loco = self.locomotives[loco_id]
            loco['last_seen'] = int(time.time() * 1000)
            loco['telemetry'] = telemetry
            
            # Store in memory variables
            for key, value in telemetry.items():
                if key == 'functions':
                    # Store individual function states
                    for func_key, func_value in value.items():
                        mem_name = "RCC_" + loco_id + "_" + func_key
                        self.set_memory(mem_name, str(func_value))
                else:
                    mem_name = "RCC_" + loco_id + "_" + key.upper()
                    self.set_memory(mem_name, str(value))
            
            # Update locomotive list
            self.update_loco_list()
            
        except Exception as e:
            import traceback
            print("Error in process_heartbeat: " + str(e))
            traceback.print_exc()
    
    def process_keys(self, topic, payload):
        try:
            topic_parts = topic.split("/")
            if len(topic_parts) < 2:
                return
            loco_id = topic_parts[1]
            keys = payload.strip().split(",")
            self.locomotive_keys[loco_id] = keys
        except Exception as e:
            print("Error in process_keys: " + str(e))
    
    def process_intro(self, topic, payload):
        try:
            topic_parts = topic.split("/")
            if len(topic_parts) < 2:
                return
            loco_id = topic_parts[1]
            parts = payload.strip().split(",")
            
            if len(parts) >= 4 and parts[0].strip() == "L":
                if loco_id not in self.locomotives:
                    self.locomotives[loco_id] = {'id': loco_id}
                
                self.locomotives[loco_id]['address'] = parts[1].strip()
                self.locomotives[loco_id]['name'] = parts[2].strip()
                self.locomotives[loco_id]['version'] = parts[3].strip()
                
                print("Loco " + loco_id + " introduced: " + parts[2].strip() + " (v" + parts[3].strip() + ")")
                self.update_loco_list()
                
                # Schedule function list request to run outside callback thread
                self.schedule_function_list_request(loco_id)
        except Exception as e:
            print("Error in process_intro: " + str(e))
    
    def schedule_function_list_request(self, loco_id):
        """Schedule a function list request to run after a short delay"""
        from java.util import Timer, TimerTask
        
        class RequestTask(TimerTask):
            def __init__(self, bridge, loco_id):
                self.bridge = bridge
                self.loco_id = loco_id
                
            def run(self):
                self.bridge.request_function_list(self.loco_id)
        
        timer = Timer()
        task = RequestTask(self, loco_id)
        timer.schedule(task, 100)  # Wait 100ms then request
    
    def request_function_list(self, loco_id):
        """Request the function list from a locomotive"""
        try:
            if self.mqtt_client and self.mqtt_client.isConnected():
                topic = "cab/" + loco_id + "/function/list/req"
                # Use same pattern as process_command - empty string payload
                self.mqtt_client.publish(topic, "".encode('utf-8'), 0, False)
                print("[OK] Requested function list for loco " + loco_id)
            else:
                print("[ERROR] Cannot request function list - MQTT not connected")
        except Exception as e:
            import traceback
            print("[ERROR] Error requesting function list: " + str(e))
            traceback.print_exc()
    
    def process_function_list(self, topic, payload):
        """Process function list response from locomotive"""
        try:
            topic_parts = topic.split("/")
            if len(topic_parts) < 2:
                return
            loco_id = topic_parts[1]
            
            # Parse payload: "0,headlight,1,bell,2,horn,3,coupler"
            parts = payload.strip().split(",")
            functions = []
            
            # Parse pairs of (number, name)
            for i in range(0, len(parts), 2):
                if i + 1 < len(parts):
                    func_num = parts[i].strip()
                    func_name = parts[i + 1].strip()
                    functions.append({
                        'number': func_num,
                        'name': func_name
                    })
            
            # Store in locomotive data
            if loco_id in self.locomotives:
                self.locomotives[loco_id]['functions'] = functions
                print("Loco " + loco_id + " has " + str(len(functions)) + " functions: " + 
                      ", ".join([f['name'] for f in functions]))
                
                # Store function list in memory as JSON
                import json
                func_json = json.dumps(functions)
                self.set_memory("RCC_" + loco_id + "_FUNCTIONS", func_json)
            
        except Exception as e:
            import traceback
            print("Error in process_function_list: " + str(e))
            traceback.print_exc()
    
    def update_loco_list(self):
        loco_list = []
        for loco_id, loco in self.locomotives.items():
            loco_list.append({
                'id': loco_id,
                'name': loco.get('name', 'Loco ' + loco_id),
                'address': loco.get('address', loco_id),
                'version': loco.get('version', ''),
                'last_seen': loco.get('last_seen', 0)
            })
        
        self.set_memory("RCC_LOCO_LIST", json.dumps(loco_list))
    
    def set_memory(self, name, value):
        try:
            memory = self.memory_manager.getMemory(name)
            if memory is None:
                memory = self.memory_manager.newMemory(name, name)
            memory.setValue(value)
        except Exception as e:
            print("Error setting memory " + name + ": " + str(e))
    
    def start_command_monitor(self):
        """Monitor RCC_CMD memory variable for commands to publish"""
        from java.util import Timer, TimerTask
        
        class CommandMonitorTask(TimerTask):
            def __init__(self, bridge):
                self.bridge = bridge
                self.last_cmd = None
                
            def run(self):
                try:
                    memory = self.bridge.memory_manager.getMemory("RCC_CMD")
                    if memory is None:
                        return
                    
                    cmd_value = memory.getValue()
                    if cmd_value and cmd_value != self.last_cmd:
                        self.last_cmd = cmd_value
                        self.bridge.process_command(str(cmd_value))
                except Exception as e:
                    print("Error in command monitor: " + str(e))
        
        self.cmd_timer = Timer()
        self.cmd_task = CommandMonitorTask(self)
        self.cmd_timer.scheduleAtFixedRate(self.cmd_task, 100, 100)  # Check every 100ms
        print("[OK] Command monitor started")
    
    def process_command(self, cmd_json):
        """Process and publish a command from the web interface"""
        try:
            cmd = json.loads(cmd_json)
            topic = cmd.get('topic')
            payload = str(cmd.get('payload', ''))
            
            if topic and self.mqtt_client and self.mqtt_client.isConnected():
                # Publish the command
                self.mqtt_client.publish(topic, payload.encode('utf-8'), 0, False)
                print("Published: " + topic + " -> " + payload)
        except Exception as e:
            print("Error processing command: " + str(e))
    
    def stop(self):
        try:
            if hasattr(self, 'cmd_timer') and self.cmd_timer:
                self.cmd_timer.cancel()
            if self.mqtt_client and self.mqtt_client.isConnected():
                self.mqtt_client.disconnect()
                self.mqtt_client.close()
            self.set_memory("RCC_STATUS", "STOPPED")
            print("RCC MQTT Bridge stopped")
        except Exception as e:
            print("Error stopping: " + str(e))

# Global instance
rcc_bridge = None

def start_bridge():
    global rcc_bridge
    if rcc_bridge is None:
        rcc_bridge = RccMqttBridge()
    else:
        print("Bridge already running")

def stop_bridge():
    global rcc_bridge
    if rcc_bridge:
        rcc_bridge.stop()
        rcc_bridge = None
    else:
        print("Bridge not running")

# Auto-start
start_bridge()