#!/usr/bin/env bash
set -e

PROJECT_MAIN_DIR_NAME="chargeV1"

# Validate variables
if [ -z "$PROJECT_MAIN_DIR_NAME" ]; then
    echo "Error: PROJECT_MAIN_DIR_NAME is not set. Please set it to your project directory name." >&2
    exit 1
fi

# Change ownership to ubuntu user
sudo chown -R ubuntu:ubuntu "/home/ubuntu/$PROJECT_MAIN_DIR_NAME"

# Create virtual environment as ubuntu
sudo -u ubuntu bash <<EOF
cd "/home/ubuntu/$PROJECT_MAIN_DIR_NAME"

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Dependencies installed successfully."
EOF
