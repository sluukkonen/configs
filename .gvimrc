set lines=80
set columns=83
set go-=T

" Scrollbars only on the right side of the window
set guioptions-=L
set guioptions-=l
set guioptions-=R
set guioptions-=r 
set guioptions-=m 
set guifont=DejaVu\ Sans\ Mono

" highlight the current line
set cursorline

"macvim fullscreen fix
if has("gui_mac")
	set fuopt=maxhorz,maxvert
endif
