chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  const baseUrl = 'http://localhost:7777';

  function makeRequest(endpoint, method, body) {
    const options = {
      method: method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (method !== 'GET' && body !== null) {
      options.body = JSON.stringify(body);
    }

    return fetch(`${baseUrl}${endpoint}`, options)
      .then(response => response.json())
      .then(data => {
        sendResponse({message: data.message || JSON.stringify(data)});
      })
      .catch(error => {
        sendResponse({message: `Error: ${error}`});
      });
  }

  switch (request.action) {
    case 'addUrlFull':
      makeRequest('/v1/url/full', 'POST', {url: request.url, tts_engine: request.ttsEngine});
      break;
    case 'addUrlSummary':
      makeRequest('/v1/url/summary', 'POST', {url: request.url, tts_engine: request.ttsEngine});
      break;
    case 'addTextFull':
      makeRequest('/v1/text/full', 'POST', {text: request.text, tts_engine: request.ttsEngine});
      break;
    case 'addTextSummary':
      makeRequest('/v1/text/summary', 'POST', {text: request.text, tts_engine: request.ttsEngine});
      break;
    case 'fetchSources':
      makeRequest('/v1/sources/fetch', 'POST', {});
      break;
    case 'getSources':
      makeRequest('/v1/sources/get', 'GET', null);
      break;
    case 'addSource':
      makeRequest('/v1/sources/add', 'POST', {
        sources: [request.sourceData]
      });
      break;
    default:
      sendResponse({message: 'Unknown action'});
  }
  return true;  // Indicates that the response is sent asynchronously
});