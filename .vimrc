" line numbers
set number
" incremental search
set incsearch
" ignore case in searches, but be case-sensitive if capital letters are used
set ignorecase
set smartcase
" we're using vim, not vi
set nocompatible
" dunno?
set tabstop=4
" slate, desert?
set shiftwidth=4
colorscheme wombat256
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
map H ^
map L $
map <C-]> <C-s>

filetype on
filetype plugin on
filetype indent on

" easier switching to tag under cursor
nnoremap <C-p> <C-]>

" ruby omni completion
autocmd FileType ruby,eruby set omnifunc=rubycomplete#Complete
autocmd FileType ruby,eruby let g:rubycomplete_buffer_loading = 1
autocmd FileType ruby,eruby let g:rubycomplete_rails = 1
autocmd FileType ruby,eruby let g:rubycomplete_classes_in_global = 1

" modifier key
let mapleader = ","
map <leader>f :FuzzyFinderTextMate<CR>

" standard library ctags for C-like languages
set tags=/.vim/tags/stdtags,tags,.tags,../tags

" fix common typos
command WQ wq
command Wq wq
command W w
command Q q

inoremap {      {}<Left>
inoremap {<CR>  {<CR>}<Esc>O
inoremap {{     {
inoremap {}     {}

