(add-hook 'ruby-mode-hook
          (lambda ()
            (ruby-electric-mode t)
            (substitute-key-definition 'ruby-electric-curlies nil ruby-mode-map)
            (substitute-key-definition 'ruby-electric-matching-char nil ruby-mode-map)
            (substitute-key-definition 'ruby-electric-close-matching-char nil ruby-mode-map)
            (setq ruby-insert-encoding-magic-comment nil)))
