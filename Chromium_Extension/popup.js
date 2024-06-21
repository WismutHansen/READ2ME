document.addEventListener('DOMContentLoaded', function() {
    const addUrlButton = document.getElementById('addUrlButton');
    const fetchSourcesButton = document.getElementById('fetchSourcesButton');
    const urlInput = document.getElementById('urlInput');
    const resultDiv = document.getElementById('result');
  
    addUrlButton.addEventListener('click', function() {
      const url = urlInput.value;
      if (url) {
        chrome.runtime.sendMessage({action: 'addUrl', url: url}, function(response) {
          resultDiv.textContent = response.message;
        });
      } else {
        resultDiv.textContent = 'Please enter a URL';
      }
    });
  
    fetchSourcesButton.addEventListener('click', function() {
      chrome.runtime.sendMessage({action: 'fetchSources'}, function(response) {
        resultDiv.textContent = response.message;
      });
    });
  });