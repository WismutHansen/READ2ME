document.addEventListener('DOMContentLoaded', function() {
  const serverUrlInput = document.getElementById('serverUrl');
  const addServerButton = document.getElementById('addServerButton');
  const serverList = document.getElementById('serverList');
  const setDefaultButton = document.getElementById('setDefaultButton');
  let selectedServer = null;

  const defaultServer = 'http://127.0.0.1:7777';

  // Initialize default server if none exist and request permissions
  chrome.storage.sync.get(['servers', 'defaultServer'], function(data) {
      let servers = data.servers || [];
      let currentDefaultServer = data.defaultServer || defaultServer;

      if (!servers.includes(defaultServer)) {
          servers.push(defaultServer);
      }

      if (!data.defaultServer) {
          chrome.storage.sync.set({defaultServer: defaultServer});
      }

      chrome.permissions.contains({
          origins: [new URL(defaultServer).origin + "/*"]
      }, function(result) {
          if (!result) {
              requestPermissionForServer(defaultServer, function(granted) {
                  if (granted) {
                      chrome.storage.sync.set({servers: servers}, function() {
                          renderServerList(servers, currentDefaultServer);
                      });
                  } else {
                      alert('Permission denied for the default server.');
                  }
              });
          } else {
              chrome.storage.sync.set({servers: servers}, function() {
                  renderServerList(servers, currentDefaultServer);
              });
          }
      });
  });

  addServerButton.addEventListener('click', function() {
      const newServer = serverUrlInput.value.trim();
      if (newServer) {
          requestPermissionForServer(newServer, function(granted) {
              if (granted) {
                  chrome.storage.sync.get(['servers', 'defaultServer'], function(data) {
                      const servers = data.servers || [];
                      if (!servers.includes(newServer)) {
                          servers.push(newServer);
                          chrome.storage.sync.set({servers: servers}, function() {
                              renderServerList(servers, data.defaultServer);
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

  setDefaultButton.addEventListener('click', function() {
      if (selectedServer) {
          chrome.storage.sync.set({defaultServer: selectedServer}, function() {
              chrome.storage.sync.get(['servers'], function(data) {
                  renderServerList(data.servers, selectedServer);
              });
          });
      }
  });

  function requestPermissionForServer(server, callback) {
      const origin = new URL(server).origin + "/*";
      chrome.permissions.request({
          origins: [origin]
      }, function(granted) {
          callback(granted);
      });
  }

  function renderServerList(servers, defaultServer) {
      serverList.innerHTML = '';
      servers.forEach(server => {
          const li = document.createElement('li');
          li.textContent = server;
          li.addEventListener('click', function() {
              selectedServer = server;
              document.querySelectorAll('#serverList li').forEach(item => item.classList.remove('selected'));
              li.classList.add('selected');
          });
          if (server === defaultServer) {
              li.classList.add('default');
          }
          serverList.appendChild(li);
      });
  }
});
