# # PhotoVault (Selfie Connect)

A secure, feature-rich photo management system with face recognition, secure sharing, and album organization capabilities.

## Features

- 🔐 **Secure Authentication**
  - Email/Password signup and login
  - JWT-based session management
  - Optional face recognition login

- 📸 **Photo Management**
  - Upload and organize photos
  - Automatic face detection
  - Image optimization and compression
  - EXIF metadata preservation
  - Folder organization

- 👥 **Face Recognition**
  - Automatic face detection
  - Face embedding generation
  - Similar face grouping
  - Person-based organization

- 🔄 **Sharing Features**
  - Secure sharing via QR codes
  - One-time password protection
  - Time-limited access links
  - Album sharing

- 🔍 **Advanced Search**
  - Face-based search
  - Similar image finding
  - Metadata-based filtering
  - Location-based search (if GPS data available)

## Tech Stack

### Backend
- Python 3.10+
- FastAPI
- Tortoise ORM
- PostgreSQL/SQLite
- OpenCV
- face_recognition (optional)
- PIL/Pillow

### Frontend
- Next.js 13+
- React
- TypeScript
- Tailwind CSS
- shadcn/ui components

## Installation

### Prerequisites
- Python 3.10 or higher
- Node.js 16.14 or higher
- PostgreSQL (optional, SQLite works too)
- Git

### Backend Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/zardozi12/selfie-connect.git
   cd selfie-connect
   ```

2. Create virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   source .venv/bin/activate # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp env.example .env
   # Edit .env with your settings
   ```

5. Initialize database:
   ```bash
   python -m aerich init-db
   ```

### Frontend Setup
1. Navigate to frontend directory:
   ```bash
   cd photovaultfrontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment:
   ```bash
   cp .env.example .env.local
   # Edit .env.local if needed
   ```

## Running the Application

### Start Backend
```bash
cd photovault
uvicorn app.main:app --reload --host 127.0.0.1 --port 8999
```

### Start Frontend
```bash
cd photovaultfrontend
npm run dev
```

Access the application at http://localhost:3000

## API Documentation
- Swagger UI: http://127.0.0.1:8999/docs
- ReDoc: http://127.0.0.1:8999/redoc

## Testing
```bash
# Run backend tests
pytest

# Run frontend tests
cd photovaultfrontend
npm test
```

## Configuration

### Backend Settings (.env)
- `DATABASE_URL`: Database connection string
- `JWT_SECRET`: Secret for JWT tokens
- `STORAGE_DRIVER`: 'local' or 's3'
- `FACE_RECOGNITION_ENABLED`: Enable/disable face recognition
- `EMBEDDINGS_PROVIDER`: 'none' or 'clip'

### Frontend Settings (.env.local)
- `NEXT_PUBLIC_API_URL`: Backend API URL
- `NEXT_PUBLIC_STORAGE_URL`: Media storage URL

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
MIT License

## Authors
- Original development by Selfie Connect team Backend - University Demo

A complete, free photo vault backend system built with FastAPI, PostgreSQL, and pgvector for automatic image organization, encryption, and intelligent classification.

## 🛠️ Technology Stack
- Backend: FastAPI + Python 3.11+
- Database: PostgreSQL + pgvector extension
- ORM: Tortoise ORM (async)
- Authentication: JWT + Argon2
- Encryption: Fernet (AES-128)
- Storage: Cloudinary (free tier) + Local fallback
- **AI/ML**: OpenCV, CLIP, Perceptual Hashing
- **Search**: pgvector similarity search
- **Migrations**: Aerich

## 📦 Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 13+ with pgvector extension

### 1. Clone and Setup
```bash
cd d:\projects\photovault
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Database Setup
```bash
createdb photovault
psql -d photovault -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d photovault -f "d:\projects\photovault\scripts\create_image_embeddings_table.sql"
```

### 3. Environment Configuration
Create `.env`:
```env
# Database
DATABASE_URL=postgresql://username:password@localhost/photovault

# Security
JWT_SECRET=your-super-secret-jwt-key-here
MASTER_KEY=your-master-encryption-key-here

# Storage (Optional - for cloud storage)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# App Settings
APP_ENV=dev
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Optional: Geocoding
ENABLE_GEOCODER=true
GEOCODER_EMAIL=your-email@example.com
```

### 4. Initialize Database
```bash
# Run migrations
aerich upgrade

# Or initialize fresh database
python init_db.py
```

### 5. Start the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 API Documentation

Once running, visit:
- **Interactive API Docs**: http://127.0.0.1:8999/docs
- **OpenAPI Schema**: http://127.0.0.1:8999/openapi.json

### Key Endpoints

#### Authentication
- `POST /auth/signup` - Create new account
- `POST /auth/login` - Login and get JWT token
- `GET /auth/verify` - Verify JWT token

#### Image Management
- `POST /images/upload` - Upload and process image
- `GET /images/list` - List user's images
- `GET /images/{id}/view` - View/download image

