;; Ruby mode settings.
(add-hook 'ruby-mode-hook
          (lambda ()
            (add-hook 'local-write-file-hooks
                      '(lambda ()
                         (save-excursion
                           (untabify (point-min) (point-max))
                           (delete-trailing-whitespace)
                           )))
            (set (make-local-variable 'tab-width) 2)
            (require 'ruby-electric)
            (ruby-electric-mode t)
            ))
