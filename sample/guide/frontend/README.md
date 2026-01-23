# AF Guide Frontend

ChatKit-based frontend for AF Guide.

## Requirements

- Node.js >= 18.18
- npm >= 9

## Setup

1. Install dependencies:

```bash
npm install
```

2. Create environment file:

```bash
cp .env.example .env.local
```

3. Start the development server:

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## Backend

Start the backend server before using the frontend (from project root):

```bash
uv run --group sample uvicorn sample.guide.server:app --reload --port 8000
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_CHATKIT_API_URL` | Backend API endpoint | `http://localhost:8000/chatkit` |
| `VITE_CHATKIT_API_DOMAIN_KEY` | ChatKit domain key | `domain_pk_localhost_dev` |
