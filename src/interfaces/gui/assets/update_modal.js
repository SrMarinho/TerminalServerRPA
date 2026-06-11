(function () {
  var e = document.getElementById('_upd_dlg');
  if (e) e.remove();
  window._upd_choice = null;
  document.body.insertAdjacentHTML('beforeend', '__HTML__');
  document.getElementById('_upd_yes').onclick = function () {
    window._upd_choice = 'yes';
    document.getElementById('_upd_dlg').remove();
  };
  document.getElementById('_upd_no').onclick = function () {
    window._upd_choice = 'no';
    document.getElementById('_upd_dlg').remove();
  };
})();
