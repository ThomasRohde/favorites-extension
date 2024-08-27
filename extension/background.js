// Function to set the appropriate icon based on the current theme
function setIconForTheme(isDarkTheme) {
  const iconPath = isDarkTheme ? {
    24: "icons8-favorite-dark-24.png",
    48: "icons8-favorite-dark-48.png",
    96: "icons8-favorite-dark-96.png"
  } : {
    24: "icons8-favorite-light-24.png",
    48: "icons8-favorite-light-48.png",
    96: "icons8-favorite-light-96.png"
  };

  chrome.action.setIcon({ path: iconPath });
}

// Function to check if the current theme is dark
function isDarkTheme(theme) {
  return theme && theme.colors && theme.colors.toolbar &&
    theme.colors.toolbar.startsWith('rgb(') &&
    parseInt(theme.colors.toolbar.split(',')[0].split('(')[1]) < 128;
}

// Listen for theme updates
chrome.theme.onUpdated.addListener((updateInfo) => {
  if (updateInfo.theme) {
    setIconForTheme(isDarkTheme(updateInfo.theme));
  }
});

// Set the initial icon when the extension is installed or updated
chrome.runtime.onInstalled.addListener(() => {
  chrome.theme.getCurrent((theme) => {
    setIconForTheme(isDarkTheme(theme));
  });
  console.log('Intelligent Favorites extension installed or updated.');
});

// Check and set the icon when a new browser window is created
chrome.windows.onCreated.addListener(() => {
  chrome.theme.getCurrent((theme) => {
    setIconForTheme(isDarkTheme(theme));
  });
});

// Listen for messages from the popup or content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getCurrentTabInfo") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        sendResponse({ url: tabs[0].url, title: tabs[0].title });
      } else {
        sendResponse({ error: "No active tab found" });
      }
    });
    return true; // Indicates that the response is sent asynchronously
  }
});

console.log('Intelligent Favorites extension background script running.');