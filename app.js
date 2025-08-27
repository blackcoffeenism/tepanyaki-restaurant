function confirmDelete(e){
  if(!confirm('Delete this menu item?')){ e.preventDefault(); return false; }
  return true;
}

const toast = document.getElementById('toast');
if (toast){ setTimeout(()=> toast.remove(), 2500); }
