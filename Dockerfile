FROM python:3.13.7-slim
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache -r requirements.txt 
COPY . .
WORKDIR /app/src
EXPOSE 8000
CMD [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" ]
