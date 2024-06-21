chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === 'addUrl') {
      fetch('http://localhost:7777/v1/url/full', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({url: request.url, tts_engine: 'edge'}),
      })
      .then(response => response.json())
      .then(data => {
        sendResponse({message: 'URL added successfully'});
      })
      .catch(error => {
        sendResponse({message: 'Error adding URL: ' + error});
      });
      return true;  // Indicates that the response is sent asynchronously
    } else if (request.action === 'fetchSources') {
      fetch('http://localhost:7777/v1/sources/fetch', {
        method: 'POST',
      })
      .then(response => response.json())
      .then(data => {
        sendResponse({message: 'Sources fetched successfully'});
      })
      .catch(error => {
        sendResponse({message: 'Error fetching sources: ' + error});
      });
      return true;  // Indicates that the response is sent asynchronously
    }
  });