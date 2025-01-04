FROM python:alpine

ARG FOLDER_NAME

# Set environment variables
ENV TZ="Hongkong"
ENV PATH="/home/worker/.local/bin:$PATH"

# Configure time zone and install system dependencies
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apk update && \
    apk add --no-cache gcc musl-dev libffi-dev openssl-dev bind-tools

# Create application directory and non-root user
RUN adduser -D worker && \
    mkdir -p /app/$FOLDER_NAME && \
    chown -R worker:worker /app

# Switch to non-root user
USER worker

# Copy the requirements file into the Docker image
COPY ./requirements.txt /app/$FOLDER_NAME/

# Install Python dependencies
RUN python -m pip install --upgrade pip --user && \
    pip install --user -r /app/$FOLDER_NAME/requirements.txt

# Copy source files after dependencies to leverage Docker cache
COPY ./src/*.py /app/$FOLDER_NAME/
COPY ./src/utilities /app/$FOLDER_NAME/utilities/
COPY ./src/config.json /app/$FOLDER_NAME/


#Ensure write access for the non-root user
USER root
RUN chown -R worker:worker /app/$FOLDER_NAME

# Switch back to non-root user
USER worker

# Set working directory
WORKDIR /app/$FOLDER_NAME/

# Run the application
CMD ["python", "main.py"]