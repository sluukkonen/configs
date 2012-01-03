;; Prefer mode-compile.
(global-set-key (kbd "C-c c") 'mode-compile)
(global-set-key (kbd "C-c k") 'mode-compile-kill)

;; Rectangle selection bindings (rect-mark).

(global-set-key (kbd "C-x r C-SPC") 'rm-set-mark)
(global-set-key (kbd "C-x r C-x")   'rm-exchange-point-and-mark)
(global-set-key (kbd "C-x r C-w")   'rm-kill-region)
(global-set-key (kbd "C-x r M-w")   'rm-kill-ring-save)

;; Toggle full screen.
(global-set-key (kbd "C-c F") 'toggle-fullscreen)

;; Textmake-like next line.
(global-set-key (kbd "M-RET") 'textmate-next-line)

;; Flymake shortcuts.
(global-set-key (kbd "M-s") 'flymake-display-err-menu-for-current-line)
(global-set-key (kbd "M-n") 'flymake-goto-next-error)
(global-set-key (kbd "M-p") 'flymake-goto-prev-error)

;; Full-ack shortcut.
(global-set-key (kbd "C-c a") 'ack)
(global-set-key (kbd "C-c A") 'ack-same)
