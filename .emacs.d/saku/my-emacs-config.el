;;; Load libraries ;;;

;; Use the vendor directory for third party libraries.
(add-to-list 'load-path (concat dotfiles-dir "vendor"))
(add-to-list 'load-path (concat dotfiles-dir "vendor/scala-mode"))

;; Load some useful libraries.
(require 'mark-lines)
(require 'rect-mark)
(require 'autopair)
(require 'yasnippet)
(require 'scala-mode-auto)

;; Initialize yasnippet
(yas/initialize)
(yas/load-directory (concat dotfiles-dir "vendor/snippets"))

;; mode-compile
(autoload 'mode-compile "mode-compile"
  "Command to compile current buffer file based on the major mode" t)
(autoload 'mode-compile-kill "mode-compile"
  "Command to kill a compilation launched by `mode-compile'" t)

;; flyspell-mode
(autoload 'flyspell-mode "flyspell" "On-the-fly spelling checker." t)

;; paredit-mode
(autoload 'paredit-mode "paredit" "Minor mode for pseudo-structurally editing Lisp code." t)

;; autopair-mode
(autopair-global-mode)

;;; General settings ;;;

;; Indent comments too
(setq comment-style 'indent)

;; Default tab width
(setq default-tab-width 4)

;; Line width
(setq-default fill-column 80)

;; Display column/line numbers in the status line
(setq column-number-mode t)

;; Display cursor as a vertical bar (I-beam)
(setq default-frame-alist
      '((cursor-type . bar)))

;; Blink cursor
(blink-cursor-mode 1)

;; When running OS X, include the Macports path and use Cmd as meta key
(when (eq system-type 'darwin)
  (setq exec-path (cons "/opt/local/bin" exec-path))
  (setenv "PATH" (concat "/opt/local/bin:" (getenv "PATH")))
  (setq ns-command-modifier 'meta))

;; Disable auto-save
(setq auto-save-default nil)

;; Mark end of sentences with only one space
(set-variable 'sentence-end-double-space nil)

;; Fix zsh in ansi-shell
(autoload 'ansi-color-for-comint-mode-on "ansi-color" nil t)
(add-hook 'shell-mode-hook 'ansi-color-for-comint-mode-on)

;; Set ispell to aspell
(set-variable 'ispell-program-name "aspell")
