FROM python:3.10
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# install requirements
COPY requirements.txt ./
# hadolint ignore=DL3013
RUN pip install --upgrade --no-cache-dir pip && \
  pip install --no-cache-dir -r requirements.txt

# copy source code
COPY . .

# make port available to other containers
EXPOSE 8000

# run app when the container launches
CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]
