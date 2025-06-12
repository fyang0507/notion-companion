.PHONY: dev dev-backend dev-frontend install clean test setup-env sync-notion

install:
	@echo "Installing Python dependencies..."
	cd backend && uv venv .venv
	cd backend && uv pip install -r requirements.in
	@echo "Installing Node.js dependencies..."
	pnpm install

dev:
	@echo "Starting development servers..."
	pnpm run dev:full

dev-backend:
	@echo "Starting backend server only..."
	cd backend && .venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "Starting frontend server only..."
	pnpm run dev

build:
	@echo "Building application..."
	pnpm run build

clean:
	@echo "Cleaning up..."
	rm -rf .next
	rm -rf node_modules
	rm -rf __pycache__

test:
	@echo "Running tests..."
	# Add test commands here

sync-notion:
	@echo "Syncing Notion databases..."
	cd backend && ./sync_notion_databases.sh

setup-env:
	@echo "Creating environment files..."
	@if [ ! -f .env.local ]; then \
		echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local; \
		echo "NEXT_PUBLIC_SUPABASE_URL=your_supabase_url" >> .env.local; \
		echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key" >> .env.local; \
		echo "Frontend environment file created."; \
	else \
		echo "Frontend environment file already exists."; \
	fi
	@if [ ! -f backend/.env ]; then \
		cp backend/.env.example backend/.env; \
		echo "Backend environment file created. Please update with your actual keys."; \
	else \
		echo "Backend environment file already exists."; \
	fi