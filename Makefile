.PHONY: dev install clean test

install:
	@echo "Installing Python dependencies..."
	uv pip install -r requirements.txt
	@echo "Installing Node.js dependencies..."
	pnpm install

dev:
	@echo "Starting development servers..."
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

setup-env:
	@echo "Creating environment file..."
	@if [ ! -f .env.local ]; then \
		echo "NEXT_PUBLIC_SUPABASE_URL=your_supabase_url" > .env.local; \
		echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key" >> .env.local; \
		echo "SUPABASE_SERVICE_ROLE_KEY=your_service_role_key" >> .env.local; \
		echo "OPENAI_API_KEY=your_openai_api_key" >> .env.local; \
		echo "COHERE_API_KEY=your_cohere_api_key" >> .env.local; \
		echo "NOTION_CLIENT_ID=your_notion_client_id" >> .env.local; \
		echo "NOTION_CLIENT_SECRET=your_notion_client_secret" >> .env.local; \
		echo "Environment file created. Please update with your actual keys."; \
	else \
		echo "Environment file already exists."; \
	fi