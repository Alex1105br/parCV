/**
 * Modal de confirmação reutilizável — substitui window.confirm() nativo.
 *
 * Uso:
 *   const ok = await confirmModal('Tem certeza que deseja cancelar?');
 *   if (!ok) return;
 *
 * Com opções:
 *   const ok = await confirmModal({
 *       title: 'Apagar análise',
 *       message: 'Apagar a análise "X"? Essa ação não pode ser desfeita.',
 *       confirmText: 'Apagar',
 *       cancelText: 'Cancelar',
 *       danger: true
 *   });
 */
(function () {
    'use strict';

    var overlayEl = null;
    var activeResolve = null;

    function buildModal() {
        var overlay = document.createElement('div');
        overlay.className = 'confirm-modal-overlay';
        overlay.innerHTML =
            '<div class="confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="confirm-modal-title" aria-describedby="confirm-modal-message">' +
                '<h3 class="confirm-modal__title" id="confirm-modal-title"></h3>' +
                '<p class="confirm-modal__message" id="confirm-modal-message"></p>' +
                '<div class="confirm-modal__actions">' +
                    '<button type="button" class="confirm-modal__btn confirm-modal__btn--cancel"></button>' +
                    '<button type="button" class="confirm-modal__btn confirm-modal__btn--confirm"></button>' +
                '</div>' +
            '</div>';
        document.body.appendChild(overlay);
        return overlay;
    }

    function close(result) {
        if (!overlayEl) return;
        overlayEl.classList.remove('confirm-modal-overlay--visible');
        document.removeEventListener('keydown', onKeydown);
        var resolve = activeResolve;
        activeResolve = null;
        setTimeout(function () {
            if (overlayEl && overlayEl.parentNode) {
                overlayEl.parentNode.removeChild(overlayEl);
            }
            overlayEl = null;
        }, 150);
        if (resolve) resolve(result);
    }

    function onKeydown(e) {
        if (e.key === 'Escape') close(false);
        else if (e.key === 'Enter') close(true);
    }

    /**
     * @param {string|Object} options Mensagem simples ou objeto de opções.
     * @returns {Promise<boolean>} true se confirmado, false se cancelado.
     */
    window.confirmModal = function (options) {
        if (typeof options === 'string') {
            options = { message: options };
        }
        options = options || {};

        var title = options.title || 'Confirmar ação';
        var message = options.message || 'Tem certeza?';
        var confirmText = options.confirmText || 'Confirmar';
        var cancelText = options.cancelText || 'Cancelar';
        var danger = !!options.danger;

        return new Promise(function (resolve) {
            // Fecha qualquer modal anterior ainda aberto
            if (overlayEl) close(false);

            activeResolve = resolve;
            overlayEl = buildModal();

            overlayEl.querySelector('#confirm-modal-title').textContent = title;
            overlayEl.querySelector('#confirm-modal-message').textContent = message;

            var cancelBtn = overlayEl.querySelector('.confirm-modal__btn--cancel');
            var confirmBtn = overlayEl.querySelector('.confirm-modal__btn--confirm');

            cancelBtn.textContent = cancelText;
            confirmBtn.textContent = confirmText;
            confirmBtn.classList.toggle('confirm-modal__btn--danger', danger);

            cancelBtn.addEventListener('click', function () { close(false); });
            confirmBtn.addEventListener('click', function () { close(true); });
            overlayEl.addEventListener('click', function (e) {
                if (e.target === overlayEl) close(false);
            });

            document.addEventListener('keydown', onKeydown);

            // Força reflow para garantir a transição de entrada
            requestAnimationFrame(function () {
                overlayEl.classList.add('confirm-modal-overlay--visible');
                confirmBtn.focus();
            });
        });
    };
})();
