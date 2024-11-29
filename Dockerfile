# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application file to the container
COPY user_service.py /app

# Install dependencies (Flask in this case)
RUN pip install flask

# Run the application
CMD ["python", "user_service.py"]
