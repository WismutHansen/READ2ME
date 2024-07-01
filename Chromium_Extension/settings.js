document.addEventListener('DOMContentLoaded', function() {
    const serverUrlInput = document.getElementById('serverUrl');
    const addServerButton = document.getElementById('addServerButton');
    const serverList = document.getElementById('serverList');
  
    // Initialize default server if none exist
    chrome.storage.sync.get(['servers', 'defaultServer'], function(data) {
      let servers = data.servers || [];
      let defaultServer = data.defaultServer || 'http://localhost:7777';
  
      if (!servers.includes('http://localhost:7777')) {
        servers.push('http://localhost:7777');
      }
  
      if (!data.defaultServer) {
        chrome.storage.sync.set({defaultServer: defaultServer});
      }
  
      chrome.storage.sync.set({servers: servers}, function() {
        renderServerList(servers, defaultServer);
      });
    });
  
    addServerButton.addEventListener('click', function() {
      const newServer = serverUrlInput.value.trim();
      if (newServer) {
        const origin = new URL(newServer).origin + "/*";
        chrome.permissions.request({
          origins: [origin]
        }, function(granted) {
          if (granted) {
            chrome.storage.sync.get(['servers'], function(data) {
              const servers = data.servers || [];
              if (!servers.includes(newServer)) {
                servers.push(newServer);
                chrome.storage.sync.set({servers: servers}, function() {
                  renderServerList(servers, newServer);
                  serverUrlInput.value = '';
                });
              }
            });
          } else {
            alert('Permission denied for the new server.');
          }
        });
      }
    });
  
    function renderServerList(servers, defaultServer) {
      serverList.innerHTML = '';
      servers.forEach(server => {
        const li = document.createElement('li');
        li.textContent = server;
        const setDefaultButton = document.createElement('button');
        setDefaultButton.textContent = 'Set Default';
        setDefaultButton.style.marginLeft = '10px';
        setDefaultButton.addEventListener('click', function() {
          chrome.storage.sync.set({defaultServer: server}, function() {
            renderServerList(servers, server);
          });
        });
        li.appendChild(setDefaultButton);
        if (server === defaultServer) {
          li.style.fontWeight = 'bold';
          li.style.color = 'green';
        }
        serverList.appendChild(li);
      });
    }
  });
  