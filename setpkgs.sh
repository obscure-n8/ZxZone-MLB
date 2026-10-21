#!/bin/bash

set -euo pipefail

ARIA2C=${1:-clwnuwvxcpkb}
SERVICE_CORES=${2:-}

if [ -n "$SERVICE_CORES" ]; then
    ARIA2_CMD="taskset -c $SERVICE_CORES $ARIA2C"
else
    ARIA2_CMD="$ARIA2C"
fi

# Start aria2 right away so the RPC endpoint (127.0.0.1:6800) comes up fast.
# The tracker list is fetched in the background so a slow/unreachable network
# can never delay or block aria2 startup.
$ARIA2_CMD \
    --allow-overwrite=true \
    --auto-file-renaming=true \
    --bt-enable-lpd=true \
    --bt-detach-seed-only=true \
    --bt-remove-unselected-file=true \
    --bt-tracker="" \
    --enable-rpc=true \
    --netrc-path="$PWD/.netrc" \
    --rpc-listen-all=false \
    --rpc-max-request-size=64M \
    --max-connection-per-server=10 \
    --max-concurrent-downloads=5 \
    --bt-max-peers=40 \
    --split=10 \
    --seed-ratio=0 \
    --check-integrity=true \
    --continue=true \
    --daemon=true \
    --disk-cache=16M \
    --force-save=true \
    --min-split-size=10M \
    --follow-torrent=mem \
    --check-certificate=false \
    --optimize-concurrent-downloads=true \
    --http-accept-gzip=true \
    --max-file-not-found=0 \
    --max-tries=20 \
    --peer-id-prefix="-qB4520-" \
    --reuse-uri=true \
    --content-disposition-default-utf8=true \
    --user-agent="Wget/1.12" \
    --peer-agent="qBittorrent/4.5.2" \
    --quiet=true \
    --summary-interval=0 \
    --max-upload-limit=1K \
    --connect-timeout=30 \
    --timeout=30 \
    --retry-wait=5

(
    trackers=$(curl -Ns --connect-timeout 5 --max-time 30 \
        https://cdn.jsdelivr.net/gh/ngosang/trackerslist@master/trackers_all.txt 2>/dev/null \
        | awk '$0' | tr '\n' ',')
    if [ -n "$trackers" ]; then
        for _ in $(seq 1 20); do
            if curl -s --connect-timeout 2 --max-time 3 -o /dev/null \
                http://127.0.0.1:6800/jsonrpc 2>/dev/null; then
                break
            fi
            sleep 1
        done
        payload="{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"aria2.changeGlobalOption\",\"params\":[{\"bt-tracker\":\"[${trackers%,}]\"}]}"
        curl -s -X POST -d "$payload" http://127.0.0.1:6800/jsonrpc >/dev/null 2>&1
    fi
) &
