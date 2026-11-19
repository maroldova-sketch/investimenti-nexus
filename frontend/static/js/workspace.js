(() => {
  'use strict';
  const sidebar = document.getElementById('nx-sidebar');
  const menuButton = document.querySelector('[data-nx-menu]');
  const search = document.getElementById('nx-nav-search');
  const groups = Array.from(document.querySelectorAll('[data-nav-group]'));
  const noResult = document.getElementById('nx-search-empty');
  const guide = document.getElementById('nx-guide-steps');
  const guideButton = document.querySelector('[data-nx-guide]');
  if (!sidebar || !search) return;

  let beforeSearch = null;
  const normalized = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('cs').trim();
  const openMenu = open => {
    sidebar.classList.toggle('is-open', open);
    if (menuButton) {
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Zavřít hlavní menu' : 'Otevřít hlavní menu');
    }
  };
  const filterMenu = () => {
    const query = normalized(search.value);
    if (query && beforeSearch === null) beforeSearch = groups.map(group => group.open);
    let matches = 0;
    groups.forEach((group, index) => {
      const links = Array.from(group.querySelectorAll('[data-nav-item]'));
      let visible = 0;
      links.forEach(item => {
        const match = !query || normalized(item.dataset.navSearch).includes(query);
        item.hidden = !match;
        if (match) { visible++; matches++; }
      });
      group.hidden = visible === 0;
      if (query) group.open = visible > 0;
      else if (beforeSearch !== null) group.open = beforeSearch[index];
    });
    if (!query) beforeSearch = null;
    if (noResult) noResult.hidden = matches > 0;
  };
  search.addEventListener('input', filterMenu);
  menuButton?.addEventListener('click', () => openMenu(!sidebar.classList.contains('is-open')));
  guideButton?.addEventListener('click', () => {
    if (!guide) return;
    guide.open = !guide.open;
    guide.querySelector('summary')?.focus();
  });
  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      openMenu(true);
      search.focus();
      search.select();
    }
    if (event.key === 'Escape' && sidebar.contains(document.activeElement)) {
      if (search.value) { search.value = ''; filterMenu(); search.focus(); }
      else { openMenu(false); menuButton?.focus(); }
    }
  });
})();
