document.addEventListener('DOMContentLoaded', function() {
  const serverUrlInput = document.getElementById('serverUrl');
  const addServerButton = document.getElementById('addServerButton');
  const serverList = document.getElementById('serverList');
  const setDefaultButton = document.getElementById('setDefaultButton');
  let selectedServer = null;

  const defaultServer = 'http://127.0.0.1:7777';

  // Initialize default server if none exist and request permissions
  browser.storage.sync.get(['servers', 'defaultServer'], function(data) {
      let servers = data.servers || [];
      let currentDefaultServer = data.defaultServer || defaultServer;

      if (!servers.includes(defaultServer)) {
          servers.push(defaultServer);
      }

      if (!data.defaultServer) {
          browser.storage.sync.set({defaultServer: defaultServer});
      }

      browser.permissions.contains({
          origins: [new URL(defaultServer).origin + "/*"]
      }, function(result) {
          if (!result) {
              requestPermissionForServer(defaultServer, function(granted) {
                  if (granted) {
                      browser.storage.sync.set({servers: servers}, function() {
                          renderServerList(servers, currentDefaultServer);
                      });
                  } else {
                      alert('Permission denied for the default server.');
                  }
              });
          } else {
              browser.storage.sync.set({servers: servers}, function() {
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
                  browser.storage.sync.get(['servers', 'defaultServer'], function(data) {
                      const servers = data.servers || [];
                      if (!servers.includes(newServer)) {
                          servers.push(newServer);
                          browser.storage.sync.set({servers: servers}, function() {
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
          browser.storage.sync.set({defaultServer: selectedServer}, function() {
              browser.storage.sync.get(['servers'], function(data) {
                  renderServerList(data.servers, selectedServer);
              });
          });
      }
  });

    function requestPermissionForServer(server, callback) {
      const origin = new URL(server).origin + "/*";
      browser.permissions.request({
        origins: [origin]
      }).then(function(granted) {
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
