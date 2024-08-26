# Intelligent Favorites Extension

## Overview

The Intelligent Favorites Extension is a sophisticated browser extension designed to enhance the bookmarking experience. It leverages advanced natural language processing techniques to automatically categorize, summarize, and tag web pages, making it easier for users to organize and retrieve their favorite content.

## Features

- **Automatic Summarization**: Generates concise summaries of bookmarked web pages using advanced NLP models.
- **Intelligent Tagging**: Suggests relevant tags based on the content of the bookmarked page.
- **Smart Folder Organization**: Recommends appropriate folders for new bookmarks based on their content.
- **Semantic Search**: Enables users to find bookmarks using natural language queries.
- **Browser Integration**: Seamlessly integrates with Microsoft Edge as a browser extension.
- **Web Interface**: Provides a user-friendly web interface for managing bookmarks, folders, and tags.
- **API Backend**: Powered by a robust FastAPI backend for efficient data management and processing.

## System Architecture

The system consists of two main components:

1. **Backend API** (Python-based)
   - Framework: FastAPI
   - Database: SQLite (structured data) and Chroma.db (vector embeddings)
   - NLP Models: 
     - LLM: phi3.5 (via Ollama) for chat completion and summarization
     - Embeddings: nomic-embed-text (via Ollama) for semantic search and clustering
   - Deployment: Windows Service

2. **Frontend Extension** (Microsoft Edge Extension)
   - Technologies: HTML, CSS, JavaScript
   - API Communication: Fetch API

## Installation

### Backend Setup

1. Clone the repository:
   ```
   git clone https://github.com/your-repo/intelligent-favorites.git
   cd intelligent-favorites
   ```

2. Install required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```
   python initDB.py
   ```

4. Start the FastAPI server:
   ```
   uvicorn main:app --reload
   ```

### Extension Setup

1. Open Microsoft Edge and navigate to `edge://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension` folder from the cloned repository

## Usage

1. **Adding a Favorite**: 
   - Click the extension icon in your browser
   - Review the automatically generated title and click "Add Favorite"

2. **Viewing Favorites**:
   - Open the main page by clicking "Open Main Page" in the extension popup
   - Browse your favorites, organized by folders and tags

3. **Searching Favorites**:
   - Use the search bar on the main page to find favorites using natural language queries

4. **Managing Folders and Tags**:
   - Use the web interface to create, edit, or delete folders and tags

5. **Accessing Admin Features**:
   - Click "Open Admin Page" in the extension popup to access advanced management features

## Development

- Backend code is located in the `server` directory
- Frontend extension code is in the `extension` directory
- Run tests using `pytest`:
  ```
  pytest api_test.py
  ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Icons provided by [Icons8](https://icons8.com)
- NLP models and services:
  - [Ollama](https://ollama.ai/) - Local LLM inference
  - [OpenAI](https://openai.com/) - Cloud-based LLM services
  - [Anthropic](https://www.anthropic.com/) - Advanced AI models including Claude
- Frontend libraries:
  - [React](https://reactjs.org/)
  - [Tailwind CSS](https://tailwindcss.com/)