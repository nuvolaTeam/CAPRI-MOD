# CAPRI-mod in a container (Debian).
#
#   docker build -t capri-mod .
#   docker run --rm capri-mod                                   # the test suite
#   docker run --rm -v "$PWD/runs:/runs" capri-mod \
#       python tools/run/run_f2f_2030.py /runs/f2f.pkl --verbose     # a full Farm-to-Fork 2030 run
#
# The image holds the code and the data layer (capri_data); results go to a mounted volume.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONHASHSEED=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# Debian's Python 3.11 (the model needs >= 3.10); a virtual environment keeps pip away from the system packages
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m venv "$VIRTUAL_ENV"

WORKDIR /app

# dependencies first, so code changes do not rebuild this layer
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

# run as an unprivileged user
RUN useradd --create-home --uid 1000 capri && chown -R capri:capri /app
USER capri

CMD ["python", "tools/run/run_tests.py", "--parts", "2"]
