Write-Host "Starting Docker Compose (PostgreSQL & Redis)..."
docker-compose up -d

Write-Host "Starting Backend API Request..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Starting Celery ML Worker..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd worker; .\venv\Scripts\activate; celery -A celery_app worker --loglevel=info --pool=solo"

Write-Host "Starting Next.js Frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "AudioShield Stack Launched!"
Write-Host "Frontend is running at: http://localhost:3000"
Write-Host "Backend API is running at: http://localhost:8000"
