#!/bin/bash

echo "🚀 Starting deployment..."

cd ~/chargeV1 || exit

# Setup virtualenv
if [ ! -d "venv" ]; then
    echo "🧪 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Apply migrations
echo "🗃️ Applying database migrations..."
python manage.py migrate

# Collect static files
echo "🧹 Collecting static files..."
python manage.py collectstatic --noinput

# Restart Gunicorn (systemd)
echo "🔁 Restarting Gunicorn..."
sudo systemctl restart gunicorn

# Reload Nginx
echo "🔄 Reloading Nginx..."
sudo systemctl reload nginx

echo "✅ Deployment complete!"
