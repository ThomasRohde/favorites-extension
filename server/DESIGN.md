# Microsoft Edge Intelligent Favorites Extension - Design Document

## 1. Introduction

This document outlines the design for an intelligent favorites management extension for Microsoft Edge. The extension will allow users to store, organize, summarize, and search their favorites using advanced natural language processing techniques.

## 2. System Architecture

The system consists of two main components:
1. Backend API (Python-based)
2. Frontend Extension (Microsoft Edge Extension)

### 2.1 Backend API

- Framework: FastAPI
- Database: SQLite (for structured data) and Chroma.db (for vector embeddings)
- NLP Models: 
  - LLM: phi3.5 (via Ollama) for chat completion and summarization
  - Embeddings: nomic-embed-text (via Ollama) for semantic search and clustering
- Deployment: Windows Service

### 2.2 Frontend Extension

- Technologies: HTML, CSS, JavaScript
- API Communication: Fetch API

## 3. Data Model

### 3.1 SQLite Schema

```sql
-- Folders table
CREATE TABLE folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES folders(id)
);

-- Favorites table
CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    folder_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (folder_id) REFERENCES folders(id)
);

-- Tags table
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Favorites-Tags association table
CREATE TABLE favorites_tags (
    favorite_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (favorite_id, tag_id),
    FOREIGN KEY (favorite_id) REFERENCES favorites(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
```

### 3.2 Chroma.db Schema

Collection name: `favorites_embeddings`

Schema:
- id: favorite.id
- embedding: nomic-embed-text generated embedding
- metadata:
  - url: favorite.url
  - title: favorite.title
  - summary: favorite.summary
  - folder_id: favorite.folder_id
  - tags: comma-separated list of tag names

## 4. API Endpoints

### 4.1 Favorites Management

- POST /api/favorites
  - Add a new favorite
  - Parameters: url, content (optional), folder_id (optional)
  - Returns: Favorite object with generated summary and suggested tags

- GET /api/favorites/{id}
  - Retrieve a specific favorite
  - Returns: Favorite object with all associated data

- PUT /api/favorites/{id}
  - Update a favorite
  - Parameters: title, summary, folder_id, tags

- DELETE /api/favorites/{id}
  - Remove a favorite

- GET /api/favorites
  - List favorites
  - Parameters: folder_id (optional), tag (optional), search_query (optional)
  - Returns: List of favorite objects

### 4.2 Folder Management

- POST /api/folders
  - Create a new folder
  - Parameters: name, parent_id (optional), description

- GET /api/folders/{id}
  - Retrieve folder details

- PUT /api/folders/{id}
  - Update folder information
  - Parameters: name, parent_id, description

- DELETE /api/folders/{id}
  - Remove a folder
  - Parameters: move_to_parent (boolean, optional)

- GET /api/folders
  - List folder structure
  - Returns: Tree-like structure of folders

### 4.3 Search and Suggestions

- POST /api/search
  - Perform semantic search on favorites
  - Parameters: query, limit (optional)

- GET /api/suggest-tags
  - Get tag suggestions for given content
  - Parameters: content or url

- GET /api/suggest-folder
  - Get folder placement suggestion for given content
  - Parameters: content or url

## 5. Key Features and Workflows

### 5.1 Adding a New Favorite

1. User clicks the extension button or uses a keyboard shortcut
2. Extension frontend sends the current page URL to the backend
3. Backend scrapes the content (if not provided) and processes it:
   a. Generates a summary using phi3.5
   b. Creates an embedding using nomic-embed-text
   c. Suggests tags based on content clustering
   d. Suggests a folder based on content analysis
4. User reviews and optionally modifies the suggestions
5. Favorite is saved to the database with all associated data

### 5.2 Searching Favorites

1. User enters a search query in the extension's search bar
2. Query is sent to the backend
3. Backend performs:
   a. Semantic search using Chroma.db
   b. Optional keyword-based search on titles and summaries
4. Results are returned and displayed in the extension UI

### 5.3 Organizing Favorites

1. User navigates the folder structure in the extension UI
2. When moving a favorite:
   a. User selects the favorite and chooses "Move"
   b. Backend suggests folders based on content similarity
   c. User selects a destination folder
   d. Backend updates the favorite's folder_id

## 6. LLM Integration

### 6.1 Content Summarization

- Use phi3.5 to generate concise summaries (2-3 sentences) of favorited web pages
- Prompt engineering will be crucial for consistent, high-quality summaries

### 6.2 Folder Suggestions

- Analyze the content and existing folder structure
- Use phi3.5 to suggest the most appropriate existing folder or propose a new one
- Generate folder descriptions for new folders

### 6.3 Tag Generation

- Use nomic-embed-text to create embeddings for favorites
- Cluster similar favorites and use phi3.5 to generate descriptive tags for each cluster

## 7. Extension UI Design

### 7.1 Popup Interface

- Quick add favorite button
- Search bar
- Recent favorites list
- Quick access to main categories/folders

### 7.2 Full Page Interface

- Complete folder structure navigation
- Advanced search options
- Favorite management (edit, move, delete)
- Tag management
- Settings and customization options

## 8. Security and Privacy

- Implement user authentication for API access
- Use HTTPS for all API communications
- Store sensitive data (e.g., authentication tokens) securely
- Provide options for users to control data storage and deletion

## 9. Performance Optimization

- Implement caching strategies for frequently accessed data
- Use background scripts for time-consuming tasks (e.g., content scraping, summarization)
- Optimize database queries and indexing

## 10. Future Enhancements

- Multi-device synchronization
- Collaborative sharing of favorites and folders
- Integration with other browsers or platforms
- Advanced analytics on browsing habits and favorite usage

## 11. Testing Strategy

- Unit tests for backend API functions
- Integration tests for database operations and LLM integrations
- End-to-end tests for extension workflows
- User acceptance testing for UI/UX

## 12. Deployment and Maintenance

### 12.1 Windows Service Setup

- Implement the API server as a Windows service for automatic startup and background operation
- Use a service management library like `win32serviceutil` or `pywin32` for service implementation
- Create service installation and configuration scripts
- Implement logging for service status and error reporting
- Ensure proper error handling and automatic restart capabilities

### 12.2 Service Configuration

- Create a configuration file for service parameters (e.g., port, database location, log file location)
- Implement a method to update service configuration without reinstallation

### 12.3 Monitoring and Management

- Develop a simple management UI or CLI tool for:
  - Starting/stopping the service
  - Viewing service status
  - Accessing logs
  - Updating configuration

### 12.4 Continuous Integration and Deployment

- Set up CI/CD pipeline for automated testing and deployment
- Include service installation and update procedures in the deployment process
- Implement version control for the service configuration

### 12.5 Regular Maintenance

- Monitor API performance and error rates
- Regularly update dependencies and LLM models
- Provide user support and feature request channels
- Schedule regular database backups and maintenance tasks

This design document provides a comprehensive overview of the Microsoft Edge Intelligent Favorites Extension project, including its implementation as a Windows service. It serves as a blueprint for development and can be updated as the project evolves.