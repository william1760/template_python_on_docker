FROM python:alpine

ARG FOLDER_NAME

# Important to review the time-zone (TZ)
ENV TZ="Hongkong"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Update and install dependencies
RUN apk update && apk add --no-cache gcc musl-dev libffi-dev openssl-dev bind-tools

# Copy source files to the application directory
COPY ./src/*.py /app/$FOLDER_NAME/
COPY ./src/config.json /app/$FOLDER_NAME/

# Create a non-root user: worker
RUN adduser -D worker
RUN chown -R worker:worker /app/$FOLDER_NAME/

# Switch to non-root user and set PATH for user-installed packages
USER worker
ENV PATH="/home/worker/.local/bin:$PATH"

# Install Python dependencies
RUN python -m pip install --upgrade pip --user
RUN pip install --user cryptography
RUN pip install --user apscheduler
RUN pip install --user requests
RUN pip install --user tzlocal
RUN pip install --user dnspython
RUN pip install --user validators

# Set the working directory
WORKDIR /app/$FOLDER_NAME/

# Run the application
CMD ["python", "main.py"]