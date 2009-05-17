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
" colorscheme
set t_Co=256 " needed for 256 color colorschemes 
colorscheme xoria256
" better end and start of line
nmap H ^
nmap L $
omap H ^
omap L $

filetype on
filetype plugin on
filetype indent on

" omnicppcomplete settings
let OmniCpp_ShowScopeInAbbr = 1
let OmniCpp_ShowPrototypeInAbbr = 1

" TextMate-like cmd-enter
imap <D-Enter> <Esc>o

" modifier key
let mapleader = ","
" fuzzyfinder mappings
nmap <leader>f :FuzzyFinderFile<CR>
nmap <leader>d :FuzzyFinderDir<CR>
nmap <leader>b :FuzzyFinderBuffer<CR>

" standard library ctags for C-like languages
set tags=/.vim/tags/stdtags,tags,.tags,../tags

" fix common typos
command WQ wq
command Wq wq
command W w
command Q q

" Insert mode readline-like bindings
:inoremap <C-a>		<Home>
:inoremap <C-b>		<Left>
:inoremap <C-d>		<Del>
:inoremap <C-e>		<End>
:inoremap <C-f>		<Right>
:inoremap <M-b>  	<S-Left>
:inoremap <M-f>	    <S-Right>
