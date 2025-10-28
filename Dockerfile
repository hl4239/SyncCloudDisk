FROM debian:latest
FROM python:3.12-slim
#FROM node:22.14.0-alpine
LABEL authors="helon"
WORKDIR /app
COPY . /app

# 安装系统依赖，再安装 Python 包
RUN apt update && apt install -y \
    build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev \
    && pip install --no-cache-dir -r requirements.txt
