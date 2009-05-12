;;; textmate-mode settings
(add-hook 'c-mode-common-hook (lambda () (textmate-mode)))
(add-hook 'emacs-lisp-mode-hook (lambda () (paredit-mode +1)))
