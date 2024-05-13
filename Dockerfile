FROM python:3.12.2

# Update package lists and install required packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    locales

# Set the locale to Bahasa Indonesia
RUN echo 'id_ID.UTF-8 UTF-8' >> /etc/locale.gen && locale-gen
ENV LANG id_ID.UTF-8
ENV LANGUAGE id_ID:en
ENV LC_ALL id_ID.UTF-8

# Set the working directory
WORKDIR /bot

# Copy the requirements file and install dependencies
COPY requirements.txt /bot/
RUN pip install -r requirements.txt

# Install flyctl
RUN curl -L https://fly.io/install.sh | sh

# Copy the application code
COPY . /bot

# Set appropriate permissions
RUN chmod -R 777 /bot

# Specify the command to run your application
CMD ["python", "bot.py"]