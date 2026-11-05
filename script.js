// Меню на телефоне: показываем ссылки и сообщаем состояние кнопки.
document.body.classList.add('js-ready');
const menuToggle = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');
function closeMenu() {
  navigation.classList.remove('is-open');
  menuToggle.setAttribute('aria-expanded', 'false');
  menuToggle.textContent = 'Меню ☰';
}
menuToggle.addEventListener('click', () => {
  const isOpen = navigation.classList.toggle('is-open');
  menuToggle.setAttribute('aria-expanded', String(isOpen));
  menuToggle.textContent = isOpen ? 'Закрыть ×' : 'Меню ☰';
});
navigation.addEventListener('click', (event) => {
  if (event.target.closest('a')) closeMenu();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && navigation.classList.contains('is-open')) {
    closeMenu();
    menuToggle.focus();
  }
});
// Фильтр показывает позиции выбранной категории без перезагрузки страницы.
const filterButtons = document.querySelectorAll('[data-filter]');

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const category = button.dataset.filter;
    filterButtons.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    let visibleCount = 0;
    document.querySelectorAll('[data-category]').forEach((card) => {
      card.hidden = category !== 'all' && card.dataset.category !== category;
      if (!card.hidden) visibleCount += 1;
    });
    document.querySelector('#menu-status').textContent = `Показано позиций: ${visibleCount}`;
  });
});

// Демонстрационные контакты не открывают чужие номера и вымышленные маршруты.
const contactDialog = document.querySelector('#contact-dialog');
const contactMessages = {
  route: 'Для маршрута нужен настоящий адрес кофейни. После его добавления эта кнопка откроет карту с направлением к заведению.',
  phone: 'Для звонка нужен настоящий номер кофейни. После его добавления эта кнопка откроет приложение телефона.',
  social: 'Для перехода нужна ссылка на официальную страницу кофейни. После её добавления здесь откроется соцсеть.'
};
document.querySelectorAll('[data-contact-demo]').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelector('#contact-dialog-text').textContent = contactMessages[button.dataset.contactDemo];
    contactDialog.showModal();
  });
});
// Работает и после изменения сезонных позиций в админке.
document.addEventListener('click', event => {
  const link = event.target.closest('.season-banner a');
  if (link) document.querySelector('[data-filter="all"]').click();
});
