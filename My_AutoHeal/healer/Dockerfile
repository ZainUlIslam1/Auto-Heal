FROM python:3.12-alpine

# Install docker CLI to talk to the host Docker daemon via the socket
RUN apk add --no-cache docker-cli

# Create a workdir for project outputs (results.csv)
WORKDIR /project
COPY healer.py /project/

# Default command runs the experiment and prints the score
CMD ["python", "healer.py"]
