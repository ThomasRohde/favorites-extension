const { useState, useEffect } = React;

const Modal = ({ isOpen, onClose, onSubmit, title, children }) => {
  if (!isOpen) return null;

  return React.createElement('div', {
    className: 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full',
    onClick: onClose
  },
    React.createElement('div', {
      className: 'relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white',
      onClick: e => e.stopPropagation()
    },
      React.createElement('h3', { className: 'text-lg font-medium leading-6 text-gray-900 mb-2' }, title),
      children,
      React.createElement('div', { className: 'mt-4 flex justify-end' },
        React.createElement('button', {
          onClick: onClose,
          className: 'px-4 py-2 bg-gray-300 text-gray-800 text-base font-medium rounded-md w-24 mr-2'
        }, 'Cancel'),
        React.createElement('button', {
          onClick: onSubmit,
          className: 'px-4 py-2 bg-blue-500 text-white text-base font-medium rounded-md w-24'
        }, 'Submit')
      )
    )
  );
};

const MainPage = () => {
  const [folders, setFolders] = useState([]);
  const [expandedFolders, setExpandedFolders] = useState({});
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [favorites, setFavorites] = useState([]);
  const [error, setError] = useState(null);
  const [expandedDescriptions, setExpandedDescriptions] = useState({});
  const [hoveredFolder, setHoveredFolder] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [newFolderDescription, setNewFolderDescription] = useState('');

  useEffect(() => {
    fetchFolders();
    fetchAllFavorites();
  }, []);

  useEffect(() => {
    if (selectedFolder) {
      console.log('Selected folder:', selectedFolder);
      fetchFavoritesForFolder(selectedFolder);
    } else {
      fetchAllFavorites();
    }
  }, [selectedFolder]);

  const fetchFolders = async () => {
    try {
      const response = await fetch('/api/folders/');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Fetched folders:', data);
      const updatedData = data.map(folder => 
        folder.name === "Root" ? { ...folder, name: "Favorites" } : folder
      );
      setFolders(updatedData || []);
    } catch (error) {
      console.error('Error fetching folders:', error);
      setError('Failed to fetch folders. Please try again later.');
      setFolders([]);
    }
  };

  const fetchAllFavorites = async () => {
    try {
      const response = await fetch('/api/favorites');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Fetched all favorites:', data);
      setFavorites(data || []);
    } catch (error) {
      console.error('Error fetching all favorites:', error);
      setError('Failed to fetch favorites. Please try again later.');
      setFavorites([]);
    }
  };

  const fetchFavoritesForFolder = async (folder) => {
    if (folder.name === "Favorites") {
      fetchAllFavorites();
      return;
    }
    try {
      const response = await fetch(`/api/folders/${folder.id}/favorites?include_children=true`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Fetched favorites for folder:', data);
      setFavorites(data || []);
    } catch (error) {
      console.error('Error fetching favorites for folder:', error);
      setError('Failed to fetch favorites. Please try again later.');
      setFavorites([]);
    }
  };

  const toggleFolder = (folderId, e) => {
    e.stopPropagation();
    if (folderId == null) return;
    setExpandedFolders(prev => ({
      ...prev,
      [folderId]: !prev[folderId]
    }));
  };

  const toggleDescription = (favoriteId) => {
    setExpandedDescriptions(prev => ({
      ...prev,
      [favoriteId]: !prev[favoriteId]
    }));
  };

  const truncateText = (text, maxLength) => {
    if (text.length <= maxLength) return text;
    return text.substr(0, maxLength) + '...';
  };

  const createFolder = async () => {
    if (!newFolderName.trim()) {
      setError('Please enter a folder name.');
      return;
    }
    try {
      const response = await fetch('/api/folders/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          name: newFolderName,
          description: newFolderDescription,
          parent_id: selectedFolder ? selectedFolder.id : null
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      setNewFolderName('');
      setNewFolderDescription('');
      setIsModalOpen(false);
      fetchFolders();
      setError(null);
    } catch (error) {
      console.error('Error creating folder:', error);
      setError('Failed to create folder. Please try again later.');
    }
  };

  const getFolderPath = (folderId) => {
    const path = [];
    let currentFolder = findFolderRecursive(folders, folderId);
    while (currentFolder) {
      path.unshift(currentFolder.name);
      currentFolder = findFolderRecursive(folders, currentFolder.parent_id);
    }
    return path.join(' > ');
  };


  const fetchFolderDetails = async (folderId) => {
    try {
      const response = await fetch(`/api/folders/${folderId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching folder details:', error);
      throw error;
    }
  };

  const findFolderRecursive = (folders, id) => {
    for (let folder of folders) {
      if (folder.id === id) {
        return folder;
      }
      if (folder.children && folder.children.length > 0) {
        const found = findFolderRecursive(folder.children, id);
        if (found) {
          return found;
        }
      }
    }
    return null;
  };

  const deleteFolder = async (folderId) => {
    if (folderId === null) {
      setError('Cannot delete an invalid folder.');
      return;
    }
    
    const folderToDelete = findFolderRecursive(folders, folderId);
    
    if (!folderToDelete) {
      setError('Folder not found. It may have been already deleted.');
      return;
    }
    
    if (folderToDelete.name === "Favorites") {
      setError('Cannot delete the root folder.');
      return;
    }
    
    try {
      const response = await fetch(`/api/folders/${folderId}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      await fetchFolders();
      if (selectedFolder && selectedFolder.id === folderId) {
        setSelectedFolder(null);
      }
      setError(null); // Clear any previous errors
    } catch (error) {
      console.error('Error deleting folder:', error);
      setError('Failed to delete folder. Please try again later.');
    }
  };

  const renderFolderTree = (folder) => {
    if (!folder || folder.id == null) return null;
    const isExpanded = expandedFolders[folder.id];
    const hasChildren = folder.children && folder.children.length > 0;

    return React.createElement('div', { 
      key: folder.id, 
      className: 'ml-4',
      onMouseEnter: () => setHoveredFolder(folder.id),
      onMouseLeave: () => setHoveredFolder(null)
    },
      React.createElement('div', {
        className: `flex items-center cursor-pointer p-2 hover:bg-gray-100 ${
          selectedFolder && selectedFolder.id === folder.id ? 'bg-blue-100' : ''
        }`,
        onClick: () => setSelectedFolder(folder)
      },
        React.createElement('span', { 
          className: 'mr-2', 
          onClick: (e) => toggleFolder(folder.id, e)
        }, hasChildren ? (isExpanded ? '📂' : '📁') : '📄'),
        React.createElement('span', { className: 'flex-grow' }, folder.name),
        folder.name !== "Favorites" && hoveredFolder === folder.id && React.createElement('button', {
          onClick: (e) => {
            e.stopPropagation();
            deleteFolder(folder.id);
          },
          className: 'text-red-500 hover:text-red-700'
        }, '🗑️')
      ),
      isExpanded && hasChildren && 
        React.createElement('div', { className: 'ml-4' },
          folder.children.map(childFolder => renderFolderTree(childFolder))
        )
    );
  };

  return React.createElement('div', { className: 'flex h-screen bg-gray-100' },
    React.createElement('div', { className: 'w-1/4 bg-white p-4 overflow-y-auto' },
      React.createElement('h2', { className: 'text-xl font-bold mb-4' }, 'Folders'),
      React.createElement('button', {
        onClick: () => setIsModalOpen(true),
        className: 'mb-4 bg-blue-500 text-white p-2 rounded hover:bg-blue-600'
      }, '+ New Folder'),
      error && React.createElement('p', { className: 'text-red-500 mb-4' }, error),
      folders.length > 0 ? folders.map(renderFolderTree) :
        React.createElement('p', null, 'No folders found')
    ),
    React.createElement('div', { className: 'w-3/4 p-4 overflow-y-auto' },
      React.createElement('h2', { className: 'text-2xl font-bold mb-4' },
        selectedFolder ? selectedFolder.name : 'All Favorites'
      ),
      React.createElement('div', { className: 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' },
        favorites.map(favorite => 
          React.createElement('div', { key: favorite.id, className: 'bg-white rounded-lg shadow-md p-4' },
            React.createElement('a', {
              href: favorite.url,
              target: '_blank',
              rel: 'noopener noreferrer',
              className: 'text-lg font-semibold text-blue-600 hover:underline mb-1 block'
            }, favorite.title),
            React.createElement('p', { className: 'text-xs text-gray-500 mb-2' },
              getFolderPath(favorite.folder_id)
            ),
            React.createElement('div', { className: 'text-gray-600 mb-2' },
              expandedDescriptions[favorite.id] 
                ? favorite.summary
                : truncateText(favorite.summary, 100),
              React.createElement('button', {
                onClick: () => toggleDescription(favorite.id),
                className: 'text-blue-500 hover:underline ml-2'
              }, expandedDescriptions[favorite.id] ? 'Read less' : 'Read more')
            ),
            React.createElement('div', { className: 'flex flex-wrap' },
              (favorite.tags || []).map(tag => 
                React.createElement('span', {
                  key: tag.id,
                  className: 'bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-sm mr-2 mb-2'
                }, tag.name)
              )
            )
          )
        )
      )
    ),
    React.createElement(Modal, {
      isOpen: isModalOpen,
      onClose: () => setIsModalOpen(false),
      onSubmit: createFolder,
      title: 'Create New Folder'
    },
      React.createElement('input', {
        type: 'text',
        value: newFolderName,
        onChange: (e) => setNewFolderName(e.target.value),
        placeholder: 'Folder Name',
        className: 'w-full p-2 mb-4 border rounded'
      }),
      React.createElement('textarea', {
        value: newFolderDescription,
        onChange: (e) => setNewFolderDescription(e.target.value),
        placeholder: 'Folder Description (optional)',
        className: 'w-full p-2 mb-4 border rounded'
      })
    )
  );
};

ReactDOM.render(React.createElement(MainPage), document.getElementById('root'));