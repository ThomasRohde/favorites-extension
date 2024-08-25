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

  chrome.browserAction.setIcon({ path: iconPath });
}

// Function to check if the current theme is dark
function isDarkTheme(theme) {
  // This is a simple check. You might need to adjust this logic
  // depending on how you want to determine if a theme is "dark"
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

// Your existing initialization code can go here
console.log('Intelligent Favorites extension background script running.');