#### Album Management
- `GET /albums/` - List all albums
- `POST /albums/auto-generate` - Generate albums automatically
- `POST /albums/manual` - Create manual album
- `GET /albums/{id}/images` - Get album images

#### Search & Discovery
- `GET /search?q=query` - Semantic image search
- `GET /albums/by-location` - Group by location
- `GET /albums/by-date` - Group by date
- `GET /albums/persons` - Person clusters

#### Dashboard & Analytics
- `GET /dashboard/stats` - Overview statistics
- `GET /dashboard/recent-activity` - Recent activity feed
- `GET /dashboard/storage-analysis` - Storage usage analysis
- `GET /dashboard/person-analysis` - Person analysis
- `GET /dashboard/location-analysis` - Location analysis

## 🔐 Security Implementation

### Encryption Architecture
```
User Upload → Encrypt with User DEK → Encrypt DEK with Master Key → Store
```

1. **User DEK (Data Encryption Key)**: Each user gets a unique Fernet key
2. **Master Key**: Server master key encrypts user DEKs
3. **Image Encryption**: Images encrypted with user's DEK before storage

### Authentication Flow
1. User registers with email/password
2. Password hashed with Argon2
3. JWT token issued for session management
4. All requests require valid JWT

## 🤖 AI/ML Features

### Face Detection & Clustering
- **Detection**: OpenCV Haar cascades for face detection
- **Clustering**: Cosine similarity-based face grouping
- **Person Albums**: Automatic album creation for each person

### Image Embeddings
- **CLIP Model**: Semantic embeddings for advanced search
- **Perceptual Hashing**: Fallback for lightweight embeddings
- **pgvector**: PostgreSQL vector extension for similarity search

### Automatic Organization
- **Location-based**: GPS extraction and geocoding
- **Date-based**: Time-based album creation
- **Person-based**: Face clustering and person albums

## 💾 Storage Strategy

### Hybrid Storage System
1. **Primary**: Cloudinary free tier (25GB, 25GB bandwidth/month)
2. **Fallback**: Local file system storage
3. **Encryption**: All data encrypted before storage

### Storage Features
- **Automatic Fallback**: Seamless switch to local storage
- **Encrypted at Rest**: All data encrypted before storage
- **User Isolation**: Complete separation between users
- **Free Tier**: No credit card required

## 📊 Database Schema

### Core Tables
- **users**: User accounts and encryption keys
- **images**: Image metadata and storage references
- **faces**: Face detection results and clustering
- **person_clusters**: Grouped faces by person
- **albums**: Album definitions and metadata
- **album_images**: Many-to-many album-image relationships
- **image_embeddings**: Vector embeddings for search

### Relationships
```
User → Images → Faces → PersonClusters
User → Albums → AlbumImages → Images
Images → ImageEmbeddings (pgvector)
```

## 🚀 Deployment

### Development
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8999 --reload
```

### Production
```bash
# Using Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Using Docker
docker-compose up -d
```

## 🔧 Configuration Options

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET`: JWT signing secret
- `MASTER_KEY`: Master encryption key
- `STORAGE_DRIVER`: Storage backend (local/cloudinary)
- `EMBEDDINGS_PROVIDER`: Embedding method (clip/phash)
- `ENABLE_GEOCODER`: Enable location geocoding

### Feature Flags
- **CLIP Embeddings**: Set `EMBEDDINGS_PROVIDER=clip`
- **Cloud Storage**: Configure Cloudinary credentials
- **Geocoding**: Set `ENABLE_GEOCODER=true`

## 📈 Performance Considerations

### Optimization Strategies
- **Async Operations**: All I/O operations are async
- **Connection Pooling**: Database connection pooling
- **Caching**: Embedding and metadata caching
- **Background Processing**: Album generation in background
- **Lazy Loading**: Related data loaded on demand

### Scalability
- **Horizontal Scaling**: Stateless API design
- **Database Indexing**: Optimized indexes for queries
- **Vector Search**: Efficient similarity search with pgvector
- **Storage Tiering**: Cloud + local hybrid storage

## 🧪 Testing

### API Testing
```bash
# Using the interactive docs
curl -X POST "http://127.0.0.1:8999/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","name":"Test User"}'
```

### Database Testing
```bash
# Test pgvector
psql photovault -c "SELECT '[1,2,3]'::vector;"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is for educational/demo purposes. Feel free to use and modify.

## 🆘 Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the logs for error details
3. Ensure all environment variables are set correctly
4. Verify database and pgvector extension are working

## 🎯 Demo Workflow

1. **User Registration**: Create account with email/password
2. **Image Upload**: Upload photos (automatically processed)
3. **Automatic Organization**: 
   - Face detection and clustering
   - Location extraction and geocoding
   - Album generation by location/date/person
4. **Dashboard View**: See analytics and organized photos
5. **Search & Discovery**: Find photos by description, location, person
6. **Album Management**: View and manage auto-generated albums

The system provides a complete, production-ready photo vault backend with advanced AI features, all using free services and no credit card requirements.
