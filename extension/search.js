document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('searchButton').addEventListener('click', performSearch);
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
});

function performSearch() {
    const query = document.getElementById('searchInput').value;
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = 'Searching...';

    fetch(`http://localhost:8000/api/favorites/search/vector?query=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            resultsDiv.innerHTML = '';
            if (data.length === 0) {
                resultsDiv.innerHTML = 'No results found.';
            } else {
                data.forEach(favorite => {
                    const favoriteElement = document.createElement('div');
                    favoriteElement.className = 'favorite-item';
                    favoriteElement.innerHTML = `
                        <h2><a href="${favorite.url}" target="_blank">${favorite.title}</a></h2>
                        <p>${favorite.summary}</p>
                    `;
                    resultsDiv.appendChild(favoriteElement);
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.innerHTML = 'An error occurred while searching.';
        });
}