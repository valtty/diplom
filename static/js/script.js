// Инициализация всех всплывающих подсказок Bootstrap
document.addEventListener('DOMContentLoaded', function() {
    // Активация popover
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Активация tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Автоматическое скрытие уведомлений через 5 секунд
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Функция для выбора времени в форме записи
function selectTimeSlot(element) {
    document.querySelectorAll('.time-slot').forEach(function(slot) {
        slot.classList.remove('selected');
    });
    element.classList.add('selected');
    document.getElementById('id_time').value = element.dataset.time;
}

// Предпросмотр изображения перед загрузкой
function previewImage(input, previewId) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById(previewId).src = e.target.result;
            document.getElementById(previewId).style.display = 'block';
        }
        reader.readAsDataURL(input.files[0]);
    }
}