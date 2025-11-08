FROM python:3.11-slim
RUN useradd -m runner
WORKDIR /home/runner/app
COPY . .
USER runner
ENV PYTHONUNBUFFERED=1
CMD ["python","agent.py"]