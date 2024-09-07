FROM python:alpine

ARG FOLDER_NAME

# Important to review the time-zone (TZ)
ENV TZ="Hongkong"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apk update && apk add --no-cache gcc musl-dev libffi-dev openssl-dev

# Create a non-root user
RUN adduser -D worker

RUN mkdir -p /app/$FOLDER_NAME

RUN pip install cryptography
RUN pip install apscheduler
RUN pip install requests
RUN pip install tzlocal

COPY ./src/*.py /app/$FOLDER_NAME/
COPY ./src/*.txt /app/$FOLDER_NAME/

RUN chown -R worker:worker /app/$FOLDER_NAME/
# Switch to the non-root user
USER worker

WORKDIR /app/$FOLDER_NAME/

CMD ["python", "main.py"]