;; Saku's Emacs settings

;; Vendor directory for custom .el files.
(add-to-list 'load-path (concat dotfiles-dir "vendor"))

;; For describe-unbound-keys
(require 'unbound)

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
(require 'color-theme)
(color-theme-initialize)
(color-theme-charcoal-black)                   

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

;; Disable scroll bars.
(toggle-scroll-bar -1)

;; Invoke M-x without alt.
(global-set-key "\C-x\C-m" 'execute-extended-command)
(global-set-key "\C-c\C-m" 'execute-extended-command)

;; C-mode settings.
(setq c-default-style "k&r"
      c-basic-offset 4)
(add-hook 'c-mode-common-hook
          (lambda ()
            (c-toggle-auto-hungry-state 1)))

;; Ruby mode settings.
(add-hook 'ruby-mode-hook
          (lambda ()
            (add-hook 'local-write-file-hooks
                      '(lambda ()
                         (save-excursion
                           (untabify (point-min) (point-max))
                           (delete-trailing-whitespace)
                           )))
			(set (make-local-variable 'indent-tabs-mode) 'nil)
            (set (make-local-variable 'tab-width) 2)
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

;; Latex settings.
(add-hook 'LaTeX-mode-hook 'LaTeX-math-mode)

;; Join two lines
(global-set-key (kbd "C-M-j") 'join-line)

;; Spell check comments
(autoload 'flyspell-mode "flyspell" "On-the-fly spelling checker." t)
(add-hook 'message-mode-hook 'turn-on-flyspell)
(add-hook 'text-mode-hook 'turn-on-flyspell)
(add-hook 'c-mode-common-hook 'flyspell-prog-mode)
(add-hook 'ruby-mode-hook 'flyspell-prog-mode)
(add-hook 'tcl-mode-hook 'flyspell-prog-mode)

(defun turn-on-flyspell ()
   "Force flyspell-mode on using a positive arg.  For use in hooks."
   (interactive)
   (flyspell-mode 1))

;; rcodetools
(require 'rcodetools)

;; Textmate and paredit mode.
(require 'textmate-mode)
(autoload 'paredit-mode "paredit"
  "Minor mode for pseudo-structurally editing Lisp code."
  t)
(add-hook 'c-mode-common-hook (lambda () (textmate-mode)))
(add-hook 'emacs-lisp-mode-hook (lambda () (paredit-mode +1)))

;; Disable auto-save
(setq auto-save-default nil)
