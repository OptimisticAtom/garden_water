import RPi.GPIO as gpio
import time
import spidev

isActive = True
delay = 0.1
adc_channel = 0

# GPIO Pin Variables
breakLoopPin = 17
ledPin = 18
valveOpenPin = 14
valveClosedPin = 15

# Watering Variables
isWatering = False
waterTimeLimit = 3600
moistureTestDelay = 60
valveActiveTime = 10
maxWaterMinutes = 5
gardenMoistureTarget = 50
dry = 1023
wet = 469

# Led Pin Variables
ledState = False
ledBlinkTime = 1


class Timer:
    def __init__(self, timerStart=time.time()):
        self.lastTime = timerStart

    def timer(self):
        seconds = (time.time() - self.lastTime)
        return seconds

    def resetTimer(self):
        self.lastTime = time.time()


BlinkTimer = Timer()


def blinkLed():
    global ledState
    timeSinceLastBlink = BlinkTimer.timer()
    # print(timeSinceLastBlink)
    # print(ledTime)
    if(timeSinceLastBlink > ledBlinkTime):
        if(ledState is False):
            ledState = True
            # print("led on")
        else:
            ledState = False
            # print("led off")
        gpio.output(ledPin, ledState)
        BlinkTimer.resetTimer()


ValveTimer = Timer(0)


def toggleValve(isWatering):
    if(ValveTimer.lastTime == 0):
        ValveTimer.lastTime = time.time()
        if(isWatering):
            gpio.output(valveClosedPin, False)
            gpio.output(valveOpenPin, True)
        else:
            gpio.output(valveOpenPin, False)
            gpio.output(valveClosedPin, True)
    else:
        if(ValveTimer.timer() > valveActiveTime):
            gpio.output(valveOpenPin, False)
            gpio.output(valveClosedPin, False)
            ValveTimer.lastTime = 0


def readadc(channel):
    if (channel > 7 or channel < 0):
        return -1
    r = spi.xfer([1, (8 + channel) << 4, 0])

    data = ((r[1] & 3) << 8) + r[2]
    return data


def checkMoistureSensors():
    moistureSensors = [0] * 5
    hour = time.localtime(time.time()).tm_hour
    day = time.localtime(time.time()).tm_mday
    month = time.localtime(time.time()).tm_mon
    year = time.localtime(time.time()).tm_year
    for i in range(0, 5):
        moistureSensors[i] = (100 - int(((readadc(i) - wet) / (dry - wet)) * 100))
        name = 'sensorLogs/Sensor'+str(i + 1)+':'+str(month)+','+str(day)+','+str(year)+'.txt'
        fdata = open(name, 'a')
        fdata.write(str(moistureSensors[i]) + '-' + str(hour) + ',')
        fdata.close()
    print(moistureSensors, time.ctime(time.time()))
    return moistureSensors


WaterTimer = Timer(0)
MoistureTimer = Timer(0)


def waterPlants():
    global isWatering
    global maxWaterMinutes
    timeSinceLastWater = WaterTimer.timer()
    timeSinceLastTest = MoistureTimer.timer()
    if(timeSinceLastWater > waterTimeLimit and timeSinceLastTest > moistureTestDelay):
        MoistureTimer.resetTimer()
        moistureSensors = checkMoistureSensors()
        hour = time.localtime(time.time()).tm_hour
        if(hour > 18 and hour < 22 and maxWaterMinutes > 0):
            maxWaterMinutes -= 1
            isGardenWatered = True
            belowTarget = 0
            for i in range(0, 5):
                if(moistureSensors[i] < gardenMoistureTarget):
                    belowTarget += 1
            if(belowTarget > 1):
                isGardenWatered = False
            if(isGardenWatered is True and ValveTimer.lastTime == 0):
                WaterTimer.resetTimer()
                isWatering = False
                toggleValve(isWatering)
                print("Closing Valve")
            elif(ValveTimer.lastTime == 0):
                if(isWatering is False):
                    isWatering = True
                    toggleValve(isWatering)
                    print("Opening Valve")
        else:
            WaterTimer.resetTimer()
            maxWaterMinutes = 5
            print("It is not a good time to water")
            if(isWatering):
                print("Valve is open after hours. Closing...")
                isWatering = False
                toggleValve(isWatering)
    # try to turn off valve if valve is on
    if(ValveTimer.lastTime != 0):
        toggleValve(isWatering)


# def initialSensorCheck():
#     global isWatering
#     print("Starting Watering Procedure")
#     moistureSensors = checkMoistureSensors()
#     isGardenWatered = True
#     for i in range(0, 5):
#         if(moistureSensors[i] < gardenMoistureTarget):
#             isGardenWatered = False
#             print("Sensor ", i, " is below the threshold")
#     if(isGardenWatered is True):
#         print("Garden is watered. Next check in t minus ", waterTimeLimit, "seconds")
#     else:
#         print("Garden is not watered. Opening valve now.")
#         WaterTimer.lastTime = waterTimeLimit + 1
#         toggleValve(isWatering)


gpio.setmode(gpio.BCM)
gpio.setup(ledPin, gpio.OUT)
gpio.setup(breakLoopPin, gpio.IN)
gpio.setup(valveOpenPin, gpio.OUT)
gpio.setup(valveClosedPin, gpio.OUT)
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000


gpio.output(valveOpenPin, False)
gpio.output(valveClosedPin, False)


# initialSensorCheck()

while(isActive):
    if(gpio.input(breakLoopPin) is True):
        isActive = False
    blinkLed()
    waterPlants()
    # print("------------")
    time.sleep(delay)


gpio.cleanup()
spi.close()
