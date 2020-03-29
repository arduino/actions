FROM python:3.8.2

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY reportsizedeltas.py /reportsizedeltas.py
RUN ["chmod", "+x", "reportsizedeltas.py"]

# Code file to execute when the docker container starts up
ENTRYPOINT ["python", "reportsizedeltas.py"]
