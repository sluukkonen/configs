;; cc-mode settings.
(setq c-default-style "k&r"
      c-basic-offset 4
      c-cleanup-list '(brace-elseif-brace
                       brace-else-brace
                       brace-catch-brace
                       empty-defun-braces))

(add-hook 'c-mode-common-hook
          (lambda ()
            (local-set-key (kbd "{") 'cheeso-insert-open-brace)
            (local-set-key (kbd "C-c o") 'ff-find-other-file)
            ;; Untabify files.
            (add-hook 'write-file-functions
                      '(lambda ()
                         (save-excursion
                           (untabify (point-min) (point-max))
                           (delete-trailing-whitespace))))))

(add-hook 'c-mode-hook
          (lambda ()
            (flymake-mode t)))
