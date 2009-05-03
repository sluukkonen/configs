;; Saku's Emacs settings

;; Vendor directory for custom .el files.
(add-to-list 'load-path (concat dotfiles-dir "vendor"))

;; For describe-unbound-keys
(require 'unbound)

;; paredit-mode
(autoload 'paredit-mode "paredit"
  "Minor mode to enter various characters in pairs."
  t)

;; Snippets.
(require 'yasnippet) 
(yas/initialize)
(yas/load-directory "~/.emacs.d/vendor/snippets")

;; Per-filetype compiler settings.
(autoload 'mode-compile "mode-compile"
   "Command to compile current buffer file based on the major mode" t)
(global-set-key "\C-cc" 'mode-compile)
(autoload 'mode-compile-kill "mode-compile"
 "Command to kill a compilation launched by `mode-compile'" t)
(global-set-key "\C-ck" 'mode-compile-kill)

;; Color themes
;; (require 'color-theme)
;; (color-theme-initialize)
;; (color-theme-twilight)

;; A full screen command
(defun toggle-fullscreen ()
  (interactive)
  (set-frame-parameter nil 'fullscreen (if (frame-parameter nil 'fullscreen)
                                           nil
                                         'fullboth)))
(global-set-key (kbd "M-n") 'toggle-fullscreen)

;; Indent comments.
(setq comment-style 'indent)

;; Default tab width.
(setq default-tab-width 4)

;; Use spaces instead of tabs.
(setq-default indent-tabs-mode nil)

;; Textmate-like newline from M-RET.
(defun textmate-next-line ()
  (interactive)
  (end-of-line)
  (newline-and-indent))
(global-set-key (kbd "M-RET") 'textmate-next-line)

;; Line width.
(setq-default fill-column 80 )

;; Display column/line numbers in the status line.
(setq column-number-mode t)

;; Disable scrollbars
(toggle-scroll-bar -1)

;; Invoke M-x without alt
(global-set-key "\C-x\C-m" 'execute-extended-command)
(global-set-key "\C-c\C-m" 'execute-extended-command)

;; C-mode settings
(setq c-default-style "bsd"
      c-basic-offset 4)
(add-hook 'c-mode-common-hook
          (lambda ()
            (c-toggle-auto-hungry-state 1)
            (paredit-mode +1)))

;; Ruby electric keys fix until emacs starter kit fixes it.
(add-hook 'ruby-mode-hook
          (lambda()
            (add-hook 'local-write-file-hooks
                      '(lambda()
                         (save-excursion
                           (untabify (point-min) (point-max))
                           (delete-trailing-whitespace)
                           )))
            (set (make-local-variable 'indent-tabs-mode) 'nil)
            (set (make-local-variable 'tab-width) 2)
            ;; (imenu-add-to-menubar "IMENU")
            (require 'ruby-electric)
            (ruby-electric-mode t)
            ))

;; Map backwards-delete-char to C-h and remap help to M-?.
(global-set-key "\C-h" 'delete-backward-char)
(global-set-key "\M-?" 'help-command)

;; Some mac-specific hacks.
(setq mac-pass-command-to-system nil)   ; Disable cmd-h in carbon emacs.
(setq mac-pass-control-to-system nil)   ; Disable control keybindings for OS X.

;; Replace dabbrev-expand with hippie-expand.
(global-set-key (kbd "M-/") 'hippie-expand)
(setq hippie-expand-try-functions-list '(try-expand-dabbrev try-expand-dabbrev-all-buffers try-expand-dabbrev-from-kill try-complete-file-name-partially try-complete-file-name try-expand-all-abbrevs try-expand-list try-expand-line try-complete-lisp-symbol-partially try-complete-lisp-symbol))

;; Marking a single line.
(require 'mark-lines)
(global-set-key [(control x) (control p)] 'mark-lines-previous-line)
(global-set-key [(control x) (control n)] 'mark-lines-next-line)

;; Latex settings
(add-hook 'LaTeX-mode-hook 'LaTeX-math-mode)

;; Join two lines
(global-set-key (kbd "C-M-j") 'join-line)
