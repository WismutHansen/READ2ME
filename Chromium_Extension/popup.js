import ErrorUtils from './errorUtils.js';

document.addEventListener('DOMContentLoaded', function () {
  const actionSelect = document.getElementById('actionSelect');
  const urlSection = document.getElementById('urlSection');
  const textSection = document.getElementById('textSection');
  const sourcesSection = document.getElementById('sourcesSection');
  const resultDiv = document.getElementById('result');
  const urlInput = document.getElementById('urlInput');
  const sourceUrlInput = document.getElementById('sourceUrl');
  const serverDropdown = document.getElementById('serverSelect');

  // Ensure serverDropdown exists before manipulating
  if (serverDropdown) {
    serverDropdown.id = 'serverSelect';
    const settingsLink = document.getElementById('settingsLink');
    if (settingsLink) {
      document.body.insertBefore(serverDropdown, settingsLink);
    }
  }

  // Load servers from storage with error handling
  chrome.storage.sync.get(['servers', 'defaultServer'], function (data) {
    try {
      const servers = data.servers || ['http://127.0.0.1:7777'];
      const defaultServer = data.defaultServer || 'http://127.0.0.1:7777';

      servers.forEach(server => {
        const option = document.createElement('option');
        option.value = server;
        option.textContent = server;
        if (server === defaultServer) {
          option.selected = true;
        }
        serverDropdown?.appendChild(option);
      });
    } catch (error) {
      ErrorUtils.showError('Failed to load server settings', resultDiv);
    }
  });

  // Fetch current tab URL and prefill the inputs with error handling
  chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    try {
      if (tabs[0] && tabs[0].url) {
        urlInput.value = tabs[0].url;
        // Prefill the source URL with the root of the current website
        const url = new URL(tabs[0].url);
        sourceUrlInput.value = `${url.protocol}//${url.hostname}`;
      }
    } catch (error) {
      ErrorUtils.showError('Failed to get current tab URL', resultDiv);
    }
  });

  // Handle section visibility
  actionSelect.addEventListener('change', function () {
    try {
      [urlSection, textSection, sourcesSection].forEach(section => section.classList.add('hidden'));

      switch (this.value) {
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
      adjustPopupHeight();
    } catch (error) {
      ErrorUtils.showError('Failed to switch sections', resultDiv);
    }
  });

  function adjustPopupHeight() {
    document.body.style.height = 'auto';
  }

  function validateUrl(url) {
    try {
      new URL(url);
      return true;
    } catch (e) {
      return false;
    }
  }

  document.getElementById('addUrlButton').addEventListener('click', async function () {
    try {
      if (!urlInput) {
        ErrorUtils.showError('URL input element not found', resultDiv);
        return;
      }

      const url = urlInput.value.trim();
      if (!url) {
        ErrorUtils.showError('Please enter a URL', resultDiv);
        return;
      }

      if (!validateUrl(url)) {
        ErrorUtils.showError('Please enter a valid URL', resultDiv);
        return;
      }

      const typeSelect = document.getElementById('urlTypeSelect');
      const ttsEngineSelect = document.getElementById('urlTtsEngine');
      const serverUrl = serverDropdown?.value;

      if (!serverUrl) {
        ErrorUtils.showError('No server selected', resultDiv);
        return;
      }

      const type = typeSelect?.value || 'defaultType';
      const ttsEngine = ttsEngineSelect?.value || 'defaultEngine';

      chrome.runtime.sendMessage({
        action: `addUrl${type.charAt(0).toUpperCase() + type.slice(1)}`,
        url: url,
        ttsEngine: ttsEngine,
        serverUrl: serverUrl
      }, function (response) {
        if (response.error) {
          ErrorUtils.showError(response.message, resultDiv);
        } else {
          ErrorUtils.showSuccess(response.message, resultDiv);
        }
      });
    } catch (error) {
      ErrorUtils.showError(ErrorUtils.handleApiError(error), resultDiv);
    }
    adjustPopupHeight();
  });

  document.getElementById('addTextButton').addEventListener('click', function () {
    try {
      const textInput = document.getElementById('textInput');
      const text = textInput?.value.trim();

      if (!text) {
        ErrorUtils.showError('Please enter some text', resultDiv);
        return;
      }

      const type = document.getElementById('textTypeSelect')?.value;
      const ttsEngine = document.getElementById('textTtsEngine')?.value;
      const serverUrl = serverDropdown?.value;

      if (!serverUrl) {
        ErrorUtils.showError('No server selected', resultDiv);
        return;
      }

      chrome.runtime.sendMessage({
        action: `addText${type.charAt(0).toUpperCase() + type.slice(1)}`,
        text: text,
        ttsEngine: ttsEngine,
        serverUrl: serverUrl
      }, function (response) {
        if (response.error) {
          ErrorUtils.showError(response.message, resultDiv);
        } else {
          ErrorUtils.showSuccess(response.message, resultDiv);
        }
      });
    } catch (error) {
      ErrorUtils.showError(ErrorUtils.handleApiError(error), resultDiv);
    }
    adjustPopupHeight();
  });

  document.getElementById('addSourceButton').addEventListener('click', function () {
    try {
      const url = sourceUrlInput.value.trim();
      const keywordsInput = document.getElementById('sourceKeywords')?.value;
      const serverUrl = serverDropdown?.value;

      if (!url || !keywordsInput) {
        ErrorUtils.showError('Please enter both URL and keywords', resultDiv);
        return;
      }

      if (!validateUrl(url)) {
        ErrorUtils.showError('Please enter a valid source URL', resultDiv);
        return;
      }

      const keywords = keywordsInput.split(',').map(k => k.trim()).filter(k => k);
      if (keywords.length === 0) {
        ErrorUtils.showError('Please enter at least one keyword', resultDiv);
        return;
      }

      if (!serverUrl) {
        ErrorUtils.showError('No server selected', resultDiv);
        return;
      }

      chrome.runtime.sendMessage({
        action: 'addSource',
        sourceData: { url, keywords },
        serverUrl: serverUrl
      }, function (response) {
        if (response.error) {
          ErrorUtils.showError(response.message, resultDiv);
        } else {
          ErrorUtils.showSuccess(response.message, resultDiv);
        }
      });
    } catch (error) {
      ErrorUtils.showError(ErrorUtils.handleApiError(error), resultDiv);
    }
    adjustPopupHeight();
  });

  document.getElementById('fetchSourcesButton').addEventListener('click', function () {
    try {
      const serverUrl = serverDropdown?.value;

      if (!serverUrl) {
        ErrorUtils.showError('No server selected', resultDiv);
        return;
      }

      chrome.runtime.sendMessage({
        action: 'fetchSources',
        serverUrl: serverUrl
      }, function (response) {
        if (response.error) {
          ErrorUtils.showError(response.message, resultDiv);
        } else {
          ErrorUtils.showSuccess(response.message, resultDiv);
        }
      });
    } catch (error) {
      ErrorUtils.showError(ErrorUtils.handleApiError(error), resultDiv);
    }
    adjustPopupHeight();
  });

  document.getElementById('getSourcesButton').addEventListener('click', function () {
    try {
      const serverUrl = serverDropdown?.value;

      if (!serverUrl) {
        ErrorUtils.showError('No server selected', resultDiv);
        return;
      }

      chrome.runtime.sendMessage({
        action: 'getSources',
        serverUrl: serverUrl
      }, function (response) {
        try {
          if (response.error) {
            ErrorUtils.showError(response.message, resultDiv);
            return;
          }

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
          ErrorUtils.showSuccess('Sources retrieved successfully', resultDiv);
        } catch (error) {
          ErrorUtils.showError('Error parsing sources: ' + response.message, resultDiv);
        }
      });
    } catch (error) {
      ErrorUtils.showError(ErrorUtils.handleApiError(error), resultDiv);
    }
    adjustPopupHeight();
  });
});
