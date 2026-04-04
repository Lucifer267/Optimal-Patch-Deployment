(function () {
  const key = 'patch-sentinel-theme';
  const root = document.documentElement;
  const button = document.getElementById('themeToggle');

  function applyTheme(theme) {
    if (theme === 'light') {
      root.setAttribute('data-theme', 'light');
      document.body.style.background = 'linear-gradient(180deg, #eef4ff, #dfe9f8)';
    } else {
      root.setAttribute('data-theme', 'dark');
      document.body.style.background = '';
    }
  }

  const stored = localStorage.getItem(key) || 'dark';
  applyTheme(stored);

  document.querySelectorAll('a[href]').forEach((link) => {
    link.addEventListener('click', () => {
      document.body.classList.add('page-transition');
    });
  });

  if (button) {
    button.addEventListener('click', function () {
      const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      localStorage.setItem(key, next);
      applyTheme(next);
    });
  }

  const fileInput = document.querySelector('input[type="file"]');
  if (fileInput) {
    fileInput.addEventListener('change', function () {
      const fileName = this.files && this.files[0] ? this.files[0].name : 'No file selected';
      this.closest('label')?.setAttribute('data-file', fileName);
    });
  }
})();
