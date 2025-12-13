# Create root backend directory
New-Item -ItemType Directory -Path "backend"
Set-Location "backend"

# Create subfolders
$folders = @(
    "app",
    "app/models",
    "app/graphql",
    "app/services",
    "app/utils",
    "app/tasks",
    "app/config",
    "tests"
)

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Path $folder
}

# Create main Python files
New-Item -ItemType File -Path "app/main.py"
New-Item -ItemType File -Path "app/graphql/schema.py"
New-Item -ItemType File -Path "app/graphql/queries.py"
New-Item -ItemType File -Path "app/graphql/mutations.py"
New-Item -ItemType File -Path "app/graphql/subscriptions.py"

New-Item -ItemType File -Path "app/models/predictor.py"
New-Item -ItemType File -Path "app/models/data_point.py"

New-Item -ItemType File -Path "app/services/fetcher.py"
New-Item -ItemType File -Path "app/services/alert_service.py"
New-Item -ItemType File -Path "app/services/price_cache.py"

New-Item -ItemType File -Path "app/tasks/runner.py"

New-Item -ItemType File -Path "app/utils/logger.py"
New-Item -ItemType File -Path "app/config/settings.py"

# Create placeholder test
New-Item -ItemType File -Path "tests/test_basic.py"

# Create requirements file
Set-Content -Path "requirements.txt" -Value @"
fastapi
uvicorn
strawberry-graphql
yfinance
pydantic
scikit-learn
pandas
numpy
websockets
redis
python-dotenv
"@

Write-Host "Backend structure created successfully!"
