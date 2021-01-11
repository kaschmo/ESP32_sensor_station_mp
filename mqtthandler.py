from umqttsimple import MQTTClient
import machine
import time


class MQTTHandler:

    def __init__(self, client_id, mqtt_server, topic_sub, topic_pub):

        self.client_id = client_id
        self.mqtt_server = mqtt_server
        self.topic_sub = topic_sub
        self.topic_pub = topic_pub
        try:
            self.client = self.connect_and_subscribe()
        except OSError as e:
            self.restart_and_reconnect()

    def sub_cb(self, topic, msg):
        print((topic, msg))

    def restart_and_reconnect(self):
        print('MQTT: Failed to connect to MQTT broker. Reconnecting...')
        time.sleep(11)
        machine.reset()

    def connect_and_subscribe(self):
        client = MQTTClient(self.client_id, self.mqtt_server)
        client.set_callback(self.sub_cb)
        client.connect()
        client.subscribe(self.topic_sub)
        print('MQTT: Connected to %s MQTT broker, subscribed to %s topic' % (self.mqtt_server, self.topic_sub))
        return client

    def publish(self, topic, msg):
        full_topic = self.topic_pub+"/"+topic
        print('MQTT: sending topic %s : %s '%(full_topic,msg))
        self.client.publish(full_topic,msg)