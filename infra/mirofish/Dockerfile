# MiroFish runtime used by QuantEdge: the published image (pinned by digest) plus the one library
# version required by the pinned MiroFish commit 7657031, whose backend code is mounted read-only
# by mirofish-service/docker-compose.override.yml. No MiroFish code is changed.
FROM ghcr.io/666ghj/mirofish@sha256:d236402eb35c5abfd68da63be9d19202d619da8803e173e8e34b97731180944a
RUN (command -v uv >/dev/null || pip install --no-cache-dir uv) \
 && uv pip install --python /app/backend/.venv/bin/python "zep-cloud==3.25.0"
