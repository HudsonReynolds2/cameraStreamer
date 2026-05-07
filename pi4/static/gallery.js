/* gallery.js — Pi Camera v2 capture gallery */

'use strict';

function deleteImage(filename) {
    if (!confirm('Delete ' + filename + '?')) return;

    fetch('/captures/' + filename, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const card = document.getElementById('card-' + filename);
            if (card) card.remove();

            // Show empty message if no cards left
            if (!document.querySelector('.card')) {
                const grid = document.querySelector('.grid');
                if (grid) {
                    grid.outerHTML = '<div class="empty">No captures yet. Go take some photos!</div>';
                }
                const count = document.querySelector('.count');
                if (count) count.remove();
            } else {
                // Update count
                const remaining = document.querySelectorAll('.card').length;
                const count = document.querySelector('.count');
                if (count) {
                    count.textContent = remaining + ' image' + (remaining !== 1 ? 's' : '');
                }
            }
        } else {
            alert('Delete failed: ' + data.error);
        }
    })
    .catch(() => alert('Delete request failed'));
}
