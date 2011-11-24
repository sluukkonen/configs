;;; init.el --- Where all the magic begins

(require 'package)
(add-to-list 'package-archives
             '("marmalade" . "http://marmalade-repo.org/packages/") t)
(add-to-list 'package-archives
             '("tromey" . "http://tromey.com/elpa/") t)
(package-initialize)

(when (not package-archive-contents)
  (package-refresh-contents))

(defvar my-packages '(starter-kit starter-kit-bindings starter-kit-lisp starter-kit-ruby autopair mode-compile rect-mark rinari ruby-electric scala-mode yasnippet-bundle)
  "A list of packages to ensure are installed at launch.")

(dolist (p my-packages)
  (when (not (package-installed-p p))
    (package-install p)))

;;; Load some global libraries.
(require 'autopair)
(require 'rect-mark)
(require 'yasnippet-bundle)

(yas/initialize)

;;; Make ruby-electric-mode behave with yasnippet.
(defun yas/advise-indent-function (function-symbol)
  (eval `(defadvice ,function-symbol (around yas/try-expand-first activate)
           ,(format
             "Try to expand a snippet before point, then call `%s' as usual"
             function-symbol)
           (let ((yas/fallback-behavior nil))
             (unless (and (interactive-p)
                          (yas/expand))
               ad-do-it)))))

(yas/advise-indent-function 'ruby-indent-line)

;;; Load personal configuration files.
(setq my-config-dir (concat user-emacs-directory "config"))

(add-to-list 'load-path my-config-dir)
(when (file-exists-p my-config-dir)
  (mapc 'load (directory-files my-config-dir nil "^[^#].*el$")))
