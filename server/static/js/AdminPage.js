// AdminPage.js

const CreateFavoriteForm = ({ onCreateFavorite }) => {
    const formElement = document.createElement('form');
    formElement.className = 'mb-8 p-4 bg-white rounded shadow';
    formElement.innerHTML = `
      <h2 class="text-xl font-bold mb-4">Create Favorite</h2>
      <div class="mb-4">
        <label for="url" class="block text-sm font-medium text-gray-700">URL</label>
        <input type="url" id="url" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
      </div>
      <div class="mb-4">
        <label for="title" class="block text-sm font-medium text-gray-700">Title</label>
        <input type="text" id="title" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
      </div>
      <button type="submit" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
        Create Favorite
      </button>
    `;
  
    formElement.addEventListener('submit', (e) => {
      e.preventDefault();
      const url = formElement.querySelector('#url').value;
      const title = formElement.querySelector('#title').value;
      onCreateFavorite({ url, title });
      formElement.reset();
    });
  
    return formElement;
  };
  
  const TaskList = ({ tasks }) => {
    const taskListElement = document.createElement('div');
    taskListElement.className = 'bg-white rounded shadow p-4';
    taskListElement.innerHTML = `
      <h2 class="text-xl font-bold mb-4">Running Tasks</h2>
      ${tasks.length === 0 
        ? '<p>No running tasks.</p>'
        : `<ul class="divide-y divide-gray-200">
            ${tasks.map(task => `
              <li class="py-4">
                <div class="flex items-center space-x-4">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">${task.title}</p>
                    <p class="text-sm text-gray-500">${task.status}</p>
                  </div>
                  <div class="inline-flex items-center text-base font-semibold text-gray-900">
                    ${task.progress}%
                  </div>
                </div>
              </li>
            `).join('')}
          </ul>`
      }
    `;
  
    return taskListElement;
  };
  
  class AdminPage {
    constructor(rootElement) {
      this.rootElement = rootElement;
      this.tasks = [];
      this.init();
    }
  
    init() {
      this.render();
      this.fetchTasks();
      setInterval(() => this.fetchTasks(), 5000);
    }
  
    async fetchTasks() {
      try {
        const response = await fetch('/api/favorites/tasks');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        this.tasks = await response.json();
        this.updateTaskList();
      } catch (error) {
        console.error('Error fetching tasks:', error);
      }
    }
  
    async handleCreateFavorite(favoriteData) {
      try {
        const response = await fetch('/api/favorites/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(favoriteData),
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        console.log('Favorite created:', result);
        // Optionally, you can update the task list or show a success message
      } catch (error) {
        console.error('Error creating favorite:', error);
        // Optionally, you can show an error message to the user
      }
    }
  
    render() {
      this.rootElement.innerHTML = `
        <div class="container mx-auto px-4 py-8">
          <h1 class="text-3xl font-bold mb-8">Admin Dashboard</h1>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div id="create-favorite-form"></div>
            <div id="task-list"></div>
          </div>
        </div>
      `;
  
      const createFavoriteForm = CreateFavoriteForm({ onCreateFavorite: this.handleCreateFavorite.bind(this) });
      this.rootElement.querySelector('#create-favorite-form').appendChild(createFavoriteForm);
  
      this.updateTaskList();
    }
  
    updateTaskList() {
      const taskListContainer = this.rootElement.querySelector('#task-list');
      taskListContainer.innerHTML = '';
      const taskList = TaskList({ tasks: this.tasks });
      taskListContainer.appendChild(taskList);
    }
  }
  
  // Initialize the admin page
  document.addEventListener('DOMContentLoaded', () => {
    const rootElement = document.getElementById('root');
    new AdminPage(rootElement);
  });