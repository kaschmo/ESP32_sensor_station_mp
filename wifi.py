import network
import time

# the class maintains a connection to a WiFi network
class Connection:

    # initialize a connection to a WiFi network
    def __init__(self, ssid, password):

        # check if ssid and password are specified
        if not ssid or not password:
            #Error OLED notice
            raise Exception('ssid/password are not set')

        self.ssid = ssid
        self.password = password
        self.nic = network.WLAN(network.STA_IF)

    # connect to the specified wi-fi network
    def connect(self):
        
        print('connecting to network: %s' % self.ssid)
        self.nic.active(True)
        self.nic.connect(self.ssid, self.password)

        attempt = 0
        while attempt < 30 and not self.nic.isconnected():
            time.sleep(1)
            attempt = attempt + 1
            print('Wifi: still connecting ...')

        if self.nic.isconnected():
            print('Wifi: connected')
            print('IP: ', self.nic.ifconfig())
            
        else:
            print('Wifi: could not connect to WiFi')

    # check if the connection is active
    def is_connected(self):
        return self.nic is not None and self.nic.active() and self.nic.isconnected()

    # tries reconnecting if the connection is lost
    def reconnect_if_necessary(self):
        while not self.is_connected():
            self.connect()

    # disconnect from the network
    def disconnect(self):
        print('Wifi: disconnecting ...')
        self.nic.disconnect()
        self.nic.active(False)

    # disconnect from the network and connect again
    def reconnect(self):
        self.disconnect()
        self.connect()

    def get_ip(self):
        # ifconfig returns tuple of IP, Subnetmask, GW. get 0.
        return self.nic.ifconfig()[0]