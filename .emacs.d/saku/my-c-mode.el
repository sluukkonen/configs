;; cc-mode settings.
(setq c-default-style "k&r"
      c-basic-offset 4
      c-cleanup-list '(brace-elseif-brace
                       brace-else-brace
                       brace-catch-brace
                       empty-defun-braces))

(add-hook 'c-mode-common-hook
          (lambda ()
            (c-toggle-auto-hungry-state t)
            (local-set-key (kbd "{") 'cheeso-insert-open-brace)
            ;; Untabify files.
            (add-hook 'local-write-file-hooks
                      '(lambda ()
                         (save-excursion
                           (untabify (point-min) (point-max))
                           (delete-trailing-whitespace))))))
