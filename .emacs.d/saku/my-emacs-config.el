;; Saku's Emacs settings

;; Vendor directory for third party libraries.
(add-to-list 'load-path (concat dotfiles-dir "vendor"))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Required libraries.
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(require 'unbound)
(require 'yasnippet)
(require 'color-theme)
(require 'mark-lines)
(require 'rcodetools)
(require 'textmate-mode)
(require 'rect-mark)

;;; mode-compile
(autoload 'mode-compile "mode-compile"
  "Command to compile current buffer file based on the major mode" t)
(autoload 'mode-compile-kill "mode-compile"
  "Command to kill a compilation launched by `mode-compile'" t)

;;; flyspell-mode
(autoload 'flyspell-mode "flyspell" "On-the-fly spelling checker." t)

;;; paredit-mode
(autoload 'paredit-mode "paredit"
  "Minor mode for pseudo-structurally editing Lisp code."
  t)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;Keybindings
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; A filetype agnostic compile command.
(global-set-key "\C-cc" 'mode-compile)
(global-set-key "\C-ck" 'mode-compile-kill)

;;; Invoke M-x without M-x.
(global-set-key "\C-x\C-m" 'execute-extended-command)

;;; Set C-h to delete a char and remap help.
(global-set-key "\C-h" 'delete-backward-char)
(global-set-key "\M-?" 'help-command)

;; ;;; Set M-/ to use hippie-expand instead of dabbrev-expand.
;; (global-set-key "\M-/" 'hippie-expand)

;;; Select whole lines.
(global-set-key "\C-x\C-p" 'mark-lines-previous-line)
(global-set-key "\C-x\C-n" 'mark-lines-next-line)

;;; Join two lines.
(global-set-key "\C-\M-j" 'join-line)

;;; Rectangle selection commands.
(global-set-key (kbd "C-x r C-SPC") 'rm-set-mark)
(global-set-key (kbd "C-x r C-x")   'rm-exchange-point-and-mark)
(global-set-key (kbd "C-x r C-w")   'rm-kill-region)
(global-set-key (kbd "C-x r M-w")   'rm-kill-ring-save)

(global-set-key (kbd "C-c F") 'toggle-fullscreen)
(global-set-key (kbd "M-RET") 'textmate-next-line)

;;; Flymake shortcuts.
(global-set-key "\M-s" 'flymake-display-err-menu-for-current-line)
(global-set-key "\M-n" 'flymake-goto-next-error)
(global-set-key "\M-p" 'flymake-goto-prev-error)


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; General settings
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Snippets.
(yas/initialize)
(yas/load-directory "~/.emacs.d/vendor/snippets")

;; Color themes
(color-theme-initialize)
(color-theme-light)

;; Indent comments.
(setq comment-style 'indent)

;; Default tab width.
(setq default-tab-width 4)

;; Line width.
(setq-default fill-column 80 )

;; Display column/line numbers in the status line.
(setq column-number-mode t)

;; Disable scroll bars.
(toggle-scroll-bar -1)

;; Some mac-specific hacks.
(setq mac-pass-command-to-system nil)   ; Disable cmd-h in carbon emacs.
(setq mac-pass-control-to-system nil)   ; Disable control keybindings for OS X.

;; hippie-expand expansions.
(setq hippie-expand-try-functions-list '(try-expand-dabbrev
                                         try-expand-dabbrev-all-buffers try-expand-dabbrev-from-kill
                                         try-complete-file-name-partially try-complete-file-name
                                         try-expand-all-abbrevs try-expand-list try-expand-line
                                         try-complete-lisp-symbol-partially try-complete-lisp-symbol))

;; Disable auto-save
(setq auto-save-default nil)
