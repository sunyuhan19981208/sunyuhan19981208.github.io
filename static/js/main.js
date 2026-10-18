(() => {
  'use strict';
  const root = document.documentElement;
  const toggle = document.querySelector('.theme-toggle');
  toggle?.addEventListener('click', () => {
    const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = theme;
    toggle.setAttribute('aria-pressed', String(theme === 'dark'));
    try { localStorage.setItem('ylog-theme', theme); } catch (_) {}
  });
  toggle?.setAttribute('aria-pressed', String(root.dataset.theme === 'dark'));
  matchMedia('(prefers-color-scheme:dark)').addEventListener('change', event => {
    try { if (localStorage.getItem('ylog-theme')) return; } catch (_) {}
    root.dataset.theme = event.matches ? 'dark' : 'light';
    toggle?.setAttribute('aria-pressed', String(event.matches));
  });

  document.querySelectorAll('[data-filter]').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-filter]').forEach(other => {
        const active = other === button;
        other.classList.toggle('active', active);
        other.setAttribute('aria-pressed', String(active));
      });
      document.querySelectorAll('.post-card[data-kind]').forEach(card => {
        card.hidden = button.dataset.filter !== 'all' && card.dataset.kind !== button.dataset.filter;
      });
    });
  });

  const body = document.querySelector('.article-body');
  const toc = document.querySelector('#article-toc');
  if (body && toc) {
    const headings = [...body.querySelectorAll('h2, h3')].filter(h => h.textContent.trim());
    const usedIds = new Set([...document.querySelectorAll('[id]')].map(e => e.id));
    let group;
    headings.forEach((heading, index) => {
      if (!heading.id) {
        let id = `section-${index + 1}`;
        while (usedIds.has(id)) id += '-';
        heading.id = id;
        usedIds.add(id);
      }
      const a = document.createElement('a');
      a.href = `#${encodeURIComponent(heading.id)}`;
      a.textContent = heading.textContent.replace(/\s+/g, ' ').trim();
      if (heading.tagName === 'H3') a.className = 'sub';
      if (heading.tagName === 'H2' || !group) {
        group = document.createElement('div');
        group.className = 'toc-section';
        toc.append(group);
      }
      group.append(a);
    });
    const citationLink = document.createElement('a');
    citationLink.href = '#cite';
    citationLink.textContent = document.documentElement.lang === 'en' ? 'Source' : '原文';
    toc.append(citationLink);
    if (matchMedia('(max-width:900px)').matches) toc.closest('details').open = false;
    const links = [...toc.querySelectorAll('a')];
    let currentHeading;
    let tocFrame;
    const updateToc = () => {
      tocFrame = null;
      let current = headings[0];
      for (const heading of headings) {
        if (heading.getBoundingClientRect().top > 160) break;
        current = heading;
      }
      if (!current || current === currentHeading) return;
      currentHeading = current;
      links.forEach(link => link.classList.toggle('current', decodeURIComponent(link.hash.slice(1)) === current.id));
      toc.querySelectorAll('.toc-section').forEach(section => section.classList.toggle('expanded', !!section.querySelector('a.current')));
    };
    const scheduleToc = () => { if (!tocFrame) tocFrame = requestAnimationFrame(updateToc); };
    addEventListener('scroll', scheduleToc, { passive: true });
    addEventListener('resize', scheduleToc);
    addEventListener('load', scheduleToc);
    scheduleToc();
    body.querySelectorAll('p').forEach(paragraph => {
      if (paragraph.children.length === 0 && /^图\s*\d+/.test(paragraph.textContent.trim()) && paragraph.textContent.length < 180) paragraph.classList.add('figure-caption');
    });
    body.querySelectorAll('table').forEach(table => {
      if (table.closest('.table-scroll, .equation-scroll')) return;
      const wrapper = document.createElement('div');
      const equation = table.classList.contains('ltx_eqn_table');
      wrapper.className = equation ? 'equation-scroll' : 'table-scroll';
      wrapper.tabIndex = 0;
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', document.documentElement.lang === 'en' ? 'Scrollable data table' : '可横向滚动的数据表格');
      table.before(wrapper); wrapper.append(table);
    });
  }

  const formulas = body?.querySelectorAll('.equation-formula');
  if (formulas?.length) {
    const measure = formula => formula.classList.toggle('has-overflow', formula.scrollWidth > formula.clientWidth + 2);
    const formulaObserver = new ResizeObserver(entries => entries.forEach(entry => measure(entry.target)));
    formulas.forEach(formula => { measure(formula); formulaObserver.observe(formula); });
  }

  const dialog = document.querySelector('.image-dialog');
  if (dialog && body) {
    body.querySelectorAll('img:not(.inline-equation):not(.figure-key-icon)').forEach(img => {
      if (img.closest('.publication-affiliations')) return;
      img.tabIndex = 0;
      img.setAttribute('role', 'button');
      img.setAttribute('aria-label', (document.documentElement.lang === 'en' ? 'Enlarge: ' : '放大查看：') + img.alt);
      const open = () => {
        dialog.querySelector('img').src = img.currentSrc || img.src;
        dialog.querySelector('img').alt = img.alt;
        dialog.querySelector('p').textContent = img.alt;
        dialog.showModal();
      };
      img.addEventListener('click', open);
      img.closest('.publication-figure')?.querySelector('.figure-expand')?.addEventListener('click', open);
      img.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
    });
    dialog.querySelector('button').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  }
  document.querySelector('.copy-citation')?.addEventListener('click', async e => {
    const button = e.currentTarget;
    try {
      await navigator.clipboard.writeText(document.querySelector('#bibtex').textContent);
      button.textContent = 'Copied ✓';
      setTimeout(() => { button.textContent = 'Copy BibTeX'; }, 1800);
    } catch (_) { button.textContent = 'Select and copy below'; }
  });
  const back = document.querySelector('.back-top');
  const updateBack = () => back?.classList.toggle('visible', scrollY > 500);
  addEventListener('scroll', updateBack, { passive: true }); updateBack();

  const search = document.querySelector('#search-input');
  if (search) {
    const status = document.querySelector('.search-status');
    const results = document.querySelector('#search-results');
    let entries;
    let failed = false;
    const loading = fetch(document.querySelector('[data-search-index]').dataset.searchIndex)
      .then(response => { if (!response.ok) throw Error('Search index unavailable'); return response.json(); })
      .then(data => { entries = data; })
      .catch(() => { failed = true; status.textContent = '搜索索引加载失败，请刷新页面重试，或通过归档浏览文章。'; });
    const text = (tag, value, className) => {
      const el = document.createElement(tag); el.textContent = value;
      if (className) el.className = className;
      return el;
    };
    const highlight = (target, value, terms) => {
      const escaped = terms.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
      const expression = new RegExp(`(${escaped.join('|')})`, 'gi');
      let last = 0;
      for (const match of value.matchAll(expression)) {
        target.append(document.createTextNode(value.slice(last, match.index)), text('mark', match[0]));
        last = match.index + match[0].length;
      }
      target.append(document.createTextNode(value.slice(last)));
    };
    let revision = 0;
    const run = async () => {
      const current = ++revision;
      const query = search.value.trim();
      const url = new URL(location.href);
      if (query) url.searchParams.set('q', query); else url.searchParams.delete('q');
      history.replaceState(null, '', url);
      results.replaceChildren();
      if (!query) { status.textContent = '输入关键词开始搜索 · 支持中文与英文'; return; }
      status.textContent = '正在搜索…';
      await loading;
      if (current !== revision) return;
      if (failed) { status.textContent = '搜索索引加载失败，请刷新页面重试，或通过归档浏览文章。'; return; }
      const terms = query.toLocaleLowerCase().split(/\s+/).filter(Boolean).slice(0, 10);
      const preferredLanguage = /[\u3400-\u9fff]/.test(query) ? 'zh-CN' : 'en';
      const ranked = entries.map(entry => {
        const title = entry.title.toLocaleLowerCase(), description = entry.description.toLocaleLowerCase();
        const haystack = `${title} ${description} ${entry.tags.join(' ')} ${entry.content}`.toLocaleLowerCase();
        const found = terms.every(term => haystack.includes(term));
        const score = terms.reduce((sum, term) => sum + (title.includes(term) ? 10 : description.includes(term) ? 5 : 1), 0);
        return { entry, found, score };
      }).filter(item => item.found).sort((a,b) => b.score-a.score || Number(b.entry.language === preferredLanguage)-Number(a.entry.language === preferredLanguage) || b.entry.date.localeCompare(a.entry.date));
      const seenWorks = new Set();
      const matches = ranked.filter(({entry}) => {
        const key = entry.workId || entry.url;
        if (seenWorks.has(key)) return false;
        seenWorks.add(key); return true;
      });
      status.textContent = matches.length ? `找到 ${matches.length} 篇相关文章` : `没有找到与“${query}”相关的文章，试试其他关键词。`;
      matches.forEach(({ entry }) => {
        const article = text('article', '', 'search-result');
        const title = document.createElement('h2'), link = document.createElement('a');
        link.href = entry.url; highlight(link, entry.title, terms); title.append(link);
        const snippet = text('p', '');
        let value = entry.description;
        if (!terms.some(term => value.toLocaleLowerCase().includes(term))) {
          const index = entry.content.toLocaleLowerCase().indexOf(terms[0]);
          if (index >= 0) value = (index > 70 ? '…' : '') + entry.content.slice(Math.max(0,index-70),index+160) + '…';
        }
        highlight(snippet, value, terms);
        const languages = document.createElement('nav');
        languages.className = 'version-switch'; languages.setAttribute('aria-label','文章语言 / Article language');
        ['zh-CN','en'].forEach((language,index) => {
          const version = entries.find(other => other.workId === entry.workId && other.language === language);
          if (!version) return;
          if (index) languages.append(text('span','/'));
          const languageLink = text('a', language === 'en' ? 'English' : '中文');
          languageLink.href = version.url; languageLink.lang = language; languageLink.hreflang = language;
          languages.append(languageLink);
        });
        article.append(text('time', entry.date), title, snippet, languages); results.append(article);
      });
    };
    let timeout;
    search.addEventListener('input', () => { clearTimeout(timeout); timeout = setTimeout(run, 100); });
    search.value = new URLSearchParams(location.search).get('q') || '';
    if (search.value) run();
    addEventListener('keydown', e => { if (e.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) { e.preventDefault(); search.focus(); } });
  }
})();
