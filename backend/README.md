# Backend - Projects Tracking Tool

Backend API server for the Projects Tracking Tool built with Node.js, Express, and MongoDB.

## 🚀 Getting Started

### Install Dependencies

```bash
npm install
```

### Setup Database

```bash
npm run setup
```

### Start Server

```bash
# Production
npm start

# Development (with auto-reload)
npm run dev
```

## 📁 Directory Structure

```
backend/
├── src/
│   ├── server.js           # Main server entry point
│   ├── models/             # MongoDB/Mongoose models
│   ├── routes/             # Express route definitions
│   ├── controllers/        # Route controllers
│   ├── utils/              # Utility functions
│   │   └── githubUtils.cjs # GitHub API utilities
│   ├── scripts/            # Automation scripts
│   │   ├── 1_setupDatabase.cjs
│   │   ├── 2_fetchPRs.cjs
│   │   ├── clonerepos.cjs
│   │   └── s_import-usernames.cjs
│   ├── config/             # Configuration files
│   └── public/             # Static files
└── package.json
```

## 🔧 Available Scripts

- `npm start` - Start the production server
- `npm run dev` - Start development server with auto-reload
- `npm run setup` - Setup database
- `npm run fetch-prs` - Fetch pull requests from GitHub

## 🌐 API Endpoints

See main README.md for complete API documentation.

## 📦 Dependencies

- **express** - Web framework
- **mongoose** - MongoDB ODM
- **axios** - HTTP client for GitHub API
- **cors** - CORS middleware
- **dotenv** - Environment variables
- **better-sqlite3** - SQLite database

## ⚙️ Environment Variables

Required environment variables (create `.env` file in project root):

```env
MONGODB_URI=your_mongodb_connection_string
GITHUB_TOKEN=your_github_personal_access_token
PORT=3000
```
