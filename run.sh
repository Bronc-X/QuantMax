#!/bin/bash
# QuantOpen CLI wrapper with PYTHONPATH set for quant_core
cd "$(dirname "$0")"
source .venv/bin/activate
PYTHONPATH=. quantopen "$@"
