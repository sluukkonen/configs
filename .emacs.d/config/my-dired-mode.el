(defun my-dired-init ()
  "Bunch of stuff to run for dired, either immediately or when it's loaded."
  (define-key dired-mode-map [return] 'dired-single-buffer)
  (define-key dired-mode-map [mouse-1] 'dired-single-buffer-mouse)
  (define-key dired-mode-map "^"
    (function
     (lambda nil (interactive) (dired-single-buffer "..")))))
(if (boundp 'dired-mode-map)
    (my-dired-init)
  (add-hook 'dired-load-hook 'my-dired-init))
