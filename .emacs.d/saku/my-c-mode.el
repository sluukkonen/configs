;; C mode settings

(setq c-default-style "k&r"
      c-basic-offset 4
      c-cleanup-list '(brace-elseif-brace
                       brace-else-brace
                       brace-catch-brace
                       empty-defun-braces))

(add-hook 'c-mode-hook
          (lambda () (flymake-mode t)))
