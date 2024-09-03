document.addEventListener('DOMContentLoaded', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        let currentTab = tabs[0];
        document.getElementById('titleInput').value = currentTab.title;
    });
    document.getElementById("searchButton").addEventListener("click", openSearchDialog);
});

function formatMetaInfoForLLM(metaInfo) {
    const relevantFields = [
        "title",
        "description",
        "keywords",
        "og:title",
        "og:description",
        "og:type",
        "og:url",
        "author",
        "publish_date",
        "article:published_time",
        "article:author",
    ];

    let formattedString = "Webpage Metadata:\n";

    for (const field of relevantFields) {
        if (metaInfo[field]) {
            formattedString += `${field}: ${metaInfo[field]}\n`;
        }
    }

    return formattedString.trim();
}

document.getElementById("addButton").addEventListener("click", async () => {
    // This function will be executed in the context of the current tab
    function getMetaDescription() {
        const metaInfo = {};

        // Extract title
        metaInfo.title = document.title;

        // Extract meta tags
        const metaTags = document.getElementsByTagName("meta");
        for (let i = 0; i < metaTags.length; i++) {
            const name = metaTags[i].getAttribute("name");
            const property = metaTags[i].getAttribute("property");
            const content = metaTags[i].getAttribute("content");

            if (name) {
                metaInfo[name.toLowerCase()] = content;
            } else if (property) {
                metaInfo[property.toLowerCase()] = content;
            }
        }

        // Extract Open Graph tags
        const ogTitle = document.querySelector('meta[property="og:title"]');
        const ogDescription = document.querySelector('meta[property="og:description"]');
        const ogImage = document.querySelector('meta[property="og:image"]');

        if (ogTitle) metaInfo["og:title"] = ogTitle.getAttribute("content");
        if (ogDescription) metaInfo["og:description"] = ogDescription.getAttribute("content");
        if (ogImage) metaInfo["og:image"] = ogImage.getAttribute("content");

        return metaInfo;
    }

    // Get the current active tab
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Execute script in the context of the active tab
    chrome.scripting.executeScript(
        {
            target: { tabId: tab.id },
            function: getMetaDescription,
        },
        (results) => {
            // Log the result to the extension's console
            console.log(results[0].result);

            // Format the metaInfo for LLM prompt
            const formattedMetaInfo = formatMetaInfoForLLM(results[0].result);
            console.log("Formatted Meta Info for LLM:");
            console.log(formattedMetaInfo);

            const favoriteData = {
                url: tab.url,
                title: document.getElementById('titleInput').value,
                metadata: formattedMetaInfo,
            };

            const messageDiv = document.getElementById("message");

            fetch("http://localhost:8000/api/favorites/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(favoriteData),
            })
                .then((response) => response.json())
                .then((data) => {
                    messageDiv.textContent = "Favorite added successfully!";
                    messageDiv.style.color = "green";
                })
                .catch((error) => {
                    messageDiv.textContent = "Error adding favorite.";
                    messageDiv.style.color = "red";
                    console.error("Error:", error);
                });
        }
    );
});

function openSearchDialog() {
    chrome.windows.create({
        url: chrome.runtime.getURL("search.html"),
        type: "popup",
        width: 400,
        height: 600
    }, function(window) {
        // Close the main extension popup
        window.chrome.windows.getCurrent(function(currentWindow) {
            chrome.windows.remove(currentWindow.id);
        });
    });
}