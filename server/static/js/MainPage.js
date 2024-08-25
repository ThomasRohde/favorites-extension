const { useState, useEffect } = React;

const MainPage = () => {
  const [folders, setFolders] = useState([]);
  const [expandedFolders, setExpandedFolders] = useState({});
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [favorites, setFavorites] = useState([]);
  const [error, setError] = useState(null);
  const [expandedDescriptions, setExpandedDescriptions] = useState({});

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

  const renderFolderTree = (folder) => {
    if (!folder || folder.id == null) return null;
    const isExpanded = expandedFolders[folder.id];
    const hasChildren = folder.children && folder.children.length > 0;

    return React.createElement('div', { key: folder.id, className: 'ml-4' },
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
        React.createElement('span', null, folder.name)
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
      error ? React.createElement('p', { className: 'text-red-500' }, error) : 
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
              className: 'text-lg font-semibold text-blue-600 hover:underline mb-2 block'
            }, favorite.title),
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
    )
  );
};

ReactDOM.render(React.createElement(MainPage), document.getElementById('root'));