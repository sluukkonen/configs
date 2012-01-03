;;; Use autopair.
(autopair-global-mode)

;; Indent comments as well.
(setq comment-style 'indent)

;; Default tab width.
(setq default-tab-width 4)

;; Line width.
(setq-default fill-column 80)

;; Display column/line numbers in the status line.
(setq column-number-mode t)

;; Set cursor to a vertical bar (I-beam) and make it blink.
(setq default-frame-alist
      '((cursor-type . bar)
        (cursor-color . "black")))
(blink-cursor-mode 1)

;;; System specific tweaks.
(cond ((eq system-type 'darwin)
       (setq exec-path (append '("/usr/local/bin" "/usr/texbin") exec-path))
       (setenv "PATH" (concat "/usr/local/bin:/usr/texbin:" (getenv "PATH")))
       (setq TeX-view-program-list
             '(("Preview" "/Applications/Preview.app/MacOS/Preview %q")))
       (setq ns-command-modifier 'meta)
       (menu-bar-mode t)))
(cond ((eq system-type 'gnu/linux)
       (setq ack-executable (executable-find "ack-grep"))))

;; Disable auto-save.
(setq auto-save-default nil)

;; Mark end of sentences with only one space. Y'know, like normal people do.
(set-variable 'sentence-end-double-space nil)

;; Use aspell as the default spell checker.
(set-variable 'ispell-program-name "aspell")
