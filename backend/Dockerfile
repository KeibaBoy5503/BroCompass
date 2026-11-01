# BroCompass 백엔드 이미지 (FastAPI). 프로젝트 루트가 아니라 backend/ 폴더를 빌드 컨텍스트로 쓴다.
#   docker build -t brocompass-api ./backend
#   docker run -p 8000:8000 -e NVIDIA_API_KEY=... brocompass-api
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 논문 DB(papers.db)는 저장소에 올리지 않으므로 이미지를 만들 때 PubMed 에서 수집한다.
# 실패해도 빌드는 계속된다(코치의 AI 요약 없이 규칙 기반 분석만 동작). 끄려면 --build-arg INGEST=0.
ARG INGEST=1
ARG PER_TOPIC=30
ARG NCBI_EMAIL=
RUN if [ "$INGEST" = "1" ]; then \
      python ingest_pubmed.py --per-topic "$PER_TOPIC" --email "$NCBI_EMAIL" \
      || echo "논문 수집에 실패했습니다. 이미지는 논문 DB 없이 만들어집니다."; \
    fi

# 노트 DB 는 컨테이너 안(/data)에 둔다. 무료 호스팅에서는 재시작하면 사라질 수 있다.
RUN mkdir -p /data
ENV BROCOMPASS_DB=/data/brocompass.db

# 호스팅이 PORT 를 넘겨 주면 그 포트를, 아니면 8000 을 쓴다.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
