# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container to the root
WORKDIR /

# Install system dependencies required for mysqlclient and pkg-config
RUN apt-get update && \
    apt-get install -y gcc default-libmysqlclient-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt /

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install boto3

# Copy the rest of the working directory contents into the container
COPY . /

COPY .chainlit / 
# Expose port 8002
EXPOSE 8002

# Debugging commands: List directory contents and show working directory
CMD ["sh", "-c", "echo 'Current Directory:' && pwd && \
echo 'Directory Contents:' && ls -la / && \
ls -la /fetch_secrets.py && \
python /fetch_secrets.py && \
chainlit run acquisition.py --host 0.0.0.0 --port 8002 --root-path /chainlit" ]
# uvicorn main:app --host 0.0.0.0 --port 8002"]
