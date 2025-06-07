const boton = document.getElementById('boton_menu');
const menu = document.getElementById('menu');
const contenido = document.querySelector('.contenido');

boton.addEventListener('click', () => {
    menu.classList.toggle('collapsed');
    menu.classList.toggle('expanded');
    contenido.classList.toggle('mover-contenido');
});





