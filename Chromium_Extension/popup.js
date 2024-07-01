document.addEventListener('DOMContentLoaded', function() {
  const actionSelect = document.getElementById('actionSelect');
  const urlSection = document.getElementById('urlSection');
  const textSection = document.getElementById('textSection');
  const sourcesSection = document.getElementById('sourcesSection');
  const resultDiv = document.getElementById('result');
  const urlInput = document.getElementById('urlInput');
  const sourceUrlInput = document.getElementById('sourceUrl');

  // Fetch current tab URL and prefill the inputs
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    if (tabs[0] && tabs[0].url) {
      urlInput.value = tabs[0].url;
      // Prefill the source URL with the root of the current website
      const url = new URL(tabs[0].url);
      sourceUrlInput.value = `${url.protocol}//${url.hostname}`;
    }
  });

  actionSelect.addEventListener('change', function() {
    [urlSection, textSection, sourcesSection].forEach(section => section.classList.add('hidden'));

    switch(this.value) {
      case 'url':
        urlSection.classList.remove('hidden');
        break;
      case 'text':
        textSection.classList.remove('hidden');
        break;
      case 'sources':
        sourcesSection.classList.remove('hidden');
        break;
    }
  });

  document.getElementById('addUrlButton').addEventListener('click', function() {
    const url = urlInput.value;
    const type = document.getElementById('urlTypeSelect').value;
    const ttsEngine = document.getElementById('urlTtsEngine').value;
    if (url) {
      chrome.runtime.sendMessage({
        action: `addUrl${type.charAt(0).toUpperCase() + type.slice(1)}`,
        url: url,
        ttsEngine: ttsEngine
      }, function(response) {
        resultDiv.textContent = response.message;
      });
    } else {
      resultDiv.textContent = 'Please enter a URL';
    }
  });

  document.getElementById('addTextButton').addEventListener('click', function() {
    const text = document.getElementById('textInput').value;
    const type = document.getElementById('textTypeSelect').value;
    const ttsEngine = document.getElementById('textTtsEngine').value;
    if (text) {
      chrome.runtime.sendMessage({
        action: `addText${type.charAt(0).toUpperCase() + type.slice(1)}`,
        text: text,
        ttsEngine: ttsEngine
      }, function(response) {
        resultDiv.textContent = response.message;
      });
    } else {
      resultDiv.textContent = 'Please enter some text';
    }
  });

  document.getElementById('addSourceButton').addEventListener('click', function() {
    const url = sourceUrlInput.value;
    const keywords = document.getElementById('sourceKeywords').value.split(',').map(k => k.trim());
    if (url && keywords.length > 0) {
      chrome.runtime.sendMessage({
        action: 'addSource',
        sourceData: { url, keywords }
      }, function(response) {
        resultDiv.textContent = response.message;
      });
    } else {
      resultDiv.textContent = 'Please enter a URL and at least one keyword';
    }
  });

  document.getElementById('fetchSourcesButton').addEventListener('click', function() {
    chrome.runtime.sendMessage({action: 'fetchSources'}, function(response) {
      resultDiv.textContent = response.message;
    });
  });


  document.getElementById('getSourcesButton').addEventListener('click', function() {
    chrome.runtime.sendMessage({action: 'getSources'}, function(response) {
      try {
        const data = JSON.parse(response.message);
        let displayText = "Global Keywords: " + (data.global_keywords ? data.global_keywords.join(", ") : "None") + "\n\nSources:\n";
        if (data.sources && data.sources.length > 0) {
          data.sources.forEach(source => {
            displayText += `URL: ${source.url}\nKeywords: ${source.keywords.join(", ")}\n\n`;
          });
        } else {
          displayText += "No sources found.";
        }
        resultDiv.textContent = displayText;
      } catch (error) {
        resultDiv.textContent = "Error parsing sources: " + response.message;
      }
    });
  });
});