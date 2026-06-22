document.addEventListener('DOMContentLoaded', function() {
    htmx.on('htmx:afterRequest', function(evt) {
        if (evt.detail.successful && evt.detail.target.id === 'modal-content') {
            document.getElementById('modal-overlay').classList.remove('hidden');
        }
    });

    document.getElementById('modal-overlay')?.addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.add('hidden');
        }
    });

    document.addEventListener('htmx:beforeSwap', function(evt) {
        if (evt.detail.xhr.status === 204) {
            evt.detail.shouldSwap = false;
        }
    });
});
