unlet! skip_defaults_vim
source $VIMRUNTIME/defaults.vim

set hidden
set number
set ignorecase
set smartcase
set re=2
set expandtab
set tabstop=4
set softtabstop=4
set shiftwidth=4

" Markdown hard line breaks and diff context can need trailing whitespace.
function! s:StripTrailingWhitespace() abort
  if &binary || index(['markdown', 'diff', 'gitsendemail'], &filetype) >= 0
    return
  endif
  let view = winsaveview()
  keeppatterns %s/\s\+$//e
  call winrestview(view)
endfunction

augroup stripTrailingWhitespace
  autocmd!
  autocmd BufWritePre * call s:StripTrailingWhitespace()
augroup END
