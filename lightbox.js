(function () {
  const images = Array.from(document.querySelectorAll('.image-grid img'));
  if (!images.length) return;

  let current = 0;

  const lb = document.createElement('div');
  lb.id = 'lightbox';
  lb.innerHTML = [
    '<button class="lb-close" aria-label="Close">&times;</button>',
    '<button class="lb-prev" aria-label="Previous">&#8249;</button>',
    '<button class="lb-next" aria-label="Next">&#8250;</button>',
    '<div class="lb-inner">',
    '  <img class="lb-img" src="" alt="">',
    '  <p class="lb-caption"></p>',
    '</div>'
  ].join('');
  document.body.appendChild(lb);

  const lbImg = lb.querySelector('.lb-img');
  const lbCaption = lb.querySelector('.lb-caption');

  function open(index) {
    current = index;
    const img = images[current];
    lbImg.src = img.src;
    lbImg.alt = img.alt;
    lbCaption.textContent = img.dataset.caption || img.alt || '';
    lb.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    lb.classList.remove('active');
    document.body.style.overflow = '';
    lbImg.src = '';
  }

  function prev() { open((current - 1 + images.length) % images.length); }
  function next() { open((current + 1) % images.length); }

  images.forEach(function (img, i) {
    img.style.cursor = 'pointer';
    img.addEventListener('click', function () { open(i); });
  });

  lb.querySelector('.lb-close').addEventListener('click', close);
  lb.querySelector('.lb-prev').addEventListener('click', prev);
  lb.querySelector('.lb-next').addEventListener('click', next);

  lb.addEventListener('click', function (e) { if (e.target === lb) close(); });

  document.addEventListener('keydown', function (e) {
    if (!lb.classList.contains('active')) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowLeft') prev();
    if (e.key === 'ArrowRight') next();
  });
})();
