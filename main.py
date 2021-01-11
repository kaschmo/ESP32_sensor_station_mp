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
led = Pin(25, Pin.OUT)

#Analog Tmp sensor
tmp_sensor = machine.ADC(machine.Pin(37)) #GPIO 37

#BME280
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=10000)
bme = BME280(i2c=i2c)


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
    print("In /mqtt Get Handler")
    mqtt.publish('temp', '300')
    content = """\
    <!DOCTYPE html>
    <html lang=en>
        <head>
        	<meta charset="UTF-8" />
            <title>MQTT sent</title>
        </head>
        <body>
            <h1>MQTT Sent</h1>
        </body>
    </html>
	"""
    httpResponse.WriteResponseOk( headers		 = None,
								  contentType	 = "text/html",
								  contentCharset = "UTF-8",
								  content 		 = content )


@MicroWebSrv.route('/test')
def _httpHandlerTestGet(httpClient, httpResponse) :
    print("In /test Get Handler")
    content = """\
    <!DOCTYPE html>
    <html lang=en>
        <head>
        	<meta charset="UTF-8" />
            <title>TEST GET</title>
        </head>
        <body>
            <h1>TEST GET</h1>
            Client IP address = %s
            <br />
			<form action="/test" method="post" accept-charset="ISO-8859-1">
				First name: <input type="text" name="firstname"><br />
				Last name: <input type="text" name="lastname"><br />
				<input type="submit" value="Submit">
			</form>
        </body>
    </html>
	""" % httpClient.GetIPAddr()
    httpResponse.WriteResponseOk( headers		 = None,
								  contentType	 = "text/html",
								  contentCharset = "UTF-8",
								  content 		 = content )
    

@MicroWebSrv.route('/test', 'POST')
def _httpHandlerTestPost(httpClient, httpResponse) :
    formData  = httpClient.ReadRequestPostedFormData()
    firstname = formData["firstname"]
    lastname  = formData["lastname"]
    display.write(firstname, lastname)
    print("In /test POST Handler")
    content   = """\
	<!DOCTYPE html>
	<html lang=en>
		<head>
			<meta charset="UTF-8" />
            <title>TEST POST</title>
        </head>
        <body>
            <h1>TEST POST</h1>
            Firstname = %s<br />
            Lastname = %s<br />
        </body>
    </html>
	""" % ( MicroWebSrv.HTMLEscape(firstname),
		    MicroWebSrv.HTMLEscape(lastname) )
    httpResponse.WriteResponseOk( headers		 = None,
								  contentType	 = "text/html",
								  contentCharset = "UTF-8",
								  content 		 = content )

#test to transmit data to a dynamic hall.html website
@MicroWebSrv.route('/hall', 'GET')
def _httpHandlerHall(httpClient, httpResponse) :
    data = '{0:.1f}'.format(esp32.hall_sensor())
    httpResponse.WriteResponseOk(
        headers = ({'Cache-Control': 'no-cache'}),
        contentType = 'text/event-stream',
        contentCharset = 'UTF-8',
        content = 'data: {0}\n\n'.format(data) )

@MicroWebSrv.route('/sensors', 'GET')
def _httpHandlerSensors(httpClient, httpResponse) :
    data = 'Hall: {0:.1f} CPU: {1:.1f}&deg;C'.format(esp32.hall_sensor(), esp32.raw_temperature())
    # es funktionieren keine \n im string.
    httpResponse.WriteResponseOk(
        headers = ({'Cache-Control': 'no-cache'}),
        contentType = 'text/event-stream',
        contentCharset = 'UTF-8',
        content = 'data: {0}\n\n'.format(data) )

print('Starting WebSrv...')
#http server start
srv = MicroWebSrv(webPath='www/')
#srv.MaxWebSocketRecvLen     = 256
#srv.WebSocketThreaded		= False
srv.Start(threaded=True)
display.write('Started WebSrv')

# display OLED paging menu
def btn_callback(p): 
    if (display.menu_page == 0 ):
        display.write('IP',wifi.get_ip())
        display.next_page()
    elif (display.menu_page == 1):
        display.write('Hall Sensor', str(esp32.hall_sensor()))
        display.next_page()
    elif (display.menu_page == 2):
        display.write('CPU Temp', str(esp32.raw_temperature()))
        display.wrap()
    
btn = Pin(0, Pin.IN)
btn.irq(trigger=Pin.IRQ_FALLING, handler=btn_callback)

# main loop
while True:
    mqtt.client.check_msg() #check if mqtt message received and acall internal callback function
    display.refresh()

    #mqtt send cycle
    if (time.ticks_ms() - last_mqtt_timer) > config.get("mqtt_send_cycle"):
        last_mqtt_timer = time.ticks_ms()
        # send cpu temperature
        mqtt.publish('cpu_temp', str(esp32.raw_temperature()))
        # send hall_sensor
        mqtt.publish('hall_sensor', str(esp32.hall_sensor()))

        #send bme280 values        
        mqtt.publish('temperature', str(bme.temperature))
        mqtt.publish('humidity', str(bme.humidity))
        mqtt.publish('pressure', str(bme.pressure))
        
        #analog tmp sensor
        mqtt.publish('analog_tmp', str(tmp_sensor.read()))


    #main Cycle
    if (time.ticks_ms() - last_main_timer) > config.get("main_cycle"):
        #print('Takt 1s')
        last_main_timer = time.ticks_ms()
        
        # todo implement. deep sleep between cycles
        #ACHTUNG gefährlich
        #machine.deepsleep(10000)
    
    
