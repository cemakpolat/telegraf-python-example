import redis
import requests
import paho.mqtt.client as mqtt
import sys
import logging
import os
import time

# Set up logging
logging.basicConfig(level=logging.INFO)

redis_host = os.getenv("REDIS_HOST" )
redis_port = int(os.getenv("REDIS_PORT",6379))
alert_endpoint = os.getenv("ALERT_ENDPOINT" )
alert_mqtt_topic = os.getenv("ALERT_TOPIC","telegraf/alert/cpu_idle")
mqtt_broker = os.getenv("MQTT_BROKER")
mqtt_port = int(os.getenv("MQTT_PORT",1883))


# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.connect(mqtt_broker, mqtt_port, 60)

# Connect to Redis
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)

# Define thresholds for alerting
thresholds = {
    'cpu:usage_system': 75,
    'cpu:usage_user': 80,
    'cpu:usage_idle':5 # Tested
}

# Function to send HTTP POST alert
def send_http_alert(metric, value):
    logging.info("Preparing to send alert to Microsoft Teams")
    # Format the alert message as required by Microsoft Teams
    alert_message = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": "Threshold Alert",
        "themeColor": "FF0000",
        "sections": [{
            "activityTitle": "Alert Notification",
            "facts": [
                {"name": "Metric", "value": metric},
                {"name": "Value", "value": value},
                {"name": "Alert", "value": "Threshold exceeded"}
            ],
            "markdown": True
        }]
    }

    # Send the POST request
    try:
        response = requests.post(alert_endpoint, json=alert_message)
        logging.info(f"HTTP Alert sent: {response.status_code}, Response Text: {response.text}")
        if response.status_code != 200:
            logging.error(f"Failed to send alert. Status Code: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        logging.error(f"Error sending HTTP alert: {e}")


# Function to send MQTT alert
def send_mqtt_alert(client, metric, value):
    alert_message = f"Alert: {metric} exceeded threshold with value {value}"
    client.publish(alert_mqtt_topic, alert_message)
    

def get_last_n_measurements(key, n=10):
    """Retrieve the last `n` measurements from a Redis list."""
    try:
        # Get the last `n` items from the list stored in Redis under `key`
        measurements = redis_client.lrange(key, -n, -1)
        logging.info(f"Retrieved measurements for key '{key}': {measurements}")
        return measurements
    except redis.RedisError as e:
        logging.error(f"Error fetching data from Redis: {e}")
        return []

def analyze_trend(values):
    average = 0
    total = 0
    for value in values:
        total = total + float(value)
    average = total / len(values)
    return average
    
# Main function to check thresholds and send alerts
def check_and_alert(measurements):
    analyze_trends = {}

    # take the average code 
    for measurement in measurements:
        for metric, values in measurement.items():  # Assuming each measurement is a dict
            average_value = analyze_trend(values)
            analyze_trends[metric] = average_value  # Store average values by metric

    # Compare with thresholds
    for metric, avg_value in analyze_trends.items():
        threshold = thresholds.get(metric)  # Get threshold for the metric
        if threshold is not None and avg_value > threshold:
            logging.warning(f"Threshold exceeded for {metric}: {avg_value} > {threshold}")
            send_http_alert(metric, avg_value)  # Send alert if needed
            send_mqtt_alert(mqtt_client, metric, avg_value)
        else:
            logging.warning(f"Everything is fine!")


def store_in_redis(measurement,tags, fields, timestamp):
    """Store parsed data in Redis."""
    # Create a unique key for each metric based on tags
    for field, value in fields.items():
        key = f"{measurement}:{field}"  
        # Store in a Redis List for time-based retrieval
        redis_client.lpush(key, float(value[0:-1])) # remove i item from 
        redis_client.ltrim(key, 0, 9)  # Keep only last 10 measurements

def get_last_n_measurements(measurement, fields, n=10):
    """Retrieve the last `n` measurements from Redis."""
    measurements = []
    for field in fields:
        key = f"{measurement}:{field}"
        measurements.append({key:redis_client.lrange(key, -n, -1)})
    return measurements


def parse_influxdb_line(line):
    """Parse InfluxDB line protocol format."""
    measurement, fields, timestamp = line.split(" ")
    names_tages = measurement.split(',')
    measurement = names_tages[0] # measurement name
    tags = names_tages[1:] # all tags
    fields = dict(field.split('=') for field in fields.split(',')) # fields
    return measurement, tags, fields, int(timestamp)

def main():
    try:
        while True:
            # Read input from stdin
            input_data = sys.stdin.readline().strip()
            if not input_data:  # If there's no line, break the loop
                break         
            if input_data:
                measurement, tags, fields, timestamp = parse_influxdb_line(input_data)
                store_in_redis(measurement,tags, fields, timestamp)
                # Retrieve the last 10 measurements
                measurements = get_last_n_measurements(measurement, fields, 10)
                check_and_alert(measurements)
                # Process the input and send alerts if needed
            else:
                logging.warning("No input received, sleeping for a while.")
                time.sleep(1)
    except Exception as err:
        logging.error(f"Occurred error: {err}")
    finally:
        mqtt_client.loop_stop()  # Stop the MQTT loop before exiting

if __name__ == "__main__":
    main()