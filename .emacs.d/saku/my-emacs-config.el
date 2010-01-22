;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Load libraries
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Vendor directory for third party libraries.
(add-to-list 'load-path (concat dotfiles-dir "vendor"))

;; Include Macports in the PATH
(setq exec-path (cons "/opt/local/bin" exec-path))
(setenv "PATH" (concat "/opt/local/bin:" (getenv "PATH")))

(require 'mark-lines)
(require 'rect-mark)
(require 'autopair)
(require 'yasnippet)

;; Initialize yasnippet
(yas/initialize)
(yas/load-directory (concat dotfiles-dir "vendor/snippets"))

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

;;; autopair-mode
(autopair-global-mode)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; General settings
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Indent comments.
(setq comment-style 'indent)

;; Default tab width.
(setq default-tab-width 4)

;; Line width.
(setq-default fill-column 80)

;; Display column/line numbers in the status line.
(setq column-number-mode t)

;; Some mac-specific hacks.
(when (eq system-type 'darwin)
    (setq ns-command-modifier 'meta))

;; hippie-expand expansions.
(setq hippie-expand-try-functions-list '(try-expand-dabbrev
                                         try-expand-dabbrev-all-buffers try-expand-dabbrev-from-kill
                                         try-complete-file-name-partially try-complete-file-name
                                         try-expand-all-abbrevs try-expand-list try-expand-line
                                         try-complete-lisp-symbol-partially try-complete-lisp-symbol))

;; Disable auto-save
(setq auto-save-default nil)

;; Mark end of sentences with one space.
(set-variable 'sentence-end-double-space nil)

;; Fix zsh prompt
(autoload 'ansi-color-for-comint-mode-on "ansi-color" nil t)
(add-hook 'shell-mode-hook 'ansi-color-for-comint-mode-on)

;;; Set ispell to aspell
(set-variable 'ispell-program-name "aspell")
