" line numbers
" set number
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
set softtabstop=4
set noexpandtab
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

" Insert mode readline-like bindings
" start of line
:inoremap <C-a>		<Home>
" back one character
:inoremap <C-b>		<Left>
" delete character under cursor
:inoremap <C-d>		<Del>
" end of line
:inoremap <C-e>		<End>
" forward one character
:inoremap <C-f>		<Right>
" back one word
:inoremap <M-b>  	<S-Left>
" forward one word
:inoremap <M-f>	    <S-Right>
