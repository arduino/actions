FROM python:3.8.5

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY reportsizedeltas /reportsizedeltas
RUN ["chmod", "+x", "/reportsizedeltas/reportsizedeltas.py"]

# Code file to execute when the docker container starts up
ENTRYPOINT ["python", "/reportsizedeltas/reportsizedeltas.py"]
