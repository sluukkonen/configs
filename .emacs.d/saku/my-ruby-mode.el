;; Ruby mode settings.

(add-hook 'ruby-mode-hook
          (lambda ()
            (setq autopair-dont-activate t)
            (set (make-local-variable 'tab-width) 2)
            (require 'ruby-electric)
            (ruby-electric-mode t)))
