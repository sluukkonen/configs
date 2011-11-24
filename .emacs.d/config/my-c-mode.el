(setq c-default-style "k&r"
      c-basic-offset 4)

(add-hook 'c-mode-hook
          (lambda ()
            (if (file-exists-p "Makefile") (flymake-mode t))
            (local-set-key (kbd "C-c o") 'ff-find-other-file)))
