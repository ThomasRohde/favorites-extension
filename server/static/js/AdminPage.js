import React, { useState, useEffect } from 'react';

const CreateFavoriteForm = ({ onCreateFavorite }) => {
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onCreateFavorite({ url, title });
    setUrl('');
    setTitle('');
  };

  return (
    <form onSubmit={handleSubmit} className="mb-8 p-4 bg-white rounded shadow">
      <h2 className="text-xl font-bold mb-4">Create Favorite</h2>
      <div className="mb-4">
        <label htmlFor="url" className="block text-sm font-medium text-gray-700">URL</label>
        <input
          type="url"
          id="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
        />
      </div>
      <div className="mb-4">
        <label htmlFor="title" className="block text-sm font-medium text-gray-700">Title</label>
        <input
          type="text"
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
        />
      </div>
      <button type="submit" className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
        Create Favorite
      </button>
    </form>
  );
};

const TaskList = ({ tasks }) => {
  return (
    <div className="bg-white rounded shadow p-4">
      <h2 className="text-xl font-bold mb-4">Running Tasks</h2>
      {tasks.length === 0 ? (
        <p>No running tasks.</p>
      ) : (
        <ul className="divide-y divide-gray-200">
          {tasks.map((task) => (
            <li key={task.id} className="py-4">
              <div className="flex items-center space-x-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{task.title}</p>
                  <p className="text-sm text-gray-500">{task.status}</p>
                </div>
                <div className="inline-flex items-center text-base font-semibold text-gray-900">
                  {task.progress}%
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const AdminPage = () => {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    // Fetch initial tasks
    fetchTasks();
    // Set up polling for task updates
    const interval = setInterval(fetchTasks, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch('/api/tasks');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const handleCreateFavorite = async (favoriteData) => {
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
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <CreateFavoriteForm onCreateFavorite={handleCreateFavorite} />
        <TaskList tasks={tasks} />
      </div>
    </div>
  );
};

export default AdminPage;