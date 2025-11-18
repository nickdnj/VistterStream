#!/bin/bash
# Quick script to check if backend is running and accessible

echo "🔍 Checking backend status..."
echo ""

# Check if container is running
echo "1. Checking if backend container is running:"
if docker ps | grep -q vistterstream-backend; then
    echo "   ✅ Backend container is running"
    docker ps | grep vistterstream-backend
else
    echo "   ❌ Backend container is NOT running"
    echo ""
    echo "   Trying to start it..."
    docker compose -f docker-compose.rpi.yml up -d backend
    sleep 3
fi

echo ""
echo "2. Checking backend logs (last 20 lines):"
docker compose -f docker-compose.rpi.yml logs --tail=20 backend

echo ""
echo "3. Testing backend connectivity:"
if curl -s http://localhost:8000/api/auth/diagnose > /dev/null; then
    echo "   ✅ Backend is responding on localhost:8000"
    curl -s http://localhost:8000/api/auth/diagnose | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/api/auth/diagnose
else
    echo "   ❌ Backend is NOT responding on localhost:8000"
fi

echo ""
echo "4. Testing from network IP:"
if curl -s http://192.168.12.107:8000/api/auth/diagnose > /dev/null; then
    echo "   ✅ Backend is responding on 192.168.12.107:8000"
else
    echo "   ❌ Backend is NOT responding on 192.168.12.107:8000"
    echo "   (This might be normal if backend is only listening on localhost)"
fi

echo ""
echo "5. Checking backend container network:"
docker inspect vistterstream-backend | grep -A 10 "NetworkSettings" | head -15

