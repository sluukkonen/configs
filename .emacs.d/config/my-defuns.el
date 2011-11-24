(defun turn-on-flyspell ()
  "Force flyspell-mode on by using a positive arg. To be used in hooks."
  (interactive)
  (flyspell-mode 1))

(defun toggle-fullscreen ()
  "Toggles full screen on and off."
  (interactive)
  (set-frame-parameter nil 'fullscreen (if (frame-parameter nil 'fullscreen)
                                           nil
                                         'fullboth)))

(defun textmate-next-line ()
  "Textmate-like Cmd-RET"
  (interactive)
  (end-of-line)
  (newline-and-indent))
