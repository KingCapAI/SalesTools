# King Cap HQ

Internal sales team dashboard for King Cap with AI-powered hat design generation.

## Features

- **AI Design Generator**: Create custom hat designs using Google Gemini 2.5 Flash
  - Upload client logos and brand guidelines
  - AI-powered brand scraping from URLs
  - Multiple hat styles and materials
  - Version management (Design #1v1, #1v2, etc.)
  - Chat-based revision requests
  - Filterable design history

- **Quote Estimator**: Calculate pricing for custom orders (Coming Soon)
- **Marketing Tools**: Access marketing materials and templates (Coming Soon)
- **Policies and Processes**: Company documentation (Coming Soon)

## Tech Stack

- **Backend**: Python FastAPI + SQLAlchemy + SQLite
- **Frontend**: React 18 + Vite + TypeScript + Tailwind CSS
- **Authentication**: Google/Microsoft SSO (OAuth2)
- **AI**: Google Gemini 2.5 Flash API

## Prerequisites

- Python 3.10+
- Node.js 18+
- Google Cloud Console account (for OAuth)
- Azure AD account (for Microsoft OAuth)
- Google AI Studio account (for Gemini API key)

## Setup

### 1. Clone and Navigate

```bash
cd SalesTools
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys and OAuth credentials

# Run the backend
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env

# Run the frontend
npm run dev
```

### 4. Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Environment Variables

### Backend (.env)

```
DATABASE_URL=sqlite:///./data/kingcap.db
JWT_SECRET=your-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_TENANT_ID=your-tenant-id
GOOGLE_GEMINI_API_KEY=your-gemini-api-key
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
```

### Frontend (.env)

```
VITE_API_URL=http://localhost:8000/api
```

## OAuth Setup

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:8000/api/auth/google/callback`
6. Copy Client ID and Client Secret to `.env`

### Microsoft OAuth

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to Azure Active Directory > App registrations
3. Create new registration
4. Add redirect URI: `http://localhost:8000/api/auth/microsoft/callback`
5. Create a client secret
6. Copy Application (client) ID, Directory (tenant) ID, and secret to `.env`

## Project Structure

```
SalesTools/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── config.py         # Configuration
│   │   ├── database.py       # Database setup
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── routers/          # API routes
│   │   ├── services/         # Business logic
│   │   └── utils/            # Utilities
│   ├── uploads/              # File storage
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/              # API client
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom hooks
│   │   ├── context/          # React context
│   │   └── types/            # TypeScript types
│   └── package.json
│
└── README.md
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

Proprietary - King Cap internal use only.
