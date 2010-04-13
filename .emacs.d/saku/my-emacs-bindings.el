;; A filetype agnostic compile command
(global-set-key (kbd "C-c c") 'mode-compile)
(global-set-key (kbd "C-c k") 'mode-compile-kill)

;;; Select whole lines
(global-set-key (kbd "C-x C-p") 'mark-lines-previous-line)
(global-set-key (kbd "C-x C-n") 'mark-lines-next-line)

;; Rectangle selection commands
(global-set-key (kbd "C-x r C-SPC") 'rm-set-mark)
(global-set-key (kbd "C-x r C-x")   'rm-exchange-point-and-mark)
(global-set-key (kbd "C-x r C-w")   'rm-kill-region)
(global-set-key (kbd "C-x r M-w")   'rm-kill-ring-save)

(global-set-key (kbd "C-c F") 'toggle-fullscreen)
(global-set-key (kbd "M-RET") 'textmate-next-line)

;; Flymake shortcuts.
(global-set-key (kbd "M-s") 'flymake-display-err-menu-for-current-line)
(global-set-key (kbd "M-n") 'flymake-goto-next-error)
(global-set-key (kbd "M-p") 'flymake-goto-prev-error)

;; Join the current line with the previous one
(global-set-key (kbd "C-x j") 'join-line)
