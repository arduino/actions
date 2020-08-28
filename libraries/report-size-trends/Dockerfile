FROM python:3.8.5

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY reportsizetrends /reportsizetrends

# Install python dependencies
RUN pip install -r /reportsizetrends/requirements.txt

# Code file to execute when the docker container starts up
ENTRYPOINT ["python", "/reportsizetrends/reportsizetrends.py"]
