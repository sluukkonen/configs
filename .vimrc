" line numbers
set number
" incremental search
set incsearch
" ignore case in searches, but be case-sensitive if capital letters are used
set ignorecase
set smartcase
" we're using vim, not vi
set nocompatible
" Indentation level
set tabstop=4
set shiftwidth=4
set expandtab
" syntax highlighting 
syntax on
" show caret position in the status bar
set ruler
" better buffer handling, ie. don't nag about saving files
set hidden
" backspace deletes eols, tabs, chars
set bs=2
" smarter file prompt
set wildmenu
" no annoying files~
set nobackup
" better end and start of line
nmap H ^
nmap L $
omap H ^
omap L $

filetype on
filetype plugin on
filetype indent on

" TextMate-like cmd-enter"
imap <D-Enter> <Esc>o

" modifier key
let mapleader = ","
nmap <leader>f :FuzzyFinderTextMate<CR>

" standard library ctags for C-like languages
set tags=/.vim/tags/stdtags,tags,.tags,../tags

" fix common typos
command WQ wq
command Wq wq
command W w
command Q q

"""""""""""""""""""""""""""" Filetype settings """""""""""""""""""""""""""""" 

" html 
let g:html_indent_tags = "p"
autocmd FileType html setlocal shiftwidth=2 | setlocal tabstop=2

" ruby 
autocmd FileType ruby setlocal shiftwidth=2 | setlocal tabstop=2
autocmd FileType ruby,eruby set omnifunc=rubycomplete#Complete
autocmd FileType ruby,eruby let g:rubycomplete_buffer_loading = 1
autocmd FileType ruby,eruby let g:rubycomplete_rails = 1
autocmd FileType ruby,eruby let g:rubycomplete_classes_in_global = 1
