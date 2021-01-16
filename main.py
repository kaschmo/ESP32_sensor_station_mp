from machine import Pin,I2C
from config import Config
from wifi import Connection
import gc
from microWebSrv import MicroWebSrv
from mqtthandler import MQTTHandler
from display import LEDDisplay
import time
import machine
import webrepl # do it in main, not in boot since Wifi needs to be connected first.
import esp32
from bme280 import BME280
from hcsr04 import HCSR04
import ujson

# garbage collection on 
gc.collect()
# load configuration for a file
config = Config('main.conf')

# timers
last_main_timer = 0
last_mqtt_timer = 0

#WIFI
wifi = Connection(config.get('ssid'), config.get('password'))
wifi.connect()

#WebREPL init. in Main. not in Boot.py
webrepl.start()

#OLED Displays
display = LEDDisplay(config.get('rst_pin'), config.get('scl_pin'), config.get('sda_pin'))
display.write('IP', wifi.get_ip())

#MQTT client implementation
mqtt = MQTTHandler(config.get('mqtt_client_id'), config.get('mqtt_server'), config.get('mqtt_in_topic'), config.get('mqtt_out_topic'))

#LED Pin 25
led = Pin(config.get('led_pin'), Pin.OUT)

#Analog Tmp sensor
tmp_sensor = machine.ADC(machine.Pin(37)) #GPIO 37

#BME280
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=10000)
bme = BME280(i2c=i2c)

#distance sensor
us_sensor = HCSR04(trigger_pin=14, echo_pin=12,echo_timeout_us=1000000)


#http server----------------------------
#LED an/aus
@MicroWebSrv.route('/led_toggle')
def _httpHandlerLED(httpClient, httpResponse) :
    led.value(not(led.value()))
    print('Toggled LED')
    httpResponse.WriteResponseRedirect('index.html')

#Reset
@MicroWebSrv.route('/reset')
def _httpHandlerLED(httpClient, httpResponse) :
    print('Restarting...')
    machine.reset()
    httpResponse.WriteResponseRedirect('index.html')

@MicroWebSrv.route('/mqtt')
def _httpHandlerMQTT(httpClient, httpResponse) :
    print("In /mqtt Get Handler: sendig mqtt")
    send_sensor_values_mqtt()
    httpResponse.WriteResponseRedirect('index.html')

@MicroWebSrv.route('/lcd')
def _httpHandlerLCD(httpClient, httpResponse) :
    print("In /lcd Get Handler: switching display")
    btn_callback(0)
    httpResponse.WriteResponseRedirect('index.html')

@MicroWebSrv.route('/sensors', 'GET')
def _httpHandlerSensors(httpClient, httpResponse) :
    data = 'Hall: {0:.1f} <br> CPU: {1:.1f}&deg;C'.format(esp32.hall_sensor(), esp32.raw_temperature())
    # es funktionieren keine \n im string.
    httpResponse.WriteResponseOk(
        headers = ({'Cache-Control': 'no-cache'}),
        contentType = 'text/event-stream',
        contentCharset = 'UTF-8',
        content = 'data: {0}\n\n'.format(data) )

def create_sensor_tuple(name, value):
    sdict={}
    sdict["name"] = name
    sdict["value"]= value
    return sdict

# server send event to update sensor values. JSON stream
@MicroWebSrv.route('/jsonsensorstream', 'GET')
def _httpHandlerJSONStream(httpClient, httpResponse) :
    #create json stream to send via server events to clients
    #todo: eigentlich brauche ich tuple: ID, sensor_name, sensor_value
    dump_dict={}
    dump_dict["temperature"] = create_sensor_tuple("Temperature", bme.temperature)
    dump_dict["humidity"] = create_sensor_tuple("Humidity", bme.humidity)
    dump_dict["pressure"] = create_sensor_tuple("Pressure", bme.pressure)
    dump_dict["analog_temp"] = create_sensor_tuple("Analog Temperature", str(tmp_sensor.read()))
    data = ujson.dumps(dump_dict)

    httpResponse.WriteResponseOk(
        headers = ({'Cache-Control': 'no-cache'}),
        contentType = 'text/event-stream',
        contentCharset = 'UTF-8',
        content = 'data: {0}\n\n'.format(data) )

print('Starting WebSrv...')
#http server start
srv = MicroWebSrv(webPath='www/')
srv.Start(threaded=True)

# display OLED paging menu
def btn_callback(p): 
    if (display.menu_page == 0 ):
        display.write('Temp: ' + bme.temperature, 'Humidity: '+bme.humidity, 'Pressure: '+bme.pressure)
        display.next_page()
    elif (display.menu_page == 1):
        display.write('Internal', 'IP:' + wifi.get_ip(), 'Hall:' + str(esp32.hall_sensor()),'CPU:' + str(esp32.raw_temperature()))
        display.next_page()
    elif (display.menu_page == 2):
        display.write('last page')
        display.wrap()
    
btn = Pin(config.get('button_pin'), Pin.IN)
btn.irq(trigger=Pin.IRQ_FALLING, handler=btn_callback)

def send_sensor_values_mqtt():
    # send cpu temperature
    mqtt.publish('cpu_temp', str(esp32.raw_temperature()))
    # send hall_sensor
    mqtt.publish('hall_sensor', str(esp32.hall_sensor()))
    #send bme280 values        
    mqtt.publish('temperature', bme.temperature)
    mqtt.publish('humidity', bme.humidity)
    mqtt.publish('pressure', bme.pressure)
    #analog tmp sensor
    mqtt.publish('analog_tmp', str(tmp_sensor.read()))

# main loop
while True:
    mqtt.client.check_msg() #check if mqtt message received and acall internal callback function
    display.refresh()

    #mqtt send cycle
    if (time.ticks_ms() - last_mqtt_timer) > config.get("mqtt_send_cycle"):
        last_mqtt_timer = time.ticks_ms()
        send_sensor_values_mqtt()

    #main Cycle
    if (time.ticks_ms() - last_main_timer) > config.get("main_cycle"):
        #print('Takt 1s')
        last_main_timer = time.ticks_ms()
        print(str(us_sensor.distance_cm()))
        # todo implement. deep sleep between cycles
        #ACHTUNG gefährlich
        #machine.deepsleep(10000)
    
    
