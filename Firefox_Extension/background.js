browser.runtime.onMessage.addListener((request, sender) => {
  const baseUrl = request.serverUrl || 'http://127.0.0.1:7777';

  function makeRequest(endpoint, method, body) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open(method, `${baseUrl}${endpoint}`, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const data = JSON.parse(xhr.responseText);
              resolve({ message: data.message || JSON.stringify(data) });
            } catch (error) {
              resolve({ message: xhr.responseText });
            }
          } else {
            reject({ message: `Error: ${xhr.status} ${xhr.statusText}` });
          }
        }
      };
      xhr.onerror = function () {
        reject({ message: 'Network error occurred' });
      };
      if (method !== 'GET' && body !== null) {
        xhr.send(JSON.stringify(body));
      } else {
        xhr.send();
      }
    });
  }

  switch (request.action) {
    case 'addUrlFull':
      return makeRequest('/v1/url/full', 'POST', { url: request.url, tts_engine: request.ttsEngine });
    case 'addUrlSummary':
      return makeRequest('/v1/url/summary', 'POST', { url: request.url, tts_engine: request.ttsEngine });
    case 'addTextFull':
      return makeRequest('/v1/text/full', 'POST', { text: request.text, tts_engine: request.ttsEngine });
    case 'addTextSummary':
      return makeRequest('/v1/text/summary', 'POST', { text: request.text, tts_engine: request.ttsEngine });
    case 'fetchSources':
      return makeRequest('/v1/sources/fetch', 'POST', {});
    case 'getSources':
      return makeRequest('/v1/sources/get', 'GET', null);
    case 'addSource':
      return makeRequest('/v1/sources/add', 'POST', {
        sources: [request.sourceData]
      });
    default:
      return Promise.resolve({ message: 'Unknown action' });
  }
});