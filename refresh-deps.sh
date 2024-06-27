#!/bin/bash
pip install --upgrade pip
pip install -qr requirements.txt --upgrade
pip install -qr requirements_docs.txt --upgrade
pip install -qr requirements_test.txt --upgrade
pre-commit autoupdate
