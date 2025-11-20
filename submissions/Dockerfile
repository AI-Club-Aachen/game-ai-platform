FROM python:3.11-slim

RUN useradd -m runner
WORKDIR /home/runner/app

COPY agent_requirements.txt /tmp/agent_requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/agent_requirements.txt && rm /tmp/agent_requirements.txt

COPY . .

USER runner
ENV PYTHONUNBUFFERED=1
CMD ["python","agent.py"]