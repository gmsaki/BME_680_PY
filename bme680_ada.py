#!/usr/bin/env python

import bme680
import time
import os
import glob
import MySQLdb

db = MySQLdb.connect(host="localhost", user="root", passwd="saki", db="FireFighter")
cur= db.cursor()

try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except IOError:
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

# These oversampling settings can be tweaked to
# change the balance between accuracy and noise in
# the data.

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

# start_time and curr_time ensure that the
# burn_in_time (in seconds) is kept track of.

start_time = time.time()
curr_time = time.time()
# For 5 min (in sec.)
burn_in_time = 100

burn_in_data = []

try:
    # Collect gas resistance burn-in values, then use the average
    # of the last 50 values to set the upper limit for calculating
    # gas_baseline.
    ###print('Collecting gas resistance burn-in data for 5 mins\n')
    while curr_time - start_time < burn_in_time:
        curr_time = time.time()
        if sensor.get_sensor_data() and sensor.data.heat_stable:
            gas = sensor.data.gas_resistance
            burn_in_data.append(gas)
            #print('Gas: {0} Ohms'.format(gas))
            time.sleep(5)

    gas_baseline = sum(burn_in_data[-50:]) / 50.0

    # Set the humidity baseline to 40%, an optimal indoor humidity.
    hum_baseline = 40.0

    # This sets the balance between humidity and gas reading in the
    # calculation of air_quality_score (25:75, humidity:gas)
    hum_weighting = 0.25

    #print('Gas baseline: {0} Ohms, humidity baseline: {1:.2f} %RH\n'.format(
        #gas_baseline,hum_baseline))

    while True:
        if sensor.get_sensor_data() and sensor.data.heat_stable:
            gas = sensor.data.gas_resistance
            gas_offset = gas_baseline - gas

            hum = sensor.data.humidity
            hum_offset = hum - hum_baseline

            # Calculate hum_score as the distance from the hum_baseline.
            if hum_offset > 0:
                hum_score = (100 - hum_baseline - hum_offset)
                hum_score /= (100 - hum_baseline)
                hum_score *= (hum_weighting * 100)

            else:
                hum_score = (hum_baseline + hum_offset)
                hum_score /= hum_baseline
                hum_score *= (hum_weighting * 100)

            # Calculate gas_score as the distance from the gas_baseline.
            if gas_offset > 0:
                gas_score = (gas / gas_baseline)
                gas_score *= (100 - (hum_weighting * 100))

            else:
                gas_score = 100 - (hum_weighting * 100)

            # Calculate air_quality_score.
            air_quality_score = hum_score + gas_score
	    
	    altitude = ((1013.25/ sensor.data.pressure)**(0.190263102) - 1) * (sensor.data.temperature) / 0.0065 
	    altitude = altitude * 3.2808

            """ print('Temperature: {0:.2f} C, Humidity: {1:.2f} %RH, Air Pressure: {2:} hpa, Gas: {3:} Ohms, air quality: {4:.2f}, Altitude: {5:.2f} ft.'.format(
                sensor.data.temperature,
		hum,
		sensor.data.pressure,
		gas,
                air_quality_score,
		altitude))"""
                       

            time.sleep(5)
	    ######
	    sql = ("""INSERT INTO bme68(Temperature, Humidity, Air_Pressure, Gas_Resistance, Air_Quality, Altitude) VALUES (%s,%s,%s,%s,%s,%s)  """, (sensor.data.temperature, hum, sensor.data.pressure, gas, air_quality_score, altitude))
            try:
	        cur.execute(*sql)
		db.commit()
	    except:
	        db.rollback()
	    cur.close()
	    db.close()

except KeyboardInterrupt:
    pass
