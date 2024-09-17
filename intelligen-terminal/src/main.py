# main.py
import network
import urequests
import machine
import utime
import json as js

SERVER_ADDR = "YOUR-SERVER"
AP_name = 'YOUR-AP-NAME'
password = 'YOUR-AP-PSW'

dev_id = 1
url = f'http://{SERVER_ADDR}:1145/dataAPI?seat_id={dev_id}&seat_status='

board_led = machine.Pin(2, machine.Pin.OUT) # on-board LED
led = machine.Pin(15, machine.Pin.OUT) # GPIO15, D10
light_relay = machine.Pin(16, machine.Pin.OUT) # GPIO16, D2

button = machine.Pin(0, machine.Pin.IN) # GPIO0, D8
infrared = machine.Pin(4, machine.Pin.IN) # GPIO4, D4
pressure = machine.Pin(5, machine.Pin.IN) # GPIO5, D3

light_condition = False # lamp light condition
light_temp_off = False # if the light is temporally off
seat_condition = 0 # 0: empty; 1: sitting; 2: occupying
led_condition = False # if the seat is scheduled

def _assert_light(bool_expr: bool) -> bool:
    """
    Assert the light condition.
    
    :param bool_expr: the boolean expression to assert
    :return: the boolean value of the expression
    """
    if bool_expr:
        board_led.off()
        return True
    else:
        board_led.on() # debug light on
        return False

def connect_WLAN() -> None:
    """
    Connect to the WLAN.
    """

    sta_if = network.WLAN(network.STA_IF); sta_if.active(True)
    sta_if.scan() # scan for available access points
    sta_if.connect(AP_name, password) # connect to an AP
    while not _assert_light(sta_if.isconnected()): # wait for connection
        utime.sleep(0.5)

def refresh_seatCondition() -> None:
    """
    Refresh the seat condition.
    """
    global seat_condition
    human = infrared.value()
    desk_occupy = not pressure.value()
    if human:
        seat_condition = 1
    elif desk_occupy:
        seat_condition = 2
    else:
        seat_condition = 0

def refresh_lightCondition() -> None:
    """
    Refresh the lamp light condition.
    """
    global light_condition

    if not led_condition: # if the seat not reserved
        light_condition = False
        return
    
    button_press = button.value() # 0 is pressed
    if not button_press:
        light_condition = not light_condition

def server_communicate() -> None:
    """
    Communicate with the server and update scheduled light.
    """
    global led_condition, light_condition

    res = urequests.get(f"{url}{seat_condition}")
    if _assert_light(res.status_code == 200):
        res = js.loads(res.text)
        if not led_condition and res["reserved"]: # not reserved to reserved
            light_condition = res["light"]
        led_condition = res["reserved"]

connect_WLAN()


while True:
    # read input and refresh conditions
    refresh_seatCondition()
    refresh_lightCondition()
    server_communicate()

    # update the output
    light_relay.value(light_condition and seat_condition == 1)
    led.value(led_condition)

    utime.sleep(2)
    
    
