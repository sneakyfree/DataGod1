FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY ./api/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy API source code
COPY ./api/src/ /app/api/src/

# Copy main entry point
COPY ./api/src/main.py /app/main.py

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:main_app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
