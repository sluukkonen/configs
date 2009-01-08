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
set tabstop=2
" indent by 2 spaces
set shiftwidth=2
" slate, desert?
colorscheme default
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
" highlight the current line
set cursorline
" no annoying files~
set nobackup
" folding
set foldmethod=syntax
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
