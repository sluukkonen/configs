setlocal shiftwidth=2 | setlocal tabstop=2
set omnifunc=rubycomplete#Complete
let g:rubycomplete_buffer_loading = 1
let g:rubycomplete_rails = 1
let g:rubycomplete_classes_in_global = 1
source ~/.vim/ftplugin/ri.vim

" fix endwise.vim
let b:delimitMate_expand_cr = 0
