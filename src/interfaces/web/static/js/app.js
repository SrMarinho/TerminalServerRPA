var _devMode = false;
api('GET', '/api/dev').then(function(d) {
  _devMode = d.dev;
  if (_devMode) initDevTools();
}).catch(function() {});

try { _connectWS(); } catch(e) {}

var _initPanel = 'tasks';
var _initTask = null;
var _initExec = null;
try {
  _initPanel = sessionStorage.getItem(PANEL_KEY) || 'tasks';
  _initTask = sessionStorage.getItem('TerminalServerRPA.task');
  _initExec = sessionStorage.getItem('TerminalServerRPA.exec');
} catch(e) {}

loadCredentials();
if (_initExec) { openExecutionDetail(_initExec); }
else if (_initTask) { openTaskDetail(_initTask); }
else { switchPanel(_initPanel); }
