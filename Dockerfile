FROM telegraf:1.32.1

# Install Python3 and venv
RUN apt-get update && apt-get install -y python3 python3-venv

# Create a virtual environment
RUN python3 -m venv /scripts/venv

# Copy the Python script and requirements file
COPY redis_client.py /scripts/redis_client.py
COPY requirements.txt /scripts/requirements.txt

# Activate the virtual environment and install dependencies
RUN /scripts/venv/bin/pip install --no-cache-dir -r /scripts/requirements.txt

# Set the virtual environment Python as the default
ENV PATH="/scripts/venv/bin:$PATH"

CMD ["telegraf"]
