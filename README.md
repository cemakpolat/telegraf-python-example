# Telegraf Alerting via Redis Python Extension

This project demonstrates how Python code can be executed within telegraf docker, which requires a custom docker creation. 
A direct installation of python softwares with `pip` is not possible due to the Debian PEP 668 restriction, which means system-wide pip installations are blocked. The solution is to use a virtual environment for Python dependencies, and running the python code within this environment.

## Use case

The application observes the following metrics with the defined thresholds. The collected values are aggregated in the redis and the average of the values for each metric is compared with the threshold value. If the values are higher then their treshold values, the two alerst mechanism will function: First an alert will be sent to the MSTeams using a webhook, and then the second message will be sent to the mqtt broker. 
```
thresholds = {
    'cpu:usage_system': 75,
    'cpu:usage_user': 80,
    'cpu:usage_idle':5 # Tested
}
```
We keep the algorithm quite simple, an intention is to see whether this system works at all. The adjustment on the evaluation of the metrics, and trend analysis must be adapted to your environment conditions. 

A more detailed explanation can be found in this medium link: 

