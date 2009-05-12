(defun turn-on-flyspell ()
  "Force flyspell-mode on using a positive arg.  For use in hooks."
  (interactive)
  (flyspell-mode 1))

(defun toggle-fullscreen ()
  "Sets full screen."
  (interactive)
  (set-frame-parameter nil 'fullscreen (if (frame-parameter nil 'fullscreen)
                                           nil
                                         'fullboth)))

(defun textmate-next-line ()
  "Textmate-like CMD-RET"
  (interactive)
  (end-of-line)
  (newline-and-indent))
