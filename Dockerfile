FROM python:3.6-slim

RUN pip install --no-cache-dir pymongo

COPY . .

ENTRYPOINT [ "./mongo-diff.py" ]
