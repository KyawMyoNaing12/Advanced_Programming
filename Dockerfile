FROM python:3.11
WORKDIR / assignment
COPY . .
RUN pip install -r requirements.txt
ENV DISPLAY=host.docker.internal:0.0
CMD  ["python", "Sale_Data_Validation.py"]
