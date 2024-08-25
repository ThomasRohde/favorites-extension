document.addEventListener('DOMContentLoaded', function() {
  const titleInput = document.getElementById('titleInput');
  const addButton = document.getElementById('addButton');
  const adminButton = document.getElementById('adminButton');
  const messageDiv = document.getElementById('message');

  // Get the current tab's title and URL
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    const currentTab = tabs[0];
    titleInput.value = currentTab.title;
  });

  addButton.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      const currentTab = tabs[0];
      const favoriteData = {
        url: currentTab.url,
        title: titleInput.value
      };

      fetch('http://localhost:8000/api/favorites/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(favoriteData)
      })
      .then(response => response.json())
      .then(data => {
        messageDiv.textContent = 'Favorite added successfully!';
        messageDiv.style.color = 'green';
      })
      .catch(error => {
        messageDiv.textContent = 'Error adding favorite.';
        messageDiv.style.color = 'red';
        console.error('Error:', error);
      });
    });
  });

  adminButton.addEventListener('click', function() {
    chrome.tabs.create({url: 'http://localhost:8000/admin'});
  });
});
