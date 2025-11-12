# Projects Tracking Tool# PR Tracker



A comprehensive tool for tracking GitHub pull requests and student project submissions. This application consists of a React frontend and a Node.js backend with MongoDB integration.## Setup



## 📋 Table of Contents1. Clone the repository.

2. Navigate to  directory.

- [Features](#features)3. Create an `.env` file in the  directory with the following variables:

- [Tech Stack](#tech-stack)

- [Project Structure](#project-structure)    ```env

- [Prerequisites](#prerequisites)    GITHUB_TOKEN=your_github_personal_access_token

- [Installation](#installation)    MONGO_URI=your_mongodb_connection_string

- [Configuration](#configuration)    ```

- [Usage](#usage)

- [API Documentation](#api-documentation)4. Run `npm install` in the  directory.

- [Contributing](#contributing)5. Start the server with `npm start`.

- [License](#license)# projects_tracking_tool


## ✨ Features

- 📊 Track GitHub pull requests across multiple repositories
- 👥 Monitor student project submissions
- 📈 Generate analytics and reports
- 🔄 Automated data fetching from GitHub API
- 💾 MongoDB integration for data persistence
- 🎨 Modern React UI with TypeScript
- 🔐 Secure environment configuration

## 🛠️ Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** - Fast build tool and dev server
- **Modern ES modules**

### Backend
- **Node.js** with Express
- **MongoDB** with Mongoose ODM
- **GitHub API** integration via Axios
- **Better-SQLite3** for local caching
- **Python scripts** for data analysis

## 📁 Project Structure

```
projects-tracking-tool/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── assets/          # Static assets
│   │   ├── App.tsx          # Main App component
│   │   └── main.tsx         # Entry point
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                 # Node.js backend
│   ├── src/
│   │   ├── server.js        # Express server entry point
│   │   ├── models/          # MongoDB models
│   │   ├── routes/          # API routes
│   │   ├── controllers/     # Route controllers
│   │   ├── utils/           # Utility functions
│   │   ├── scripts/         # Automation scripts
│   │   ├── config/          # Configuration files
│   │   └── public/          # Static files
│   └── package.json
│
├── data/                    # Data files and samples
├── docs/                    # Documentation
├── cloned_repos/           # Cloned GitHub repositories
├── .env.example            # Environment variables template
├── .gitignore
└── README.md
```

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v18 or higher)
- **npm** or **yarn**
- **MongoDB** (local or cloud instance)
- **Python** (v3.8 or higher) for analysis scripts
- **Git**

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Newton-School/projects_tracking_tool.git
cd projects_tracking_tool
```

### 2. Install Backend Dependencies

```bash
cd backend
npm install
```

### 3. Install Frontend Dependencies

```bash
cd ../frontend
npm install
```

## ⚙️ Configuration

### 1. Create Environment File

Copy the `.env.example` file to `.env` in the root directory:

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit the `.env` file with your credentials:

```env
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database_name

# GitHub API Token
GITHUB_TOKEN=your_github_personal_access_token_here

# Server Configuration (optional)
PORT=3000
NODE_ENV=development
```

### 3. Generate GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `read:org`, `read:user`
4. Copy the token and add it to your `.env` file

## 🏃‍♂️ Usage

### Running the Backend

```bash
cd backend

# Setup database (first time only)
npm run setup

# Start the server
npm start

# Or run in development mode with auto-reload
npm run dev
```

The backend server will start on `http://localhost:3000`

### Running the Frontend

```bash
cd frontend

# Start the development server
npm run dev
```

The frontend will start on `http://localhost:5173`

### Running Scripts

```bash
cd backend

# Fetch pull requests from GitHub
npm run fetch-prs

# Run Python analysis scripts
python src/scripts/evaluate_projects_csv.py
```

## 📚 API Documentation

### Base URL
```
http://localhost:3000/api
```

### Endpoints

#### Get All Projects
```
GET /api/projects
```

#### Get Project by ID
```
GET /api/projects/:id
```

#### Get Pull Requests
```
GET /api/pullrequests
```

#### Get User Statistics
```
GET /api/stats/:username
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the ISC License.

## 🙏 Acknowledgments

- Newton School for the project requirements
- GitHub API for data access
- MongoDB for database services

## 📞 Support

For support, email support@newtonschool.co or create an issue in the repository.

---

Made with ❤️ by Newton School
