#!/usr/bin/env bash

uvicorn fairsharing_proxy:app --host 0.0.0.0 --port 8888 --proxy-headers --no-use-colors
