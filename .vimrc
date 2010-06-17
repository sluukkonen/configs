" line numbers
set number
" incremental search
set incsearch
" ignore case in searches, but be case-sensitive if capital letters are used
set ignorecase
set smartcase
" we're using vim, not vi
set nocompatible
" default indentation level
set tabstop=4
set shiftwidth=4
set softtabstop=4
set expandtab
" syntax highlighting
syntax on
" show caret position in the status bar
set ruler
" better buffer handling, ie. don't nag about saving files
set hidden
" backspace deletes eols, tabs, chars
set bs=indent,eol,start
" smarter file prompt
set wildmenu
" no annoying files~
set nobackup
" colorscheme
set t_Co=256 " needed for 256 color colorschemes
colorscheme zenburn
" disable toolbar and menubar
set guioptions-=T
set guioptions-=m
set guioptions-=r
set guioptions-=l
set guioptions-=b

" automatic filetype detection
filetype on
filetype plugin on
filetype indent on

" better mapleader key
let mapleader = ","
" fuzzyfinder mappings
nmap <leader>f :FuzzyFinderFile<CR>
nmap <leader>d :FuzzyFinderDir<CR>
nmap <leader>b :FuzzyFinderBuffer<CR>
nmap <leader>s :FuzzyFinderTag<CR>

" standard library ctags for C-like languages
set tags+=tags;$HOME

" fix common typos
command WQ wq
command Wq wq
command W w
command Q q

" Insert mode readline-like bindings
noremap! <C-a> <Home>
noremap! <C-b> <Left>
noremap! <C-d> <Del>
noremap! <C-e> <End>
noremap! <C-f> <Right>
noremap! <M-b> <S-Left>
noremap! <M-f> <S-Right>

" Window management.
nmap <C-J> <C-W>j
nmap <C-K> <C-W>k
nmap <C-H> <C-W>h
nmap <C-L> <C-W>l

" Highligh trailing whitespace.
match Underlined /\s\+$/

" Functions
function! StripTrailingWhitespace()
    %s/\s\+$//e
endfunction

" Easier gqap.
map Q gq
