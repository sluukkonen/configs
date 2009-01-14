;; Saku's Emacs settings

(require 'unbound)

;; Snippets
(require 'yasnippet) 
(yas/initialize)
(yas/load-directory "~/.emacs.d/saku/snippets")

;; Install mode-compile to give friendlier compiling support!
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

;; A full  screen command
(defun toggle-fullscreen ()
  (interactive)
  (set-frame-parameter nil 'fullscreen (if (frame-parameter nil 'fullscreen)
                                           nil
                                         'fullboth)))
(global-set-key (kbd "M-n") 'toggle-fullscreen)

;; Skeleton pairing
(setq skeleton-pair t)
(setq skeleton-pair-on-word t) ; apply skeleton trick even in front of a word.
(global-set-key (kbd "(")  'skeleton-pair-insert-maybe)
(global-set-key (kbd "[")  'skeleton-pair-insert-maybe)
(global-set-key (kbd "{")  'skeleton-pair-insert-maybe)
(global-set-key (kbd "\"") 'skeleton-pair-insert-maybe)
(global-set-key (kbd "\'") 'skeleton-pair-insert-maybe)

;; Indent comments
(setq comment-style 'indent)

;; Default tab width
(setq default-tab-width 4)

;; Textmate-like newline
(defun textmate-next-line ()
  (interactive)
  (end-of-line)
  (newline-and-indent))
(global-set-key (kbd "M-RET") 'textmate-next-line)

;; Line width
(setq-default full-column 80 )

;; Whole line marking

;; Disable scrollbars
(toggle-scroll-bar -1)