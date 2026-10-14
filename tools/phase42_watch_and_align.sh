#!/bin/bash
cd /workspace/djfm-sgcs
for i in $(seq 1 120); do
  if python3 tools/phase42_align_dirs.py; then
    echo "ALIGNED_OK $(date)" | tee -a assets/samples/phase42/ALIGN_OK.txt
    exit 0
  fi
  sleep 15
done
echo "WATCH_TIMEOUT $(date)" | tee -a assets/samples/phase42/ALIGN_OK.txt
exit 1
